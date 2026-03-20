import asyncio
import hashlib
import logging
import secrets
import shutil
import os
import json
import uuid

from contextlib import asynccontextmanager
from datetime import date, datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from autoapply.logging import get_logger
from autoapply.application_handlers import (
    apply_with_streaming,
    get_application_answers,
    tailor_for_url,
    apply_for_url,
    parse_resume,
    list_resume,
)
from typing import Optional

from autoapply.env import ALLOWED_ORIGINS
from autoapply.services.scrape_google_results import GoogleSearchAutomation
from autoapply.services.db import Txc, _calc_years_of_experience
from autoapply.models import (
    ApplicationAnswers,
    Contact,
    Job,
    LoginParams,
    PostJobsParams,
    SignupParams,
    UploadResumeParams,
    Resume,
    SearchParams,
    UserOnboarding,
    QuestionRequest,
)
from autoapply.sse import SSEManager
from autoapply.browser_manager import BrowserManager

get_logger()
logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{key.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, key = stored.split(":")
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return new_key.hex() == key
    except Exception:
        return False


# Global instances for SSE and browser management
sse_manager = SSEManager()
browser_manager = BrowserManager()

# Max concurrent job applications running at the same time
APPLICATION_POOL_SIZE = 3
_apply_semaphore = asyncio.Semaphore(APPLICATION_POOL_SIZE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup: Initialize browser manager on application startup
    After shutdown: Cleanup browser manager on application shutdown
    """
    # DB migrations
    try:
        with Txc() as tx:
            tx.cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
            tx.cursor.execute("ALTER TABLE user_data ADD COLUMN IF NOT EXISTS years_of_experience INT")
            tx.conn.commit()
        logger.info("DB migrations applied")
    except Exception as e:
        logger.warning(f"DB migration warning (may be harmless): {e}")

    logger.info("Initializing browser manager...")
    try:
        await browser_manager.initialize()
        logger.info("Browser manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize browser manager: {e}")
        raise
    yield
    logger.info("Shutting down browser manager...")
    try:
        await browser_manager.shutdown()
        logger.info("Browser manager shutdown complete")
    except Exception as e:
        logger.error(f"Error during browser manager shutdown: {e}")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def batch_process(params: PostJobsParams, tailor: bool = False):
    batch_size = 5
    total = len(params.urls)

    all_results = []

    # Process in batches
    for batch_idx in range(0, total, batch_size):
        # Get the current batch of URLs
        urls_batch = params.urls[batch_idx : batch_idx + batch_size]

        logger.info(
            f"Processing batch {batch_idx // batch_size + 1} of {(total + batch_size - 1) // batch_size}"
        )

        # Create tasks for this batch
        if tailor:
            tasks = [
                tailor_for_url(batch_idx + idx, url, total, params.resume_id)
                for idx, url in enumerate(urls_batch)
            ]
        else:
            tasks = [
                apply_for_url(batch_idx + idx, url, total, params.resume_id)
                for idx, url in enumerate(urls_batch)
            ]

        # Wait for all tasks in this batch to complete
        results = await asyncio.gather(*tasks)
        all_results.extend(results)

        logger.info(f"Batch {batch_idx // batch_size + 1} completed")

    return all_results


@app.post("/tailortojobs")
async def tailor_for_jobs(params: PostJobsParams):
    with Txc() as tx:
        user_email = tx.get_user_email_by_resume(params.resume_id)
        if user_email:
            tx.insert_fetched_urls(params.urls, user_email, params.resume_id, 'tailor')
    return await batch_process(params, tailor=True)


async def _run_pooled(session_id: str, url: str, resume_id: int):
    """Acquire a pool slot then run the application, releasing the slot when done."""
    async with _apply_semaphore:
        await apply_with_streaming(
            session_id=session_id,
            url=url,
            resume_id=resume_id,
            sse_manager=sse_manager,
            browser_manager=browser_manager,
        )


@app.post("/applytojobs")
async def apply_for_jobs(params: PostJobsParams):
    """
    Submit job applications with real-time monitoring.

    Up to APPLICATION_POOL_SIZE (3) run concurrently; the rest wait for a slot.
    Frontend can connect to /stream/{session_id} for real-time updates.
    """
    sessions = []

    with Txc() as tx:
        user_email = tx.get_user_email_by_resume(params.resume_id)
        if user_email:
            tx.insert_fetched_urls(params.urls, user_email, params.resume_id, 'apply')

    for url in params.urls:
        session_id = str(uuid.uuid4())
        today = datetime.now().strftime("%Y-%m-%d")
        screenshot_dir = f"data/applications/{today}/screenshots/{session_id}"

        try:
            with Txc() as tx:
                placeholder_job = Job(
                    url=url,
                    role="Processing",
                    company_name="Processing",
                    date_posted=None,
                    cloud="aws",
                    resume_score=0.0,
                    job_match_summary="Application in progress",
                    date_applied=datetime.now(),
                    jd_filepath=None,
                    resume_filepath=None,
                    application_qnas=None,
                )
                tx.insert_job(placeholder_job, params.resume_id)
                tx.create_application_session(
                    session_id=session_id,
                    job_url=url,
                    resume_id=params.resume_id,
                    status="queued",
                    screenshot_dir=screenshot_dir,
                )

            sessions.append({"session_id": session_id, "url": url, "status": "queued"})

            # Launch concurrently — semaphore limits to APPLICATION_POOL_SIZE at once
            asyncio.create_task(_run_pooled(session_id, url, params.resume_id))

        except Exception as e:
            logger.error(f"Error creating session for {url}: {e}")
            sessions.append({"session_id": session_id, "url": url, "status": "failed", "error": str(e)})

    return {"sessions": sessions}


@app.get("/sessions")
async def list_sessions(date: Optional[date] = None, email: Optional[str] = None):
    """List job application sessions, defaulting to today, filtered by user email."""
    target_date = date or datetime.now().date()
    with Txc() as tx:
        sessions = tx.list_application_sessions(target_date, user_email=email)
    return sessions


@app.get("/jobs")
async def get_jobs(date: Optional[date] = None, email: Optional[str] = None) -> list[Job]:
    with Txc() as tx:
        jobs = tx.list_jobs(date=date, user_email=email)
    return [Job(**job) for job in jobs]


@app.get("/fetched-urls")
async def get_fetched_urls(date: Optional[date] = None, email: Optional[str] = None):
    target_date = date or datetime.now().date()
    with Txc() as tx:
        rows = tx.list_fetched_urls(target_date, user_email=email)
    return [dict(r) for r in rows]


@app.post("/upload")
async def upload_file(user_email: str, file: UploadFile = File(...)):
    try:
        upload_dir = "data/resumes"
        os.makedirs(upload_dir, exist_ok=True)
        filename = str(file.filename)
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with Txc() as tx:
            resume_id = tx.add_resume_path(file_path, user_email)

        return {"resume_id": resume_id, "path": file_path}
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-resume")
async def upload_resume(params: UploadResumeParams) -> int:
    try:
        return await parse_resume(params.path)
    except Exception as e:
        logger.error(f"Error parsing resume: {e}")
        raise HTTPException(status_code=400, detail=f"Upload .docx files only, {e}")


@app.get("/get-details")
async def get_resume_details(resume_id: int) -> Resume:
    try:
        logger.debug(f"Getting data for {resume_id}")
        data = await list_resume(resume_id)
        return data
    except RuntimeError as e:
        raise HTTPException(
            status_code=404, detail=f"Resume not found or resume_id cannot be None: {e}"
        )


@app.get("/list-resumes")
async def list_resume_ids(email: Optional[str] = None) -> list[int]:
    with Txc() as tx:
        saved_resumes = tx.list_resumes(user_email=email)
    return [resume["id"] for resume in saved_resumes]


@app.post("/application-question")
async def get_answers(params: QuestionRequest) -> ApplicationAnswers:
    return await get_application_answers(params.url, params.questions)


@app.post("/search-jobs")
async def run_search(params: SearchParams) -> list[str]:
    google = GoogleSearchAutomation(cache_duration_hours=24)

    if not params.ats_sites:
        # Popular job sites
        sites = [
            "greenhouse.io",
            "myworkdayjobs.com",
            "ashbyhq.com",
            "icims.com",
            "oraclecloud.com",
            "adp.com",
            "smartrecruiters.com",
            "taleo.net",
            "applytojob.com",
            "lever.co",
            "ultipro.com",
            "workable.com",
            "rippling.com",
            "paylocity.com",
            "dayforcehcm.com",
            "jobvite.com",
            "bamboohr.com",
            "teamtailor.com",
            "paycomonline.net",
            "successfactors.com",
            "recruitingbypaycor.com",
            "dayforcehcm.com",
        ]
    else:
        sites = params.ats_sites

    # Build search query parts, filtering out empty values
    parts = [params.role]
    if params.company:
        parts.append(params.company)
    for site in sites:
        parts.append(f"site:{site} OR")

    search = " ".join(parts)
    search = search.strip("OR")
    urls = await google.auto_search(search, params.force, params.pages)

    sanitized = []
    for url in urls:
        if "myworkdayjobs.com" in url:
            # Strip /apply and everything after — those pages show login/apply form, not the JD
            idx = url.find("/apply")
            if idx != -1:
                url = url[:idx]
        sanitized.append(url)

    return sanitized


@app.post("/signup")
async def signup(params: SignupParams):
    """Create a new user account with password."""
    password_hash = _hash_password(params.password)
    with Txc() as tx:
        email = tx.create_user_with_password(
            name=params.name,
            email=params.email,
            phone=params.phone,
            country_code=params.country_code,
            location=params.location,
            linkedin=params.linkedin,
            github=params.github,
            password_hash=password_hash,
        )
    return {"email": email, "name": params.name, "message": "Account created successfully"}


@app.post("/login")
async def login(params: LoginParams):
    """Authenticate a user by email and password."""
    with Txc() as tx:
        user = tx.get_user_by_email(params.email)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not _verify_password(params.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    with Txc() as tx:
        has_data = tx.has_user_data(user["email"])
    return {"email": user["email"], "name": user["name"], "message": "Login successful", "has_user_data": has_data}


@app.get("/validate-session")
async def validate_session(email: str):
    """Check if a stored email still corresponds to a valid user account."""
    with Txc() as tx:
        user = tx.get_user_by_email(email)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Session invalid")
    return {"valid": True}


@app.get("/user-info")
async def get_user_info(email: str):
    """Get basic user info from signup (name, phone, location) for pre-filling forms."""
    with Txc() as tx:
        user = tx.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "country_code": user.get("country_code", "+1"),
        "location": user.get("location", ""),
    }


@app.post("/save-user")
async def save_user(contact: Contact):
    """Save/update user contact information"""
    with Txc() as tx:
        email = tx.upsert_user(contact)
    return {"email": email, "message": "User saved successfully"}


@app.get("/user-form")
async def get_user_form(email: str):
    """Fetch saved user application data"""
    with Txc() as tx:
        data = tx.get_user_data(email)
    if not data:
        raise HTTPException(status_code=404, detail="No application data found")
    # Pre-fill years_of_experience from resume if not manually set
    if not data.get("years_of_experience"):
        with Txc() as tx2:
            resumes = tx2.list_resumes(user_email=email)
            if resumes:
                job_exps = tx2.list_job_exps(resumes[0]["id"])
                calc = _calc_years_of_experience(job_exps)
                if calc:
                    data["years_of_experience"] = calc
    return data


@app.get("/profile/yoe")
async def profile_yoe(email: str):
    """Returns calculated years of experience from resume job dates."""
    with Txc() as tx:
        resumes = tx.list_resumes(user_email=email)
        if not resumes:
            return {"years_of_experience": 0}
        job_exps = tx.list_job_exps(resumes[0]["id"])
    return {"years_of_experience": _calc_years_of_experience(job_exps)}


@app.get("/profile/completion")
async def profile_completion(email: str):
    """Returns profile completion status for the user."""
    with Txc() as tx:
        has_data = tx.has_user_data(email)
        resumes = tx.list_resumes(user_email=email)
    has_resume = len(resumes) > 0
    pct = (50 if has_resume else 0) + (50 if has_data else 0)
    return {"has_resume": has_resume, "has_user_data": has_data, "completion": pct}


@app.post("/user-form")
async def fill_form(params: UserOnboarding):
    """Save/update user onboarding data"""
    with Txc() as tx:
        email = tx.fill_user_information(params)
    return {"email": email, "message": "User data saved successfully"}


# Real-time monitoring endpoints
@app.get("/stream/{session_id}")
async def stream_events(session_id: str):
    """
    SSE endpoint for real-time job application updates.

    Streams events like:
    - status_update: Session status changes
    - tool_call: Agent tool executions
    - screenshot: New screenshots available
    - error: Error occurred
    - pause: Agent paused
    - resume: Agent resumed
    """
    queue = await sse_manager.add_stream(session_id)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                if event is None:  # End signal
                    break

                # Format as SSE event
                yield {
                    "event": event.get("type", "message"),
                    "data": json.dumps(event.get("data", {})),
                }
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for session {session_id}")
        finally:
            await sse_manager.remove_stream(session_id)

    return EventSourceResponse(event_generator())


@app.get("/screenshots/{session_id}/{filename}")
async def get_screenshot(session_id: str, filename: str):
    """
    Serve screenshot files for a session.

    Security: Validates session exists in database before serving.
    """
    # Validate session exists
    with Txc() as tx:
        session = tx.get_application_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build screenshot path
    screenshot_dir = session.get("screenshot_dir")
    if not screenshot_dir:
        # Fallback to default path structure
        created_at = session.get("created_at")
        if created_at:
            date_str = created_at.strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
        screenshot_dir = f"data/applications/{date_str}/screenshots/{session_id}"

    screenshot_path = os.path.join(screenshot_dir, filename)

    # Validate path exists
    if not os.path.exists(screenshot_path):
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return FileResponse(screenshot_path, media_type="image/png")


@app.post("/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    """
    Request agent to pause.

    Agent will pause after completing current tool execution.
    """
    with Txc() as tx:
        session = tx.get_application_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session["status"] not in ["running", "queued"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause session in status: {session['status']}",
            )

        tx.update_session_status(session_id, "paused")

    return {"status": "paused", "message": "Agent will pause after current action"}


@app.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """
    Resume paused agent.

    Agent will continue from where it paused.
    """
    with Txc() as tx:
        session = tx.get_application_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session["status"] != "paused":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume session in status: {session['status']}",
            )

        tx.update_session_status(session_id, "running")

    return {"status": "running", "message": "Agent resumed"}


@app.get("/sessions/{session_id}/vnc-focus")
async def focus_vnc_tab(session_id: str):
    """
    Focus browser tab in VNC viewer.

    Brings the tab for this session to front, making it visible in VNC.
    """
    with Txc() as tx:
        session = tx.get_application_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    tab_index = session.get("tab_index")
    if tab_index is None:
        raise HTTPException(
            status_code=404, detail="No browser tab found for this session"
        )

    try:
        await browser_manager.focus_tab(tab_index)
    except Exception as e:
        logger.error(f"Failed to focus tab: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to focus tab: {str(e)}")

    return {
        "tab_index": tab_index,
        "vnc_url": "http://localhost:6080/vnc.html",
        "message": "Tab focused successfully",
    }


@app.get("/download-resume")
async def get_resume(url: str):
    with Txc() as tx:
        resume = tx.get_resume(url)
    if resume:
        logger.debug(f"Resume fetched: {resume}")

        headers = {"Content-Disposition": f"inline; filename={resume}"}

        # Create a FileResponse object with the file path, media type and headers
        response = FileResponse(
            f"{resume}", media_type="application/pdf", headers=headers
        )
        return response
    else:
        raise RuntimeError("No resume found")

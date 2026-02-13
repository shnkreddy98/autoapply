import logging
import os
import uuid
import asyncio

from datetime import datetime, timezone
from playwright.async_api import async_playwright

from autoapply.services.db import Txc
from autoapply.env import RESUME_PATH
from autoapply.logging import get_logger
from autoapply.utils import read
from autoapply.services.llm import (
    BrowserTools,
    JobApplicationAgent,
    ResumeParserAgent,
    ResumeTailorAgent,
    ApplicationQuestionAgent,
)
from autoapply.services.llm.streaming_agent import StreamingJobApplicationAgent
from autoapply.services.word import create_resume, convert_docx_to_pdf
from autoapply.models import (
    ApplicationAnswers,
    Certification,
    Contact,
    Education,
    Job,
    JobExperience,
    Resume,
    Skills,
)

get_logger()
logger = logging.getLogger(__name__)
applications_dir = "data/applications"


async def extract_job_description(url: str, page=None) -> tuple[str, str, str]:
    """
    Extract job description from URL.

    Args:
        url: Job posting URL
        page: Optional existing Playwright page. If None, creates a new browser instance.

    Returns:
        Tuple of (title, content, jd_filepath) where jd_filepath is the saved markdown file path
    """
    close_browser = False
    browser = None

    try:
        if page is None:
            # Create new browser instance
            from playwright.async_api import async_playwright
            p = await async_playwright().__aenter__()
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            page = await browser.new_page()
            close_browser = True

        # Set default timeout
        page.set_default_timeout(timeout=60000)

        # Navigate to URL
        await page.goto(url)

        # Handle cookie popup
        await handle_cookie_popup(page)

        # Wait for page to load
        await page.wait_for_timeout(5000)

        # Get page content
        title = await page.title()
        content = await page.inner_text("body")

        # Extract company and role from title
        company_name = "Unknown"
        role = "Unknown"

        if " - " in title:
            parts = title.split(" - ", 1)
            role = parts[0].strip()
            company_name = parts[1].strip()
        elif " at " in title.lower():
            parts = title.lower().split(" at ", 1)
            role = title[:len(parts[0])].strip()
            company_name = title[len(parts[0])+4:].strip()
        else:
            role = title

        # Save JD to file
        today = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(applications_dir, today, company_name)
        os.makedirs(output_dir, exist_ok=True)

        filename = role.replace("/", "")
        jd_filepath = os.path.join(output_dir, f"{filename}.md")

        with open(jd_filepath, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"Source: {url}\n\n")
            f.write("---\n\n")
            f.write(content)

        logger.info(f"Job description saved to {jd_filepath}")

        if close_browser and browser:
            await browser.close()

        return title, content, jd_filepath

    except Exception as e:
        logger.error(f"Error extracting JD from {url}: {e}")
        if close_browser and browser:
            await browser.close()
        raise


async def list_resume(resume_id: int) -> Resume:
    with Txc() as tx:
        contact = tx.list_contact(resume_id)
        if not contact:
            raise RuntimeError(f"{resume_id} not found in database")
        contact_obj = Contact(**contact[0])

        summary = tx.get_summary(resume_id)
        if summary:
            summary_obj = summary
        else:
            raise RuntimeError("No summary found")
        job_exps = tx.list_job_exps(resume_id)
        job_exps_obj = [JobExperience(**job_exp) for job_exp in job_exps]

        skills = tx.list_skills(resume_id)
        skills_obj = [Skills(**skill) for skill in skills]

        education = tx.list_education(resume_id)
        education_obj = [Education(**education) for education in education]

        certifications = tx.list_certifications(resume_id)
        certification_obj = [
            Certification(**certification) for certification in certifications
        ]

    return Resume(
        contact=contact_obj,
        summary=summary_obj,
        job_exp=job_exps_obj,
        skills=skills_obj,
        education=education_obj,
        certifications=certification_obj,
    )


async def parse_resume(path: str) -> int:
    resume = await read(path)
    if not isinstance(resume, Resume):
        # Use ResumeParserAgent to parse resume text
        parser = ResumeParserAgent()
        resume_details = await parser.parse_resume(resume)
        logger.debug(f"Resume returned from the Agent: {resume_details}")
        try:
            with Txc() as tx:
                resume_id = tx.insert_resume(resume_details, path=path)

            return resume_id
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            raise RuntimeError(f"Failed to insert resume: {e}")
    else:
        logger.error("LLM returned data could not be validated")
        raise RuntimeError("Resume parsing returned invalid data")


async def apply(url: str, resume_id: int, session_id: str) -> tuple[Job, dict]:
    """
    Apply to a job and return Job object along with agent conversation data.
    Returns: (job, agent_data) where agent_data contains messages, usage, etc.
    """
    try:
        with Txc() as tx:
            candidate_data = tx.get_candidate_data(resume_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            page = await browser.new_page()

            # Extract and save job description
            title, content, jd_filepath = await extract_job_description(url, page)

            # Extract role and company from title
            company_name = "Unknown"
            role = "Unknown"

            if " - " in title:
                parts = title.split(" - ", 1)
                role = parts[0].strip()
                company_name = parts[1].strip()
            elif " at " in title.lower():
                parts = title.lower().split(" at ", 1)
                role = title[:len(parts[0])].strip()
                company_name = title[len(parts[0])+4:].strip()
            else:
                role = title

            # Now apply with the agent
            tools = BrowserTools(page)
            jobs_agent = JobApplicationAgent(tools)

            result = await jobs_agent.apply_to_job(url, candidate_data)
            logger.debug(f"Results from ApplyAgent: {result}")

            # Capture agent conversation data
            agent_data = {
                "messages": jobs_agent.messages,
                "usage": jobs_agent.result.usage,
                "iterations": jobs_agent.result.iterations,
                "success": jobs_agent.result.success,
                "error": jobs_agent.result.error,
            }

            await browser.close()

            # Create Job object
            now_utc = datetime.now(timezone.utc)
            job = Job(
                url=url,
                role=role,
                company_name=company_name,
                date_posted=None,
                cloud="aws",
                resume_score=0.0,  # No scoring for direct apply
                job_match_summary="Applied directly without tailoring",
                date_applied=now_utc,
                jd_filepath=jd_filepath,
                resume_filepath=candidate_data.get("resume_path"),
                application_qnas=None,
            )

            return job, agent_data
    except Exception as e:
        logger.error(f"Error occured: {e} while applying for {url}")
        raise RuntimeError(f"Error occured {e} while applying for {url}")


async def apply_for_url(idx: int, url: str, total: int, resume_id: int):
    logger.info(url)
    logger.info(f"Processing {idx + 1} of {total}")
    session_id = str(uuid.uuid4())

    try:
        job, agent_data = await apply(url, resume_id, session_id)

        with Txc() as tx:
            # Insert job
            tx.insert_job(job, resume_id)

            # Get user email from resume
            user_email = tx.get_user_email_by_resume(resume_id)

            # Save conversation to database
            if user_email:
                tx.insert_conversation(
                    session_id=session_id,
                    user_email=user_email,
                    job_url=url,
                    endpoint="applytojobs",
                    agent_type="JobApplicationAgent",
                    messages=agent_data["messages"],
                    usage_metrics=agent_data["usage"],
                    iterations=agent_data["iterations"],
                    success=agent_data["success"],
                    error_message=agent_data["error"],
                )
        return True

    except Exception as e:
        logger.error(f"Error applying for resume: {e}")
        # Try to save failed conversation
        try:
            with Txc() as tx:
                user_email = tx.get_user_email_by_resume(resume_id)
                if user_email:
                    tx.insert_conversation(
                        session_id=session_id,
                        user_email=user_email,
                        job_url=url,
                        endpoint="applytojobs",
                        agent_type="JobApplicationAgent",
                        messages=[],
                        usage_metrics={},
                        iterations=0,
                        success=False,
                        error_message=str(e),
                    )
        except:
            pass  # Don't fail if conversation save fails
        return False


async def tailor_for_url(idx: int, url: str, total: int, resume_id: int):
    logger.info(url)
    logger.info(f"Processing {idx + 1} of {total}")
    session_id = str(uuid.uuid4())

    try:
        job, agent_data = await tailor_resume(url, resume_id, session_id)

        with Txc() as tx:
            # Insert job
            tx.insert_job(job, resume_id)

            # Get user email from resume
            user_email = tx.get_user_email_by_resume(resume_id)

            # Save conversation to database
            if user_email and agent_data:
                tx.insert_conversation(
                    session_id=session_id,
                    user_email=user_email,
                    job_url=url,
                    endpoint="tailortojobs",
                    agent_type="ResumeTailorAgent",
                    messages=agent_data["messages"],
                    usage_metrics=agent_data["usage"],
                    iterations=agent_data["iterations"],
                    success=agent_data["success"],
                    error_message=agent_data["error"],
                )
        return True

    except Exception as e:
        logger.error(f"Error tailoring resume: {e}")
        # Try to save failed conversation
        try:
            with Txc() as tx:
                user_email = tx.get_user_email_by_resume(resume_id)
                if user_email:
                    tx.insert_conversation(
                        session_id=session_id,
                        user_email=user_email,
                        job_url=url,
                        endpoint="tailortojobs",
                        agent_type="ResumeTailorAgent",
                        messages=[],
                        usage_metrics={},
                        iterations=0,
                        success=False,
                        error_message=str(e),
                    )
        except:
            pass  # Don't fail if conversation save fails
        return False


async def handle_cookie_popup(page):
    """
    Try to accept cookie consent popups using common patterns.
    Returns True if a popup was found and clicked, False otherwise.
    """
    # Common selectors and text patterns for cookie consent buttons
    selectors_to_try = [
        # By button text (most common)
        "button:has-text('Accept')",
        "button:has-text('Accept all')",
        "button:has-text('Accept All')",
        "button:has-text('Accept all and continue')",
        "button:has-text('I agree')",
        "button:has-text('I Agree')",
        "button:has-text('Agree')",
        "button:has-text('OK')",
        "button:has-text('Got it')",
        "button:has-text('Allow all')",
        "button:has-text('Consent')",
        "button:has-text('Confirm My Choices')"
        # By common IDs and classes
        "#onetrust-accept-btn-handler",  # OneTrust
        "#accept-cookies",
        ".accept-cookies",
        "[data-testid='cookie-accept']",
        "[data-testid='accept-all-cookies']",
        ".cookie-consent-accept",
        ".cookies-accept-all",
        # By aria-label
        "[aria-label*='Accept']",
        "[aria-label*='Agree']",
    ]

    for selector in selectors_to_try:
        try:
            # Wait up to 2 seconds for this selector
            button = await page.wait_for_selector(
                selector, timeout=2000, state="visible"
            )
            if button:
                await button.click()
                logger.info(f"Clicked cookie consent button: {selector}")
                await page.wait_for_timeout(500)  # Wait for popup to close
                return True
        except Exception:
            continue  # Try next selector

    logger.debug("No cookie popup found or already accepted")
    return False


async def tailor_resume(url: str, resume_id: int, session_id: str) -> tuple[Job, dict]:
    try:
        # Extract and save job description using shared function
        title, content, jd_filepath = await extract_job_description(url)
    except Exception as e:
        logger.error(f"Error: {e}\noccured while extracting JD for: {url}")
        return None, None

    llm = None
    agent_data = None
    now_utc = datetime.now(timezone.utc)
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # Reading resume to compare
        logger.debug(f"Reading resume: {resume_id}")

        resume = await list_resume(resume_id)
        logger.debug(f"Resume returned of type {type(resume)} with data: \n{resume}")

        # Extract JD details and tailor resume (LLM Call)
        tailor_agent = ResumeTailorAgent()
        llm = await tailor_agent.tailor_resume(resume, f"{title}\n\n{content}")
        logger.debug("Job details extracted!")

        # Capture agent conversation data
        agent_data = {
            "messages": tailor_agent.messages,
            "usage": tailor_agent.result.usage,
            "iterations": tailor_agent.result.iterations,
            "success": tailor_agent.result.success,
            "error": tailor_agent.result.error,
        }

        # Output directory for tailored resume (same as JD location)
        output_dir = os.path.join(applications_dir, today, llm.company_name)
        os.makedirs(output_dir, exist_ok=True)

    except Exception as e:
        logger.error(f"Error: {e}\nwhile LLM comparing JD and resume for {url}")
        return None, None

    resume_name = ""
    try:
        # Read current resume for scoring
        with Txc() as tx:
            contact_list = tx.list_contact(resume_id)
            if not contact_list:
                logger.error(f"Contact details for resume_id {resume_id} not found.")
                return None, None
            contact_details = contact_list[0]
            contact = Contact(**contact_details)

            job_list = tx.list_job_exps(resume_id)
            jobs = {
                job["company_name"].lower(): JobExperience(**job) for job in job_list
            }

            education_list = tx.list_education(resume_id)
            education = [Education(**edu) for edu in education_list]

            cert_list = tx.list_certifications(resume_id)
            certificates = [Certification(**cert) for cert in cert_list]

        summary = llm.new_summary

        for new_points in llm.new_job_experience:
            if new_points.company_name.lower() in jobs:
                jobs[
                    new_points.company_name.lower()
                ].experience = new_points.experience_points

        skills = llm.new_skills_section

        # Writing resume to file
        resume_name = create_resume(
            save_path=output_dir,
            contact=contact,
            summary_text=summary,
            job_exp=list(jobs.values()),
            skills=skills,
            education_entries=education,
            certifications=certificates,
        )
        logger.debug(f"Resume written to {resume_name}")
    except Exception as e:
        logger.error(f"Error occured while creating new resume: {e}")
        return None, None

    try:
        logger.debug(f"Converting {resume_name} to pdf")
        resume_pdf = await convert_docx_to_pdf(resume_name)
        if resume_pdf:
            logger.debug(f"Resume created at {resume_pdf}")
        else:
            logger.debug("Conversion to pdf failed")

        # Saving new data
        llm_data = llm.model_dump()
        job = Job(
            **llm_data,
            url=url,
            date_applied=now_utc,
            jd_filepath=jd_filepath,
            resume_filepath=resume_pdf,
        )

        logger.info(f"Job description saved to {jd_filepath}")
        logger.info(f"Tailored resume saved to {resume_pdf}")

        return job, agent_data
    except Exception as e:
        logger.error(f"Error occured for {url}: {e}")
        return None, None


async def get_application_answers(url: str, questions: str) -> ApplicationAnswers:
    with Txc() as tx:
        jd_path = tx.get_jd_path(url)
        if jd_path:
            jd = await read(jd_path["jd_filepath"])
    path = "/".join(jd.split(".")[0].split("/")[:-1])
    resume_file = RESUME_PATH.split("/")[-1]
    resume_path = os.path.join(path, resume_file)
    if os.path.exists(resume_path):
        resume = await read(resume_path)
    else:
        logger.error(f"Error finding resume for {url} use default resume")
        resume = await read(RESUME_PATH)

    # Use ApplicationQuestionAgent to answer questions
    question_agent = ApplicationQuestionAgent()
    answers = await question_agent.answer_questions(
        resume=resume,
        job_description=jd,
        questions=[questions],  # Wrap in list as agent expects list of questions
    )

    with Txc() as tx:
        update_application_qnas = tx.update_qnas(answers.model_dump(), url)

    return answers


def parse_job_title(title: str) -> tuple[str, str]:
    """
    Parse job title to extract company name and role.

    Args:
        title: Page title from job posting

    Returns:
        Tuple of (company_name, role)
    """
    company_name = "Unknown"
    role = "Unknown"

    if " - " in title:
        parts = title.split(" - ", 1)
        role = parts[0].strip()
        company_name = parts[1].strip()
    elif " at " in title.lower():
        parts = title.lower().split(" at ", 1)
        role = title[:len(parts[0])].strip()
        company_name = title[len(parts[0])+4:].strip()
    else:
        role = title

    return company_name, role


async def apply_with_streaming(
    session_id: str,
    url: str,
    resume_id: int,
    sse_manager,
    browser_manager,
):
    """
    Apply to job with real-time streaming via SSE.

    Creates a browser tab for the session, uses StreamingJobApplicationAgent
    for automatic screenshots and event streaming, and updates the database
    with results.

    Args:
        session_id: Unique session identifier
        url: Job URL to apply to
        resume_id: Resume ID to use for application
        sse_manager: SSEManager instance for event streaming
        browser_manager: BrowserManager instance for tab management
    """
    try:
        # Update status to running
        with Txc() as tx:
            tx.update_session_status(session_id, "running")
            candidate_data = tx.get_candidate_data(resume_id)

        # Send initial status event
        await sse_manager.send_event(session_id, {
            "type": "status_update",
            "data": {"status": "running", "message": "Starting application"}
        })

        # Create browser tab for this session
        page, tab_index = await browser_manager.create_tab_for_session(session_id)

        # Update tab index in database
        with Txc() as tx:
            tx.update_session_tab_index(session_id, tab_index)

        # Extract job description (reuses the page)
        title, content, jd_filepath = await extract_job_description(url, page)

        # Parse company/role from title
        company_name, role = parse_job_title(title)

        # Get screenshot directory from database
        with Txc() as tx:
            session = tx.get_application_session(session_id)
            screenshot_dir = session.get("screenshot_dir", f"data/applications/{datetime.now().strftime('%Y-%m-%d')}/screenshots/{session_id}")

        # Create streaming agent
        tools = BrowserTools(page, session_id=session_id)
        agent = StreamingJobApplicationAgent(
            browser_tools=tools,
            sse_manager=sse_manager,
            session_id=session_id,
            screenshot_dir=screenshot_dir,
        )

        # Apply to job (agent streams events automatically)
        logger.info(f"Starting job application for session {session_id}")
        result = await agent.apply_to_job(url, candidate_data)

        # Create Job object with results
        now_utc = datetime.now(timezone.utc)
        job = Job(
            url=url,
            role=role,
            company_name=company_name,
            date_posted=None,
            cloud="aws",
            resume_score=0.0,
            job_match_summary="Applied directly without tailoring",
            date_applied=now_utc,
            jd_filepath=jd_filepath,
            resume_filepath=candidate_data.get("resume_path"),
            application_qnas=None,
        )

        # Save to database
        with Txc() as tx:
            # Update existing job record
            tx.insert_job(job, resume_id)
            tx.update_session_status(session_id, "completed")

            # Get user email for conversation save
            user_email = tx.get_user_email_by_resume(resume_id)

            # Save conversation
            if user_email:
                tx.insert_conversation(
                    session_id=session_id,
                    user_email=user_email,
                    job_url=url,
                    endpoint="applytojobs",
                    agent_type="StreamingJobApplicationAgent",
                    messages=agent.messages,
                    usage_metrics=agent.result.usage,
                    iterations=agent.result.iterations,
                    success=agent.result.success,
                    error_message=agent.result.error,
                )

        # Send completion event
        await sse_manager.send_event(session_id, {
            "type": "status_update",
            "data": {
                "status": "completed",
                "message": "Application completed successfully",
                "role": role,
                "company": company_name,
            }
        })

        logger.info(f"Application completed for session {session_id}")

        # Close tab after delay (keep visible for 30s so user can see final state)
        await asyncio.sleep(30)
        await browser_manager.close_tab(session_id)
        await sse_manager.remove_stream(session_id)

    except Exception as e:
        logger.error(f"Error in apply_with_streaming for session {session_id}: {e}", exc_info=True)

        # Update status to failed
        try:
            with Txc() as tx:
                tx.update_session_status(session_id, "failed", error=str(e))
        except Exception as db_error:
            logger.error(f"Failed to update session status on error: {db_error}")

        # Send error event
        try:
            await sse_manager.send_event(session_id, {
                "type": "error",
                "data": {
                    "error": str(e),
                    "status": "failed",
                }
            })
        except Exception as sse_error:
            logger.error(f"Failed to send error event: {sse_error}")

        # Save failed conversation
        try:
            with Txc() as tx:
                user_email = tx.get_user_email_by_resume(resume_id)
                if user_email:
                    tx.insert_conversation(
                        session_id=session_id,
                        user_email=user_email,
                        job_url=url,
                        endpoint="applytojobs",
                        agent_type="StreamingJobApplicationAgent",
                        messages=[],
                        usage_metrics={},
                        iterations=0,
                        success=False,
                        error_message=str(e),
                    )
        except Exception as conv_error:
            logger.error(f"Failed to save failed conversation: {conv_error}")

        # Clean up
        try:
            await browser_manager.close_tab(session_id)
            await sse_manager.remove_stream(session_id)
        except:
            pass

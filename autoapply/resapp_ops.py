import logging
import os
import shutil
import asyncio

from datetime import datetime, timezone
from playwright.async_api import async_playwright

from autoapply.env import APPLICATIONS_DIR
from autoapply.services.db import Txc
from autoapply.logging import get_logger
from autoapply.services.llm import (
    BrowserTools,
    DocumentTools,
    JobApplicationAgent,
    ResumeTailorAgent,
)
from autoapply.services.llm.streaming_agent import StreamingJobApplicationAgent
from autoapply.services.word import convert_docx_to_pdf
from autoapply.models import (
    Job,
)

get_logger()
logger = logging.getLogger(__name__)


async def get_jd_path(llm: Job):
    today = datetime.now().strftime("%Y-%m-%d")

    # Output directory for tailored resume and JD
    output_dir = os.path.join(APPLICATIONS_DIR, today, llm.company_name)
    os.makedirs(output_dir, exist_ok=True)

    jd_filename = llm.role.replace("/", "")
    return os.path.join(output_dir, f"{jd_filename}.md")


async def extract_job_description(url: str, page=None) -> str:
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
                headless=False, args=["--no-sandbox", "--disable-dev-shm-usage"]
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
        content = await page.inner_text("body")

        if close_browser and browser:
            await browser.close()

        return content

    except Exception as e:
        logger.error(f"Error extracting JD from {url}: {e}")
        if close_browser and browser:
            await browser.close()
        raise


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
                headless=False, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = await browser.new_page()

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

            jd_filepath = await get_jd_path(result)

            # Create Job object
            now_utc = datetime.now(timezone.utc)
            job = Job(
                url=url,
                role=result.role,
                company_name=result.company_name,
                date_posted=result.date_posted,
                cloud=result.cloud,
                resume_score=result.resume_score,  # No scoring for direct apply
                job_match_summary=result.job_match_summary,
                date_applied=now_utc,
                jd_filepath=jd_filepath,
                resume_filepath=candidate_data.get("resume_path"),
                application_qnas=None,
            )

            return job, agent_data
    except Exception as e:
        logger.error(f"Error occured: {e} while applying for {url}")
        raise RuntimeError(f"Error occured {e} while applying for {url}")


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


async def tailor_resume(url: str, resume_id: int) -> None:
    try:
        # Extract and save job description using shared function
        content = await extract_job_description(url)
    except Exception as e:
        logger.error(f"Error: {e}\noccured while extracting JD for: {url}")
        return None, None

    llm = None
    agent_data = None

    try:
        # Reading resume to compare
        logger.debug(f"Reading resume: {resume_id}")

        with Txc() as tx:
            resume_path = tx.get_resume_path(resume_id)

        if resume_path:
            resume_file = resume_path.split("/")[-1]
            tmp = f"/tmp/{datetime.now().strftime('%H%M%S%f')}"
            os.makedirs(tmp, exist_ok=True)
            tmp_path = os.path.join(tmp, resume_file)
            shutil.copy(resume_path, tmp_path)
            logger.debug(f"Resume copied from {resume_path} to {tmp_path}")

            # Extract JD details and tailor resume (LLM Call)
            doc = DocumentTools(tmp_path)
            tailor_agent = ResumeTailorAgent(document_tools=doc)
            llm = await tailor_agent.tailor_resume(content)
            logger.debug("Job details extracted!")

            # Capture agent conversation data
            agent_data = {
                "messages": tailor_agent.messages,
                "usage": tailor_agent.result.usage,
                "iterations": tailor_agent.result.iterations,
                "success": tailor_agent.result.success,
                "error": tailor_agent.result.error,
            }

            # Output directory for tailored resume and JD
            jd_filepath = await get_jd_path(llm)
            output_dir = "/".join(jd_filepath.split("/")[:-1])
            resume_name = os.path.join(output_dir, resume_file)
            logger.debug(f"Resume written to {output_dir}")
            shutil.move(tmp_path, resume_name)

            with open(jd_filepath, "w", encoding="utf-8") as f:
                f.write(f"# {llm.role}\n\n")
                f.write(f"Source: {url}\n\n")
                f.write("---\n\n")
                f.write(content)
                logger.debug(f"JD written to {output_dir}")
        else:
            raise RuntimeError(f"No resume found for {resume_id}")

    except Exception as e:
        logger.error(f"Error: {e}\nwhile LLM comparing JD and resume for {url}")
        return None, None

    try:
        logger.debug(f"Converting {resume_name} to pdf")
        resume_pdf = await convert_docx_to_pdf(resume_name)
        if resume_pdf:
            logger.debug(f"Resume created at {resume_pdf}")
        else:
            logger.debug("Conversion to pdf failed")

        # Saving new data
        now_utc = datetime.now(timezone.utc)
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
        await sse_manager.send_event(
            session_id,
            {
                "type": "status_update",
                "data": {"status": "running", "message": "Starting application"},
            },
        )

        # Create browser tab for this session
        page, tab_index = await browser_manager.create_tab_for_session(session_id)

        # Update tab index in database
        with Txc() as tx:
            tx.update_session_tab_index(session_id, tab_index)

        # Get screenshot directory from database
        with Txc() as tx:
            session = tx.get_application_session(session_id)
            screenshot_dir = session.get(
                "screenshot_dir",
                f"data/applications/{datetime.now().strftime('%Y-%m-%d')}/screenshots/{session_id}",
            )

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
        logger.debug(f"Applied to {url} with {result}")

        jd_filepath = await get_jd_path(result)
        # Create Job object with results
        now_utc = datetime.now(timezone.utc)
        job = Job(
            url=url,
            role=result.role,
            company_name=result.company_name,
            date_posted=None,
            cloud=result.cloud,
            resume_score=result.resume_score,
            job_match_summary="Applied directly without tailoring",
            date_applied=now_utc,
            jd_filepath=jd_filepath,
            resume_filepath=candidate_data.get("resume_path"),
            application_qnas=None,
        )

        # Save to database
        with Txc() as tx:
            # Update existing job record
            logger.debug(f"Written {job.jd_filepath} to db")
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
        await sse_manager.send_event(
            session_id,
            {
                "type": "status_update",
                "data": {
                    "status": "completed",
                    "message": "Application completed successfully",
                    "role": result.role,
                    "company": result.company_name,
                },
            },
        )

        logger.info(f"Application completed for session {session_id}")

        # Close tab after delay (keep visible for 30s so user can see final state)
        await asyncio.sleep(30)
        await browser_manager.close_tab(session_id)
        await sse_manager.remove_stream(session_id)

    except Exception as e:
        logger.error(
            f"Error in apply_with_streaming for session {session_id}: {e}",
            exc_info=True,
        )

        # Update status to failed
        try:
            with Txc() as tx:
                tx.update_session_status(session_id, "failed", error=str(e))
        except Exception as db_error:
            logger.error(f"Failed to update session status on error: {db_error}")

        # Send error event
        try:
            await sse_manager.send_event(
                session_id,
                {
                    "type": "error",
                    "data": {
                        "error": str(e),
                        "status": "failed",
                    },
                },
            )
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
        await browser_manager.close_tab(session_id)
        await sse_manager.remove_stream(session_id)

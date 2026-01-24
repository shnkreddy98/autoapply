import logging
import os

from datetime import date
from playwright.async_api import async_playwright

from autoapply.services.db import Txc
from autoapply.env import RESUME_PATH
from autoapply.models import Job
from autoapply.logging import get_logger
from autoapply.utils import read
from autoapply.services.llm import extract_details
from autoapply.services.word import create_resume, convert_docx_to_pdf
from autoapply.models import (
    Certification,
    Contact,
    Education,
    JobExperience,
    Resume,
    Skills,
)

get_logger()
logger = logging.getLogger(__name__)
applications_dir = "data/applications"


async def list_resume(resume_id: int) -> Resume:
    with Txc() as tx:
        contact = tx.list_contact(resume_id)
        if not contact:
            raise RuntimeError(f"{resume_id} not found in database")
        contact_obj = Contact(**contact[0])

        job_exps = tx.list_job_exps(resume_id)
        job_exps_obj = [JobExperience(**job_exp) for job_exp in job_exps]

        skills = tx.list_skills(resume_id)
        skills_obj = [Skills(**skill) for skill in skills]

        education = tx.list_education(resume_id)
        education_obj = [Education(**education) for education in education]

        certification = tx.list_certifications(resume_id)
        certification_obj = [
            Certification(**certification) for certification in certification
        ]


    return Resume(
        contact=contact_obj,
        job_exp=job_exps_obj,
        skills=skills_obj,
        education=education_obj,
        certification=certification_obj,
    )


async def parse_resume(path: str) -> int:
    resume = await read(path)
    if not isinstance(resume, Resume):
        resume_details = await extract_details(resume, resume_flag=1)
        try:
            with Txc() as tx:
                resume_id = tx.insert_resume()
                tx.insert_contact_details(resume_id, resume_details.contact)
                tx.insert_job_exp(resume_id, resume_details.job_exp)
                tx.insert_skills(resume_id, resume_details.skills)
                tx.insert_education(resume_id, resume_details.education)
                tx.insert_certifications(resume_id, resume_details.certification)
            return resume_id
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
    else:
        logger.error("LLM returned data could not be validated")


async def process_url(idx: int, url: str, total: int, resume_id: int):
    logger.info(url)
    logger.info(f"Processing {idx + 1} of {total}")
    try:
        job = await tailor_resume(url, resume_id)

        with Txc() as tx:
            tx.insert_job(job)
        return True
    except Exception as e:
        logger.error(f"Error tailoring resume: {e}")
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


async def tailor_resume(url: str, resume_id: int) -> Job:
    title = ""
    content = ""
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Set default timeout for all operations on this page
            page.set_default_timeout(timeout=60000)

            # Navigate to URL
            await page.goto(url)
            # handle cookies if any
            await handle_cookie_popup(page)

            # Wait for page to load
            await page.wait_for_timeout(10000)

            # Get the page content
            content = await page.inner_text("body")

            title = await page.title()

            await browser.close()

    except Exception as e:
        logger.error(f"Error: {e}\noccured while extracting JD for: {url}")
        return None

    llm = None
    output_file = ""
    today = date.today().isoformat()
    
    try:
        # Reading resume to compare
        logger.debug(f"Reading resume from {RESUME_PATH}")
        resume = await read(RESUME_PATH)

        # Extract JD details and tailor resume (LLM Call)
        llm = await extract_details(f"{title}\n\n{content}", resume)
        logger.debug("Job details extracted!")

        # Writing JD to file
        output_dir = os.path.join(applications_dir, today, llm.company_name)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{llm.role}.md")

        # Save to JD to markdown file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"Source: {url}\n\n")
            f.write("---\n\n")
            f.write(content)
    except Exception as e:
        logger.error(f"Error: {e}\nwhile LLM comparing JD and resume for {url}")
        return None

    resume_name = ""
    try:
        # Read current resume for scoring
        with Txc() as tx:
            contact_list = tx.list_contact(resume_id)
            if not contact_list:
                logger.error(f"Contact details for resume_id {resume_id} not found.")
                return None
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
        return None

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
            date_applied=today,
            jd_filepath=output_file,
            resume_filepath=RESUME_PATH,
        )

        logger.info(f"Content saved to {output_file}")

        return job
    except Exception as e:
        logger.error(f"Error occured for {url}: {e}")
        return None

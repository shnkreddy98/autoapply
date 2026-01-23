import logging
import os

from datetime import date
from playwright.async_api import async_playwright

from autoapply.services.db import Txc
from autoapply.env import RESUME_PATH
from autoapply.models import Job
from autoapply.logging import get_logger
from autoapply.utils import get_rough_cloud, read
from autoapply.services.llm import extract_details
from autoapply.services.word import create_resume
from autoapply.models import Contact, Education, JobExperience

get_logger()
logger = logging.getLogger(__name__)
applications_dir = "data/applications"


async def process_url(idx: int, url: str, total: int):
    logger.info(url)
    logger.info(f"Processing {idx + 1} of {total}")
    try:
        job = await extract_job_description(url)

        with Txc() as tx:
            tx.insert_job(job)
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
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


async def extract_job_description(url: str) -> Job:
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)
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

            rough_cloud = await get_rough_cloud(content)
            logger.debug(f"Rough cloud is {rough_cloud}")
            resume_filepath = f"{RESUME_PATH}/{rough_cloud}/shashank_reddy.pdf"
            resume = await read(resume_filepath)

            llm = await extract_details(title, content, resume)
            today = date.today().isoformat()
            logger.debug("Job details extracted!")

            # Writing JD to file
            output_dir = os.path.join(applications_dir, today, llm.company_name)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{llm.role}.md")

            name = "Shashank Shashishekhar Reddy"
            contact = Contact(
                email="shnkreddy98@gmail.com",
                location="San Jose, California",
                phone="(510) 892-7191",
                linkedin="linkedin.com/in/shnkreddy",
                github="github.com/shnkreddy98",
            )
            summary = llm.new_summary
            exp = {}
            for new_job_exp in llm.new_job_experience:
                exp[new_job_exp.company_name.lower()] = new_job_exp.experience_points
            jobs = [
                JobExperience(
                    job_title="Founding Engineer",
                    company_name="AirFold",
                    location="San Francisco, California",
                    from_=date(year=2024, day=1, month=1),
                    to_="current",
                    experience=exp["airfold"],
                ),
                JobExperience(
                    job_title="Data Engineer",
                    company_name="Kantar",
                    location="Bengaluru, India",
                    from_=date(year=2020, day=1, month=4),
                    to_=date(year=2022, day=1, month=4),
                    experience=exp["kantar"],
                ),
                JobExperience(
                    job_title="Data Engineer",
                    company_name="The Sparks Foundation",
                    location="Bengaluru, India",
                    from_=date(year=2018, day=1, month=3),
                    to_=date(year=2020, day=1, month=3),
                    experience=exp["the sparks foundation"],
                ),
            ]
            skills = llm.new_skills_section
            education = [
                Education(
                    degree="Master's Degree",
                    major="Data Analytics",
                    college="San Jose State University",
                    from_=date(year=2023, day=1, month=1),
                    to_=date(year=2024, day=1, month=12),
                ),
                Education(
                    degree="Post Graduate Diploma",
                    major="Data Science",
                    college="IIIT Bangalore",
                    from_=date(year=2020, day=1, month=11),
                    to_=date(year=2021, day=1, month=10),
                ),
                Education(
                    degree="Bachelor of Engineering",
                    major="Computer Science",
                    college="Visvesvaraya Technological University",
                    from_=date(year=2016, day=1, month=7),
                    to_=date(year=2020, day=1, month=8),
                ),
            ]
            certificates = [
                "AWS Certified Cloud Practitioner | Amazon Web Services (AWS) | Jul 2023",
                "Azure AI Fundamentals | Microsoft Certified | Jan 2025",
            ]

            # Writing resume to file
            resume_name = create_resume(
                save_path=output_dir,
                name=name,
                contact=contact,
                summary_text=summary,
                job_exp=jobs,
                skills=skills,
                education_entries=education,
                certifications=certificates,
            )
            logger.debug(f"Resume written to {resume_name}")

            llm_data = llm.model_dump()
            job = Job(
                **llm_data,
                date_applied=today,
                jd_filepath=output_file,
                resume_filepath=resume_filepath,
            )

            # Save to markdown file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"Source: {url}\n\n")
                f.write("---\n\n")
                f.write(content)

            await browser.close()
            logger.info(f"Content saved to {output_file}")

        return job
    except Exception as e:
        logger.error(f"Error occured for {url}: {e}")
        return None

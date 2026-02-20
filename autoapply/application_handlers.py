import logging
import os
import uuid

from datetime import datetime

from autoapply.services.db import Txc
from autoapply.logging import get_logger
from autoapply.utils import read
from autoapply.services.llm import (
    ResumeParserAgent,
    ApplicationQuestionAgent,
)
from autoapply.functions import tailor_resume, apply
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


async def get_application_answers(url: str, questions: str) -> ApplicationAnswers:
    with Txc() as tx:
        data = tx.get_jd_resume(url)
        if data["jd_path"]:
            jd = await read(data["jd_path"])

        if data["resume_id"]:
            global_resume_path = tx.get_resume_path(data["resume_id"])

    path = "/".join(data["jd_path"].split(".")[0].split("/")[:-1])
    resume_file = global_resume_path.split("/")[-1]
    resume_path = os.path.join(path, resume_file)
    if os.path.exists(resume_path):
        resume = await read(resume_path)
    else:
        logger.error(f"Error finding resume for {url} use default resume")
        resume = await read(global_resume_path)

    # Use ApplicationQuestionAgent to answer questions
    question_agent = ApplicationQuestionAgent()
    answers = await question_agent.answer_questions(
        resume=resume,
        job_description=jd,
        questions=[questions],  # Wrap in list as agent expects list of questions
    )

    return answers


async def tailor_for_url(idx: int, url: str, total: int, resume_id: int):
    logger.info(url)
    logger.info(f"Processing {idx + 1} of {total}")
    session_id = str(uuid.uuid4())

    try:
        # Insert placeholder job first to satisfy foreign key constraint for conversations table
        with Txc() as tx:
            placeholder_job = Job(
                url=url,
                role="Processing",
                company_name="Processing",
                date_posted=None,
                cloud="aws",
                resume_score=0.0,
                job_match_summary="Tailor in progress",
                date_applied=datetime.now(),
                jd_filepath=None,
                resume_filepath=None,
                application_qnas=None,
            )
            tx.insert_job(placeholder_job, resume_id)

        job, agent_data = await tailor_resume(url, resume_id)

        with Txc() as tx:
            # Update job with real data
            logger.debug(f"Written {job.jd_filepath} to db")
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

        return False


async def apply_for_url(idx: int, url: str, total: int, resume_id: int):
    logger.info(url)
    logger.info(f"Processing {idx + 1} of {total}")
    session_id = str(uuid.uuid4())

    try:
        # Insert placeholder job first to satisfy foreign key constraint for conversations table
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
            tx.insert_job(placeholder_job, resume_id)

        job, agent_data = await apply(url, resume_id, session_id)

        with Txc() as tx:
            # Update job with real data
            logger.debug(f"Written {job.jd_filepath} to db")
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

        return False


async def parse_resume(path: str) -> int:
    resume = await read(path)
    if not isinstance(resume, Resume):
        # Use ResumeParserAgent to parse resume text
        parser = ResumeParserAgent()
        resume_details = await parser.parse_resume(resume)
        logger.debug(f"Resume returned from the Agent: {resume_details}")
        try:
            with Txc() as tx:
                # Upsert the resume by path (updates the record created by add_resume_path)
                resume_id = tx.upsert_resume(resume_details, path=path)

            return resume_id
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            raise RuntimeError(f"Failed to upsert resume: {e}")
    else:
        logger.error("LLM returned data could not be validated")
        raise RuntimeError("Resume parsing returned invalid data")


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

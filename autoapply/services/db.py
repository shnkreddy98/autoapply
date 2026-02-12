import logging
import psycopg2

from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
from contextlib import contextmanager
from datetime import date
from typing import Optional, Union

from autoapply.env import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from autoapply.models import (
    Contact,
    Job,
    Resume,
    UserOnboarding,
)
from autoapply.logging import get_logger

# Build connection string
CONNINFO = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

get_logger()
logger = logging.getLogger(__name__)


@contextmanager
def Txc():
    """
    Context manager for database transactions.

    Usage:
        with get_transaction() as repo:
            repo.insert_location(...)
            repo.insert_weather_reading(...)
        # Auto-commits on success, auto-rollbacks on exception
    """
    with psycopg2.connect(CONNINFO) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield AutoApply(cur, conn)


class AutoApply:
    """Repository for AutoApply Operations"""

    def __init__(self, cursor, conn):
        self.cursor = cursor
        self.conn = conn

    def insert_job(self, job: Job, resume_id: int) -> str:
        """
        Insert or update job post.
        Returns the URL of the inserted/updated job.
        """
        self.cursor.execute(
            """
            INSERT INTO jobs (url, role, company_name, date_posted, date_applied, jd_path, resume_id, resume_score, job_match_summary, application_qnas)
            VALUES (%(url)s, %(role)s, %(company_name)s, %(date_posted)s, DEFAULT, %(jd_path)s, %(resume_id)s, %(resume_score)s, %(job_match_summary)s, %(application_qnas)s)
            ON CONFLICT (url) DO UPDATE SET
                role = EXCLUDED.role,
                company_name = EXCLUDED.company_name,
                date_posted = EXCLUDED.date_posted,
                jd_path = EXCLUDED.jd_path,
                resume_id = EXCLUDED.resume_id,
                resume_score = EXCLUDED.resume_score,
                job_match_summary = EXCLUDED.job_match_summary,
                application_qnas = EXCLUDED.application_qnas
            RETURNING url
            """,
            {
                "url": job.url,
                "role": job.role,
                "company_name": job.company_name,
                "date_posted": job.date_posted,
                "jd_path": job.jd_filepath,
                "resume_id": resume_id,
                "resume_score": job.resume_score,
                "job_match_summary": job.job_match_summary,
                "application_qnas": Json(job.application_qnas)
                if hasattr(job, "application_qnas")
                else Json({}),
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to insert/update job: {job.url}")
        return result["url"]

    def list_jobs(
        self,
        date: Optional[date] = None,
    ) -> list[tuple]:
        """
        List all jobs, optionally filtered by date applied.
        """
        if date:
            sql = """
                SELECT * FROM jobs
                WHERE date_applied::date = %(date)s::date
                ORDER BY date_applied DESC
            """
            self.cursor.execute(sql, {"date": date})
        else:
            sql = """
                SELECT * FROM jobs
                ORDER BY date_applied DESC
            """
            self.cursor.execute(sql)

        return self.cursor.fetchall()

    def upsert_user(self, contact: Contact) -> str:
        """
        Insert or update user from resume contact info.
        Returns the user's email.
        """
        self.cursor.execute(
            """
            INSERT INTO users (name, email, phone, linkedin, github, location)
            VALUES (%(name)s, %(email)s, %(phone)s, %(linkedin)s, %(github)s, %(location)s)
            ON CONFLICT (email) DO UPDATE SET
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                linkedin = EXCLUDED.linkedin,
                github = EXCLUDED.github,
                location = EXCLUDED.location
            RETURNING email
            """,
            {
                "name": contact.name,
                "email": contact.email,
                "phone": contact.phone,
                "linkedin": contact.linkedin,
                "github": contact.github,
                "location": contact.location,
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to insert/update user: {contact.email}")
        return result["email"]

    def insert_resume(self, resume: Resume, path: Optional[str] = None) -> int:
        # First, ensure the user exists in the users table
        self.upsert_user(resume.contact)

        # Convert Pydantic models to dicts for JSONB columns
        # Use mode='json' to properly serialize dates and other non-JSON types
        job_exp_dicts = [exp.model_dump(mode='json') if hasattr(exp, 'model_dump') else exp for exp in resume.job_exp]
        education_dicts = [edu.model_dump(mode='json') if hasattr(edu, 'model_dump') else edu for edu in resume.education]
        skills_data = [skill.model_dump(mode='json') if hasattr(skill, 'model_dump') else skill for skill in resume.skills]
        cert_dicts = [cert.model_dump(mode='json') if hasattr(cert, 'model_dump') else cert for cert in resume.certifications]

        self.cursor.execute(
            """
            INSERT INTO resumes (id, user_email, path, summary, job_experience, education, skills, certifications)
            VALUES (DEFAULT, %(user_email)s, %(path)s, %(summary)s, %(job_experience)s, %(education)s, %(skills)s, %(certifications)s)
            RETURNING id
            """,
            {
                "user_email": resume.contact.email,
                "path": path,
                "summary": resume.summary,
                "job_experience": Json(job_exp_dicts),
                "education": Json(education_dicts),
                "skills": Json(skills_data),
                "certifications": Json(cert_dicts),
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError("Errored creating resume")
        return result["id"]

    def list_contact(self, resume_id: int) -> list[dict]:
        """
        Get contact details for a resume by joining with users table.
        Returns list with one contact dict that can be unpacked into Contact model.
        """
        sql = """
            SELECT u.name, u.email, u.phone, u.linkedin, u.github, u.location
            FROM resumes r
            JOIN users u ON r.user_email = u.email
            WHERE r.id = %(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})
        return self.cursor.fetchall()

    def list_job_exps(self, resume_id: int) -> list[dict]:
        """
        Get job experience array from resume JSONB column.
        Returns list of job experience dictionaries.
        """
        sql = """
            SELECT job_experience FROM resumes
            WHERE id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()

        if not result or not result["job_experience"]:
            return []

        # job_experience is already a Python list/dict (psycopg2 auto-converts JSONB)
        jobs = result["job_experience"]

        # Handle date parsing if needed
        if isinstance(jobs, list):
            for job in jobs:
                if isinstance(job.get("to_date"), str) and job[
                    "to_date"
                ].lower() not in [
                    "current",
                    "present",
                ]:
                    try:
                        parsed_date = datetime.strptime(
                            job["to_date"].strip(), "%Y-%m-%d"
                        ).date()
                        job["to_date"] = parsed_date
                    except (ValueError, AttributeError):
                        pass

        return jobs if isinstance(jobs, list) else []

    def list_education(self, resume_id: int) -> list[dict]:
        """
        Get education array from resume JSONB column.
        Returns list of education dictionaries.
        """
        sql = """
            SELECT education FROM resumes
            WHERE id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()

        if not result or not result["education"]:
            return []

        education = result["education"]
        return education if isinstance(education, list) else []

    def list_certifications(self, resume_id: int) -> list[dict]:
        """
        Get certifications array from resume JSONB column.
        Returns list of certification dictionaries.
        """
        sql = """
            SELECT certifications FROM resumes
            WHERE id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()

        if not result or not result["certifications"]:
            return []

        certifications = result["certifications"]
        return certifications if isinstance(certifications, list) else []

    def list_skills(self, resume_id: int) -> list[dict]:
        """
        Get skills from resume JSONB column.
        Returns skills object (could be dict or list depending on schema).
        """
        sql = """
            SELECT skills FROM resumes
            WHERE id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()

        if not result or not result["skills"]:
            return []

        skills = result["skills"]
        # Skills might be a dict or list, return as-is
        return skills if isinstance(skills, (list, dict)) else []

    def get_summary(self, resume_id: int) -> Optional[str]:
        """
        Get resume summary text.
        Returns summary string or None.
        """
        sql = """
            SELECT summary FROM resumes
            WHERE id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()

        return result["summary"] if result else None

    def list_resumes(self) -> list[dict]:
        """
        List all resumes with their IDs.
        Returns list of resume records.
        """
        sql = """
            SELECT id, user_email, path
            FROM resumes
            ORDER BY id DESC
        """

        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_jd_path(self, url: str) -> Optional[str]:
        """
        Get job description file path for a job URL.
        Returns path string or None.
        """
        sql = """
            SELECT jd_path
            FROM jobs
            WHERE url=%(url)s
        """

        self.cursor.execute(sql, {"url": url})
        result = self.cursor.fetchone()

        return result["jd_path"] if result else None
    
    def update_qnas(self, qnas: Union[dict, list], url: str) -> str:
        """
        Update the application_qnas for an existing job.
        Raises RuntimeError if job doesn't exist.
        """
        self.cursor.execute(
            """
                UPDATE jobs
                SET application_qnas = %(application_qnas)s
                WHERE url = %(url)s
                RETURNING url
            """,
            {
               "url": url,
               "application_qnas": Json(qnas),
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Job not found: {url}")
        return result["url"]

    def fill_user_information(self, user_data: UserOnboarding) -> str:
        """
        Insert or update user application data.
        Returns the user's email.
        """
        self.cursor.execute(
            """
            INSERT INTO user_data (
                email, full_name, street_address, city, state, zip_code, phone_number,
                date_of_birth, age_18_or_older, work_eligible_us, visa_sponsorship,
                available_start_date, employment_type, willing_relocate, willing_travel,
                travel_percentage, desired_salary, gender, race_ethnicity, veteran_status,
                disability_status, current_employee, ever_terminated, termination_explanation,
                security_clearance, cert_accuracy, cert_dismissal, cert_background_check,
                cert_drug_testing, cert_at_will, cert_job_description, cert_privacy_notice,
                cert_data_processing, electronic_signature, signature_date
            )
            VALUES (
                %(email_address)s, %(full_name)s, %(street_address)s, %(city)s, %(state)s,
                %(zip_code)s, %(phone_number)s, %(date_of_birth)s, %(age_18_or_older)s,
                %(work_eligible_us)s, %(visa_sponsorship)s, %(available_start_date)s,
                %(employment_type)s, %(willing_relocate)s, %(willing_travel)s,
                %(travel_percentage)s, %(desired_salary)s, %(gender)s, %(race_ethnicity)s,
                %(veteran_status)s, %(disability_status)s, %(current_employee)s,
                %(ever_terminated)s, %(termination_explanation)s, %(security_clearance)s,
                %(cert_accuracy)s, %(cert_dismissal)s, %(cert_background_check)s,
                %(cert_drug_testing)s, %(cert_at_will)s, %(cert_job_description)s,
                %(cert_privacy_notice)s, %(cert_data_processing)s, %(electronic_signature)s,
                %(signature_date)s
            )
            ON CONFLICT (email) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                street_address = EXCLUDED.street_address,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                zip_code = EXCLUDED.zip_code,
                phone_number = EXCLUDED.phone_number,
                date_of_birth = EXCLUDED.date_of_birth,
                age_18_or_older = EXCLUDED.age_18_or_older,
                work_eligible_us = EXCLUDED.work_eligible_us,
                visa_sponsorship = EXCLUDED.visa_sponsorship,
                available_start_date = EXCLUDED.available_start_date,
                employment_type = EXCLUDED.employment_type,
                willing_relocate = EXCLUDED.willing_relocate,
                willing_travel = EXCLUDED.willing_travel,
                travel_percentage = EXCLUDED.travel_percentage,
                desired_salary = EXCLUDED.desired_salary,
                gender = EXCLUDED.gender,
                race_ethnicity = EXCLUDED.race_ethnicity,
                veteran_status = EXCLUDED.veteran_status,
                disability_status = EXCLUDED.disability_status,
                current_employee = EXCLUDED.current_employee,
                ever_terminated = EXCLUDED.ever_terminated,
                termination_explanation = EXCLUDED.termination_explanation,
                security_clearance = EXCLUDED.security_clearance,
                cert_accuracy = EXCLUDED.cert_accuracy,
                cert_dismissal = EXCLUDED.cert_dismissal,
                cert_background_check = EXCLUDED.cert_background_check,
                cert_drug_testing = EXCLUDED.cert_drug_testing,
                cert_at_will = EXCLUDED.cert_at_will,
                cert_job_description = EXCLUDED.cert_job_description,
                cert_privacy_notice = EXCLUDED.cert_privacy_notice,
                cert_data_processing = EXCLUDED.cert_data_processing,
                electronic_signature = EXCLUDED.electronic_signature,
                signature_date = EXCLUDED.signature_date
            RETURNING email
            """,
            user_data.model_dump()
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to insert/update user data: {user_data.email_address}")
        return result["email"]

    def get_candidate_data(self, resume_id: int) -> dict:
        """
        Get combined candidate data (resume + user application data).
        Returns dict with resume info and user_data merged together.
        """
        # Get resume data
        resume_data = {}

        # Get contact info
        contact_list = self.list_contact(resume_id)
        if not contact_list:
            raise RuntimeError(f"Resume {resume_id} not found")

        contact = contact_list[0]
        resume_data["contact"] = contact

        # Get resume components
        resume_data["summary"] = self.get_summary(resume_id)
        resume_data["job_experience"] = self.list_job_exps(resume_id)
        resume_data["skills"] = self.list_skills(resume_id)
        resume_data["education"] = self.list_education(resume_id)
        resume_data["certifications"] = self.list_certifications(resume_id)

        # Get user application data
        sql = """
            SELECT * FROM user_data
            WHERE email = %(email)s
        """
        self.cursor.execute(sql, {"email": contact["email"]})
        user_data_result = self.cursor.fetchone()

        # Merge user_data if exists
        if user_data_result:
            resume_data["user_data"] = dict(user_data_result)

        return resume_data



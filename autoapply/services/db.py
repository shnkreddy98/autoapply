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
            INSERT INTO jobs (url, resume_path, role, company_name, date_posted, date_applied, jd_path, resume_id, resume_score, job_match_summary, application_qnas)
            VALUES (%(url)s, %(resume_path)s, %(role)s, %(company_name)s, %(date_posted)s, DEFAULT, %(jd_path)s, %(resume_id)s, %(resume_score)s, %(job_match_summary)s, %(application_qnas)s)
            ON CONFLICT (url) DO UPDATE SET
                role = EXCLUDED.role,
                company_name = EXCLUDED.company_name,
                resume_path = EXCLUDED.resume_path,
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
                "resume_path": getattr(job, "resume_filepath", None)
                or getattr(job, "resume_path", None),
                "role": job.role,
                "company_name": job.company_name,
                "date_posted": job.date_posted,
                "jd_path": getattr(job, "jd_filepath", None)
                or getattr(job, "jd_path", None),
                "resume_id": resume_id,
                "resume_score": job.resume_score,
                "job_match_summary": getattr(job, "job_match_summary", None)
                or getattr(job, "detailed_explanation", None)
                or "",
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
            INSERT INTO users (name, email, phone, country_code, linkedin, github, location)
            VALUES (%(name)s, %(email)s, %(phone)s, %(country_code)s, %(linkedin)s, %(github)s, %(location)s)
            ON CONFLICT (email) DO UPDATE SET
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                country_code = EXCLUDED.country_code,
                linkedin = EXCLUDED.linkedin,
                github = EXCLUDED.github,
                location = EXCLUDED.location
            RETURNING email
            """,
            {
                "name": contact.name,
                "email": contact.email,
                "phone": contact.phone,
                "country_code": contact.country_code,
                "linkedin": contact.linkedin,
                "github": contact.github,
                "location": contact.location,
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to insert/update user: {contact.email}")
        return result["email"]

    def add_resume_path(self, path: str, user: str) -> int:
        sql = """
            INSERT INTO resumes (id, user_email, path)
            VALUES (DEFAULT, %(user_email)s, %(path)s)
            RETURNING id
        """

        self.cursor.execute(sql, {"user_email": user, "path": path})

        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to insert/update resume: {path}")
        return result["id"]

    def get_resume_path(self, resume_id: int) -> str:
        sql = """
            SELECT path
            FROM resumes
            WHERE id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})

        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"No data found for {resume_id}")

        return result["path"]

    def insert_resume(self, resume: Resume, path: Optional[str] = None) -> int:
        # First, ensure the user exists in the users table
        self.upsert_user(resume.contact)

        # Convert Pydantic models to dicts for JSONB columns
        # Use mode='json' to properly serialize dates and other non-JSON types
        job_exp_dicts = [
            exp.model_dump(mode="json") if hasattr(exp, "model_dump") else exp
            for exp in resume.job_exp
        ]
        education_dicts = [
            edu.model_dump(mode="json") if hasattr(edu, "model_dump") else edu
            for edu in resume.education
        ]
        skills_data = [
            skill.model_dump(mode="json") if hasattr(skill, "model_dump") else skill
            for skill in resume.skills
        ]
        cert_dicts = [
            cert.model_dump(mode="json") if hasattr(cert, "model_dump") else cert
            for cert in resume.certifications
        ]
        projects_dicts = [
            proj.model_dump(mode="json") if hasattr(proj, "model_dump") else proj
            for proj in resume.projects
        ]
        achievements_dicts = [
            ach.model_dump(mode="json") if hasattr(ach, "model_dump") else ach
            for ach in resume.achievements
        ]

        self.cursor.execute(
            """
            INSERT INTO resumes (id, user_email, path, summary, job_experience, education, skills, certifications, projects, achievements)
            VALUES (DEFAULT, %(user_email)s, %(path)s, %(summary)s, %(job_experience)s, %(education)s, %(skills)s, %(certifications)s, %(projects)s, %(achievements)s)
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
                "projects": Json(projects_dicts),
                "achievements": Json(achievements_dicts),
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError("Errored creating resume")
        return result["id"]

    def upsert_resume(self, resume: Resume, path: Optional[str] = None) -> int:
        """Update existing resume by path with parsed data, or insert if not exists."""
        # First, ensure the user exists in the users table
        self.upsert_user(resume.contact)

        # Convert Pydantic models to dicts for JSONB columns
        job_exp_dicts = [
            exp.model_dump(mode="json") if hasattr(exp, "model_dump") else exp
            for exp in resume.job_exp
        ]
        education_dicts = [
            edu.model_dump(mode="json") if hasattr(edu, "model_dump") else edu
            for edu in resume.education
        ]
        skills_data = [
            skill.model_dump(mode="json") if hasattr(skill, "model_dump") else skill
            for skill in resume.skills
        ]
        cert_dicts = [
            cert.model_dump(mode="json") if hasattr(cert, "model_dump") else cert
            for cert in resume.certifications
        ]
        projects_dicts = [
            proj.model_dump(mode="json") if hasattr(proj, "model_dump") else proj
            for proj in resume.projects
        ]
        achievements_dicts = [
            ach.model_dump(mode="json") if hasattr(ach, "model_dump") else ach
            for ach in resume.achievements
        ]

        self.cursor.execute(
            """
            UPDATE resumes
            SET user_email = %(user_email)s,
                summary = %(summary)s,
                job_experience = %(job_experience)s,
                education = %(education)s,
                skills = %(skills)s,
                certifications = %(certifications)s,
                projects = %(projects)s,
                achievements = %(achievements)s
            WHERE path = %(path)s
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
                "projects": Json(projects_dicts),
                "achievements": Json(achievements_dicts),
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to upsert resume for path: {path}")
        return result["id"]

    def list_contact(self, resume_id: int) -> list[dict]:
        """
        Get contact details for a resume by joining with users table.
        Returns list with one contact dict that can be unpacked into Contact model.
        """
        sql = """
            SELECT u.name, u.email, u.phone, u.country_code, u.linkedin, u.github, u.location
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

    def list_projects(self, resume_id: int) -> list[dict]:
        """
        Get projects array from resume JSONB column.
        Returns list of project dictionaries.
        """
        sql = """
            SELECT projects FROM resumes
            WHERE id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()

        if not result or not result["projects"]:
            return []

        projects = result["projects"]
        return projects if isinstance(projects, list) else []

    def list_achievements(self, resume_id: int) -> list[dict]:
        """
        Get achievements array from resume JSONB column.
        Returns list of achievement dictionaries.
        """
        sql = """
            SELECT achievements FROM resumes
            WHERE id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()

        if not result or not result["achievements"]:
            return []

        achievements = result["achievements"]
        return achievements if isinstance(achievements, list) else []

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

    def get_jd_resume(self, url: str) -> dict[str]:
        """
        Get job description file path for a job URL.
        Returns path string or None.
        """
        sql = """
            SELECT jd_path, resume_id
            FROM jobs
            WHERE url=%(url)s
        """

        self.cursor.execute(sql, {"url": url})
        result = self.cursor.fetchone()

        return result if result else None

    def get_resume(self, url: str) -> Optional[str]:
        """
        Get tailored resume file path for a job URL.
        Returns path string or None.
        """
        sql = """
            SELECT resume_path
            FROM jobs
            WHERE url=%(url)s
        """

        self.cursor.execute(sql, {"url": url})
        result = self.cursor.fetchone()

        return result["resume_path"] if result else None

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
            user_data.model_dump(),
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(
                f"Failed to insert/update user data: {user_data.email_address}"
            )
        return result["email"]

    def get_candidate_data(
        self, resume_id: int, resume_path: Optional[str] = None
    ) -> dict:
        """
        Get combined candidate data formatted for JobApplicationAgent.
        Returns dict with all candidate information in flat structure.

        Args:
            resume_id: Resume ID to fetch
            resume_path: Path to resume file. Defaults to 'data/resumes/aws/shashank_reddy.pdf'
        """
        # Get contact info
        contact_list = self.list_contact(resume_id)
        if not contact_list:
            raise RuntimeError(f"Resume {resume_id} not found")

        contact = contact_list[0]

        # Get resume path from database or use default
        sql_resume_path = """
            SELECT path FROM resumes WHERE id = %(resume_id)s
        """
        self.cursor.execute(sql_resume_path, {"resume_id": resume_id})
        resume_result = self.cursor.fetchone()

        if resume_path is None:
            if resume_result and resume_result.get("path"):
                resume_path = resume_result["path"]
            else:
                resume_path = "data/resumes/aws/shashank_reddy.pdf"

        # Parse name into first/last
        full_name = contact.get("name", "")
        name_parts = full_name.split(maxsplit=1)
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Build candidate data structure for agent
        country_code = contact.get("country_code", "+1")
        phone = contact.get("phone", "")
        full_phone = f"{country_code} {phone}" if phone else ""

        candidate_data = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": contact.get("email", ""),
            "phone": phone,
            "country_code": country_code,
            "phone_number": full_phone,  # Full formatted phone with country code
            "location": contact.get("location", ""),
            "linkedin_url": contact.get("linkedin", ""),
            "github_url": contact.get("github", ""),
            "resume_path": resume_path,
        }

        # Get resume components for the resume_text field
        summary = self.get_summary(resume_id)
        job_exps = self.list_job_exps(resume_id)
        skills = self.list_skills(resume_id)
        education = self.list_education(resume_id)
        projects = self.list_projects(resume_id)
        achievements = self.list_achievements(resume_id)

        # Build resume text for answering questions
        resume_text_parts = []
        if summary:
            resume_text_parts.append(f"Summary:\n{summary}\n")

        if job_exps:
            resume_text_parts.append("Experience:")
            for job in job_exps:
                resume_text_parts.append(
                    f"- {job.get('job_title', '')} at {job.get('company_name', '')}"
                )
                if job.get("experience"):
                    for exp in job["experience"]:
                        resume_text_parts.append(f"  • {exp}")
            resume_text_parts.append("")

        if skills:
            resume_text_parts.append("Skills:")
            for skill in skills:
                resume_text_parts.append(
                    f"- {skill.get('title', '')}: {skill.get('skills', '')}"
                )
            resume_text_parts.append("")

        if projects:
            resume_text_parts.append("Projects:")
            for proj in projects:
                resume_text_parts.append(
                    f"- {proj.get('title', '')}: {proj.get('description', '')}"
                )
            resume_text_parts.append("")

        if achievements:
            resume_text_parts.append("Achievements:")
            for ach in achievements:
                resume_text_parts.append(
                    f"- {ach.get('title', '')}: {ach.get('description', '')}"
                )
            resume_text_parts.append("")

        candidate_data["resume_text"] = "\n".join(resume_text_parts)
        candidate_data["skills"] = (
            [s.get("skills", "") for s in skills] if skills else []
        )
        candidate_data["education"] = education if education else []
        candidate_data["projects"] = projects if projects else []
        candidate_data["achievements"] = achievements if achievements else []

        # Get user application data
        sql = """
            SELECT * FROM user_data
            WHERE email = %(email)s
        """
        self.cursor.execute(sql, {"email": contact["email"]})
        user_data_result = self.cursor.fetchone()

        # Merge user_data if exists
        if user_data_result:
            user_data = dict(user_data_result)
            # Add relevant fields from user_data
            candidate_data["years_of_experience"] = 5  # TODO: Calculate from job_exps
            candidate_data["work_authorization"] = (
                "Yes" if user_data.get("work_eligible_us") else "No"
            )
            candidate_data["requires_sponsorship"] = user_data.get(
                "visa_sponsorship", False
            )
            candidate_data["desired_salary"] = user_data.get("desired_salary", "")
            candidate_data["available_start_date"] = user_data.get(
                "available_start_date", ""
            )
            candidate_data["willing_to_relocate"] = user_data.get(
                "willing_relocate", False
            )

            # Add full user_data for additional fields
            candidate_data["user_data"] = user_data

        return candidate_data

    def insert_conversation(
        self,
        session_id: str,
        user_email: str,
        job_url: Optional[str],
        endpoint: str,
        agent_type: str,
        messages: list,
        usage_metrics: dict,
        iterations: int,
        success: bool,
        error_message: Optional[str] = None,
    ) -> int:
        """
        Insert agent conversation history into the database.
        Returns the conversation ID.
        """
        self.cursor.execute(
            """
            INSERT INTO conversations (
                session_id, user_email, job_url, endpoint, agent_type,
                messages, usage_metrics, iterations, success, error_message
            )
            VALUES (
                %(session_id)s, %(user_email)s, %(job_url)s, %(endpoint)s,
                %(agent_type)s, %(messages)s, %(usage_metrics)s,
                %(iterations)s, %(success)s, %(error_message)s
            )
            RETURNING id
            """,
            {
                "session_id": session_id,
                "user_email": user_email,
                "job_url": job_url,
                "endpoint": endpoint,
                "agent_type": agent_type,
                "messages": Json(messages),
                "usage_metrics": Json(usage_metrics),
                "iterations": iterations,
                "success": success,
                "error_message": error_message,
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError("Failed to insert conversation")
        return result["id"]

    def get_user_email_by_resume(self, resume_id: int) -> Optional[str]:
        """
        Get user email for a given resume ID.
        Returns email string or None.
        """
        sql = """
            SELECT user_email FROM resumes
            WHERE id = %(resume_id)s
        """
        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()
        return result["user_email"] if result else None

    def create_application_session(
        self,
        session_id: str,
        job_url: str,
        resume_id: int,
        status: str = "queued",
        screenshot_dir: Optional[str] = None,
    ) -> str:
        """
        Create new application session for real-time monitoring.
        Returns the session_id.
        """
        self.cursor.execute(
            """
            INSERT INTO job_application_sessions (
                session_id, job_url, resume_id, status, screenshot_dir
            )
            VALUES (
                %(session_id)s, %(job_url)s, %(resume_id)s, %(status)s, %(screenshot_dir)s
            )
            RETURNING session_id
            """,
            {
                "session_id": session_id,
                "job_url": job_url,
                "resume_id": resume_id,
                "status": status,
                "screenshot_dir": screenshot_dir,
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to create application session: {session_id}")
        return result["session_id"]

    def get_application_session(self, session_id: str) -> Optional[dict]:
        """
        Get application session details.
        Returns session dict or None.
        """
        sql = """
            SELECT * FROM job_application_sessions
            WHERE session_id = %(session_id)s
        """
        self.cursor.execute(sql, {"session_id": session_id})
        return self.cursor.fetchone()

    def update_session_status(
        self,
        session_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> str:
        """
        Update application session status.
        Returns the session_id.
        """
        if error:
            self.cursor.execute(
                """
                UPDATE job_application_sessions
                SET status = %(status)s,
                    error_message = %(error)s,
                    updated_at = now(),
                    completed_at = CASE WHEN %(status)s IN ('completed', 'failed') THEN now() ELSE completed_at END
                WHERE session_id = %(session_id)s
                RETURNING session_id
                """,
                {"session_id": session_id, "status": status, "error": error},
            )
        else:
            self.cursor.execute(
                """
                UPDATE job_application_sessions
                SET status = %(status)s,
                    updated_at = now(),
                    completed_at = CASE WHEN %(status)s IN ('completed', 'failed') THEN now() ELSE completed_at END
                WHERE session_id = %(session_id)s
                RETURNING session_id
                """,
                {"session_id": session_id, "status": status},
            )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to update session status: {session_id}")
        return result["session_id"]

    def update_session_step(
        self,
        session_id: str,
        step: str,
        thought: Optional[str] = None,
    ) -> str:
        """
        Update current step and thought for a session.
        Returns the session_id.
        """
        if thought:
            self.cursor.execute(
                """
                UPDATE job_application_sessions
                SET current_step = %(step)s,
                    current_thought = %(thought)s,
                    updated_at = now()
                WHERE session_id = %(session_id)s
                RETURNING session_id
                """,
                {"session_id": session_id, "step": step, "thought": thought},
            )
        else:
            self.cursor.execute(
                """
                UPDATE job_application_sessions
                SET current_step = %(step)s,
                    updated_at = now()
                WHERE session_id = %(session_id)s
                RETURNING session_id
                """,
                {"session_id": session_id, "step": step},
            )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to update session step: {session_id}")
        return result["session_id"]

    def update_session_tab_index(self, session_id: str, tab_index: int) -> str:
        """
        Update browser tab index for VNC focusing.
        Returns the session_id.
        """
        self.cursor.execute(
            """
            UPDATE job_application_sessions
            SET tab_index = %(tab_index)s,
                updated_at = now()
            WHERE session_id = %(session_id)s
            RETURNING session_id
            """,
            {"session_id": session_id, "tab_index": tab_index},
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to update session tab index: {session_id}")
        return result["session_id"]

    def insert_timeline_event(
        self,
        session_id: str,
        event_type: str,
        content: str,
        metadata: Optional[dict] = None,
        screenshot_path: Optional[str] = None,
    ) -> int:
        """
        Insert timeline event for application session.
        Returns the event ID.
        """
        self.cursor.execute(
            """
            INSERT INTO application_timeline_events (
                session_id, event_type, content, metadata, screenshot_path
            )
            VALUES (
                %(session_id)s, %(event_type)s, %(content)s, %(metadata)s, %(screenshot_path)s
            )
            RETURNING id
            """,
            {
                "session_id": session_id,
                "event_type": event_type,
                "content": content,
                "metadata": Json(metadata) if metadata else None,
                "screenshot_path": screenshot_path,
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError("Failed to insert timeline event")
        return result["id"]

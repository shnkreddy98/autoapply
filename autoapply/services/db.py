import logging
import psycopg2

from psycopg2.extras import RealDictCursor, Json
from datetime import datetime, date, timezone
from contextlib import contextmanager
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
        with Txc() as repo:
            repo.insert_job(...)
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

    def upsert_user(self, contact: Contact) -> int:
        """
        Insert or update user from resume contact info.
        Returns the user's id.
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
            RETURNING id
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
        return result["id"]

    def add_resume_path(self, path: str, user_id: int) -> int:
        sql = """
            INSERT INTO resumes (user_id, path)
            VALUES (%(user_id)s, %(path)s)
            RETURNING id
        """
        self.cursor.execute(sql, {"user_id": user_id, "path": path})
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to insert resume path: {path}")
        return result["id"]

    def get_user_id_by_email(self, email: str) -> Optional[int]:
        self.cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        result = self.cursor.fetchone()
        return result["id"] if result else None

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

    def _build_parsed(self, resume: Resume) -> dict:
        return {
            "summary": resume.summary,
            "experience": [
                exp.model_dump(mode="json") if hasattr(exp, "model_dump") else exp
                for exp in resume.job_exp
            ],
            "education": [
                edu.model_dump(mode="json") if hasattr(edu, "model_dump") else edu
                for edu in resume.education
            ],
            "skills": [
                skill.model_dump(mode="json") if hasattr(skill, "model_dump") else skill
                for skill in resume.skills
            ],
            "certifications": [
                cert.model_dump(mode="json") if hasattr(cert, "model_dump") else cert
                for cert in resume.certifications
            ],
            "projects": [
                proj.model_dump(mode="json") if hasattr(proj, "model_dump") else proj
                for proj in resume.projects
            ],
            "achievements": [
                ach.model_dump(mode="json") if hasattr(ach, "model_dump") else ach
                for ach in resume.achievements
            ],
        }

    def insert_resume(self, resume: Resume, path: Optional[str] = None) -> int:
        user_id = self.upsert_user(resume.contact)
        parsed = self._build_parsed(resume)
        self.cursor.execute(
            """
            INSERT INTO resumes (user_id, path, parsed)
            VALUES (%(user_id)s, %(path)s, %(parsed)s)
            RETURNING id
            """,
            {"user_id": user_id, "path": path, "parsed": Json(parsed)},
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError("Errored creating resume")
        return result["id"]

    def upsert_resume(self, resume: Resume, path: Optional[str] = None) -> int:
        """Update existing resume by path with parsed data, or insert if not exists."""
        user_id = self.upsert_user(resume.contact)
        parsed = self._build_parsed(resume)
        self.cursor.execute(
            """
            UPDATE resumes
            SET user_id = %(user_id)s,
                parsed = %(parsed)s
            WHERE path = %(path)s
            RETURNING id
            """,
            {"user_id": user_id, "path": path, "parsed": Json(parsed)},
        )
        result = self.cursor.fetchone()
        if result:
            return result["id"]
        # No existing row — insert fresh
        self.cursor.execute(
            "INSERT INTO resumes (user_id, path, parsed) VALUES (%(user_id)s, %(path)s, %(parsed)s) RETURNING id",
            {"user_id": user_id, "path": path, "parsed": Json(parsed)},
        )
        return self.cursor.fetchone()["id"]

    def list_resumes(self) -> list[dict]:
        sql = """
            SELECT id, user_id, path
            FROM resumes
            ORDER BY id DESC
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def list_contact(self, resume_id: int) -> list[dict]:
        sql = """
            SELECT u.name, u.email, u.phone, u.country_code, u.linkedin, u.github, u.location
            FROM resumes r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = %(resume_id)s
        """
        self.cursor.execute(sql, {"resume_id": resume_id})
        return self.cursor.fetchall()

    def list_job_exps(self, resume_id: int) -> list[dict]:
        self.cursor.execute(
            "SELECT parsed->'experience' AS experience FROM resumes WHERE id=%(resume_id)s",
            {"resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        if not result or not result["experience"]:
            return []
        jobs = result["experience"]
        if isinstance(jobs, list):
            for job in jobs:
                if isinstance(job.get("to_date"), str) and job["to_date"].lower() not in [
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
        self.cursor.execute(
            "SELECT parsed->'education' AS education FROM resumes WHERE id=%(resume_id)s",
            {"resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        if not result or not result["education"]:
            return []
        education = result["education"]
        return education if isinstance(education, list) else []

    def list_certifications(self, resume_id: int) -> list[dict]:
        self.cursor.execute(
            "SELECT parsed->'certifications' AS certifications FROM resumes WHERE id=%(resume_id)s",
            {"resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        if not result or not result["certifications"]:
            return []
        certifications = result["certifications"]
        return certifications if isinstance(certifications, list) else []

    def list_skills(self, resume_id: int) -> list[dict]:
        self.cursor.execute(
            "SELECT parsed->'skills' AS skills FROM resumes WHERE id=%(resume_id)s",
            {"resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        if not result or not result["skills"]:
            return []
        skills = result["skills"]
        return skills if isinstance(skills, (list, dict)) else []

    def get_summary(self, resume_id: int) -> Optional[str]:
        self.cursor.execute(
            "SELECT parsed->>'summary' AS summary FROM resumes WHERE id=%(resume_id)s",
            {"resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        return result["summary"] if result else None

    def list_projects(self, resume_id: int) -> list[dict]:
        self.cursor.execute(
            "SELECT parsed->'projects' AS projects FROM resumes WHERE id=%(resume_id)s",
            {"resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        if not result or not result["projects"]:
            return []
        projects = result["projects"]
        return projects if isinstance(projects, list) else []

    def list_achievements(self, resume_id: int) -> list[dict]:
        self.cursor.execute(
            "SELECT parsed->'achievements' AS achievements FROM resumes WHERE id=%(resume_id)s",
            {"resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        if not result or not result["achievements"]:
            return []
        achievements = result["achievements"]
        return achievements if isinstance(achievements, list) else []

    def insert_job(self, job: Job, resume_id: int) -> str:
        """
        Upsert job posting then upsert application.
        Returns the URL of the inserted/updated job.
        """
        # Derive user_id from resume
        self.cursor.execute(
            "SELECT user_id FROM resumes WHERE id = %(resume_id)s",
            {"resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Resume not found: {resume_id}")
        user_id = result["user_id"]

        # Upsert job posting
        self.cursor.execute(
            """
            INSERT INTO jobs (url, role, company, date_posted, jd_path)
            VALUES (%(url)s, %(role)s, %(company)s, %(date_posted)s, %(jd_path)s)
            ON CONFLICT (url) DO UPDATE SET
                role = EXCLUDED.role,
                company = EXCLUDED.company,
                date_posted = EXCLUDED.date_posted,
                jd_path = EXCLUDED.jd_path
            RETURNING url
            """,
            {
                "url": job.url,
                "role": job.role,
                "company": job.company_name,
                "date_posted": job.date_posted,
                "jd_path": getattr(job, "jd_filepath", None) or getattr(job, "jd_path", None),
            },
        )

        # Upsert application
        self.cursor.execute(
            """
            INSERT INTO applications (user_id, job_url, resume_id, resume_path, status, score, match_summary, qnas)
            VALUES (%(user_id)s, %(job_url)s, %(resume_id)s, %(resume_path)s, 'pending', %(score)s, %(match_summary)s, %(qnas)s)
            ON CONFLICT (user_id, job_url) DO UPDATE SET
                resume_id = EXCLUDED.resume_id,
                resume_path = EXCLUDED.resume_path,
                score = EXCLUDED.score,
                match_summary = EXCLUDED.match_summary,
                qnas = EXCLUDED.qnas
            """,
            {
                "user_id": user_id,
                "job_url": job.url,
                "resume_id": resume_id,
                "resume_path": getattr(job, "resume_filepath", None) or getattr(job, "resume_path", None),
                "score": job.resume_score,
                "match_summary": job.job_match_summary,
                "qnas": Json(job.application_qnas if job.application_qnas else []),
            },
        )
        return job.url

    def list_jobs(self, date: Optional[date] = None) -> list[dict]:
        if date:
            sql = """
                SELECT j.*, a.*
                FROM jobs j
                JOIN applications a ON a.job_url = j.url
                WHERE DATE_TRUNC('day', a.date_applied AT TIME ZONE 'UTC') = %(date)s::date
                ORDER BY a.date_applied DESC
            """
            self.cursor.execute(sql, {"date": date})
        else:
            sql = """
                SELECT j.*, a.*
                FROM jobs j
                JOIN applications a ON a.job_url = j.url
                ORDER BY a.date_applied DESC
            """
            self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_jd_resume(self, url: str) -> Optional[dict]:
        sql = """
            SELECT j.jd_path, a.resume_id
            FROM jobs j
            JOIN applications a ON a.job_url = j.url
            WHERE j.url = %(url)s
        """
        self.cursor.execute(sql, {"url": url})
        result = self.cursor.fetchone()
        return result if result else None

    def get_resume(self, url: str) -> Optional[str]:
        sql = """
            SELECT resume_path
            FROM applications
            WHERE job_url = %(url)s
        """
        self.cursor.execute(sql, {"url": url})
        result = self.cursor.fetchone()
        return result["resume_path"] if result else None

    def update_qnas(self, qnas: Union[dict, list], url: str) -> str:
        self.cursor.execute(
            """
            UPDATE applications
            SET qnas = %(qnas)s
            WHERE job_url = %(url)s
            RETURNING job_url
            """,
            {"url": url, "qnas": Json(qnas)},
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Application not found for job: {url}")
        return result["job_url"]

    def fill_user_information(self, user_data: UserOnboarding) -> str:
        """
        Insert or update autofill data for a user.
        Returns the user's email address.
        """
        self.cursor.execute(
            "SELECT id FROM users WHERE email = %(email)s",
            {"email": user_data.email_address},
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"User not found: {user_data.email_address}")
        user_id = result["id"]

        certs = {
            "cert_accuracy": user_data.cert_accuracy,
            "cert_dismissal": user_data.cert_dismissal,
            "cert_background_check": user_data.cert_background_check,
            "cert_drug_testing": user_data.cert_drug_testing,
            "cert_at_will": user_data.cert_at_will,
            "cert_job_description": user_data.cert_job_description,
            "cert_privacy_notice": user_data.cert_privacy_notice,
            "cert_data_processing": user_data.cert_data_processing,
        }

        def _enum_val(v):
            return v.value if v is not None and hasattr(v, "value") else v

        self.cursor.execute(
            """
            INSERT INTO autofill (
                user_id, full_name, street_address, city, state, zip_code,
                date_of_birth, age_18_or_older, work_eligible_us, visa_sponsorship,
                available_start_date, employment_type, willing_relocate, willing_travel,
                travel_percentage, desired_salary, gender, race_ethnicity, veteran_status,
                disability_status, current_employee, ever_terminated, termination_explanation,
                security_clearance, certs, electronic_signature, signature_date
            )
            VALUES (
                %(user_id)s, %(full_name)s, %(street_address)s, %(city)s, %(state)s, %(zip_code)s,
                %(date_of_birth)s, %(age_18_or_older)s, %(work_eligible_us)s, %(visa_sponsorship)s,
                %(available_start_date)s, %(employment_type)s, %(willing_relocate)s, %(willing_travel)s,
                %(travel_percentage)s, %(desired_salary)s, %(gender)s, %(race_ethnicity)s, %(veteran_status)s,
                %(disability_status)s, %(current_employee)s, %(ever_terminated)s, %(termination_explanation)s,
                %(security_clearance)s, %(certs)s, %(electronic_signature)s, %(signature_date)s
            )
            ON CONFLICT (user_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                street_address = EXCLUDED.street_address,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                zip_code = EXCLUDED.zip_code,
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
                certs = EXCLUDED.certs,
                electronic_signature = EXCLUDED.electronic_signature,
                signature_date = EXCLUDED.signature_date
            RETURNING user_id
            """,
            {
                "user_id": user_id,
                "full_name": user_data.full_name,
                "street_address": user_data.street_address,
                "city": user_data.city,
                "state": user_data.state,
                "zip_code": user_data.zip_code,
                "date_of_birth": user_data.date_of_birth,
                "age_18_or_older": user_data.age_18_or_older,
                "work_eligible_us": user_data.work_eligible_us,
                "visa_sponsorship": user_data.visa_sponsorship,
                "available_start_date": user_data.available_start_date,
                "employment_type": _enum_val(user_data.employment_type),
                "willing_relocate": user_data.willing_relocate,
                "willing_travel": user_data.willing_travel,
                "travel_percentage": user_data.travel_percentage,
                "desired_salary": user_data.desired_salary,
                "gender": _enum_val(user_data.gender),
                "race_ethnicity": _enum_val(user_data.race_ethnicity),
                "veteran_status": _enum_val(user_data.veteran_status),
                "disability_status": _enum_val(user_data.disability_status),
                "current_employee": user_data.current_employee,
                "ever_terminated": user_data.ever_terminated,
                "termination_explanation": user_data.termination_explanation,
                "security_clearance": _enum_val(user_data.security_clearance),
                "certs": Json(certs),
                "electronic_signature": user_data.electronic_signature,
                "signature_date": user_data.signature_date,
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to insert/update autofill: {user_data.email_address}")
        return user_data.email_address

    def get_candidate_data(self, resume_id: int, resume_path: Optional[str] = None) -> dict:
        """
        Get combined candidate data formatted for JobApplicationAgent.
        Returns dict with all candidate information.
        """
        self.cursor.execute(
            """
            SELECT r.parsed, r.path, u.id AS user_id,
                   u.name, u.email, u.phone, u.country_code,
                   u.linkedin, u.github, u.location
            FROM resumes r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = %(resume_id)s
            """,
            {"resume_id": resume_id},
        )
        row = self.cursor.fetchone()
        if not row:
            raise RuntimeError(f"Resume {resume_id} not found")

        if resume_path is None:
            resume_path = row["path"] or "data/resumes/aws/shashank_reddy.pdf"

        parsed = row["parsed"] or {}
        full_name = row["name"] or ""
        name_parts = full_name.split(maxsplit=1)
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        country_code = row["country_code"] or "+1"
        phone = row["phone"] or ""
        full_phone = f"{country_code} {phone}" if phone else ""

        summary = parsed.get("summary", "")
        job_exps = parsed.get("experience", [])
        skills = parsed.get("skills", [])
        education = parsed.get("education", [])
        projects = parsed.get("projects", [])
        achievements = parsed.get("achievements", [])

        resume_text_parts = []
        if summary:
            resume_text_parts.append(f"Summary:\n{summary}\n")
        if job_exps:
            resume_text_parts.append("Experience:")
            for job in job_exps:
                resume_text_parts.append(
                    f"- {job.get('job_title', '')} at {job.get('company_name', '')}"
                )
                for exp in job.get("experience", []):
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

        candidate_data = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": row["email"],
            "phone": phone,
            "country_code": country_code,
            "phone_number": full_phone,
            "location": row["location"],
            "linkedin_url": row["linkedin"],
            "github_url": row["github"],
            "resume_path": resume_path,
            "resume_text": "\n".join(resume_text_parts),
            "skills": [s.get("skills", "") for s in skills] if skills else [],
            "education": education,
            "projects": projects,
            "achievements": achievements,
        }

        self.cursor.execute(
            "SELECT * FROM autofill WHERE user_id = %(user_id)s",
            {"user_id": row["user_id"]},
        )
        autofill = self.cursor.fetchone()

        if autofill:
            af = dict(autofill)
            certs = af.get("certs") or {}
            candidate_data["years_of_experience"] = 5  # TODO: Calculate from job_exps
            candidate_data["work_authorization"] = "Yes" if af.get("work_eligible_us") else "No"
            candidate_data["requires_sponsorship"] = af.get("visa_sponsorship", False)
            candidate_data["desired_salary"] = af.get("desired_salary", "")
            candidate_data["available_start_date"] = af.get("available_start_date", "")
            candidate_data["willing_to_relocate"] = af.get("willing_relocate", False)
            af.update(certs)
            candidate_data["user_data"] = af

        return candidate_data

    def get_user_email_by_resume(self, resume_id: int) -> Optional[str]:
        sql = """
            SELECT u.email
            FROM resumes r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = %(resume_id)s
        """
        self.cursor.execute(sql, {"resume_id": resume_id})
        result = self.cursor.fetchone()
        return result["email"] if result else None

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
        Insert agent run record into agent_runs.
        Returns the run id.
        """
        application_id = None
        if job_url:
            self.cursor.execute(
                """
                SELECT a.id FROM applications a
                JOIN users u ON a.user_id = u.id
                WHERE a.job_url = %(job_url)s AND u.email = %(user_email)s
                """,
                {"job_url": job_url, "user_email": user_email},
            )
            result = self.cursor.fetchone()
            if result:
                application_id = result["id"]

        merged_metrics = {**usage_metrics, "endpoint": endpoint}

        self.cursor.execute(
            """
            INSERT INTO agent_runs (
                application_id, agent_type, iterations, model,
                messages, usage_metrics, success, error_message
            )
            VALUES (
                %(application_id)s, %(agent_type)s, %(iterations)s, %(model)s,
                %(messages)s, %(usage_metrics)s, %(success)s, %(error_message)s
            )
            RETURNING id
            """,
            {
                "application_id": application_id,
                "agent_type": agent_type,
                "iterations": iterations,
                "model": endpoint,
                "messages": Json(messages),
                "usage_metrics": Json(merged_metrics),
                "success": success,
                "error_message": error_message,
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError("Failed to insert agent run")
        return result["id"]

    def create_application_session(
        self,
        session_id: str,
        job_url: str,
        resume_id: int,
        status: str = "running",
        screenshot_dir: Optional[str] = None,
    ) -> str:
        """
        Create new browser session for real-time monitoring.
        Returns the session_id.
        """
        self.cursor.execute(
            "SELECT id FROM applications WHERE job_url = %(job_url)s AND resume_id = %(resume_id)s",
            {"job_url": job_url, "resume_id": resume_id},
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(
                f"Application not found for job_url={job_url}, resume_id={resume_id}"
            )
        application_id = result["id"]

        self.cursor.execute(
            """
            INSERT INTO browser_sessions (session_id, application_id, status, screenshot_dir)
            VALUES (%(session_id)s, %(application_id)s, %(status)s, %(screenshot_dir)s)
            RETURNING session_id
            """,
            {
                "session_id": session_id,
                "application_id": application_id,
                "status": status,
                "screenshot_dir": screenshot_dir,
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to create browser session: {session_id}")
        return result["session_id"]

    def get_application_session(self, session_id: str) -> Optional[dict]:
        sql = """
            SELECT * FROM browser_sessions
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
        self.cursor.execute(
            """
            UPDATE browser_sessions
            SET status = %(status)s,
                error_message = %(error)s,
                updated_at = now(),
                completed_at = CASE WHEN %(status)s IN ('completed', 'failed') THEN now() ELSE completed_at END
            WHERE session_id = %(session_id)s
            RETURNING session_id
            """,
            {"session_id": session_id, "status": status, "error": error},
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
        self.cursor.execute(
            """
            UPDATE browser_sessions
            SET current_step = %(step)s,
                current_thought = %(thought)s,
                updated_at = now()
            WHERE session_id = %(session_id)s
            RETURNING session_id
            """,
            {"session_id": session_id, "step": step, "thought": thought},
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to update session step: {session_id}")
        return result["session_id"]

    def update_session_tab_index(self, session_id: str, tab_index: int) -> str:
        self.cursor.execute(
            """
            UPDATE browser_sessions
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
    ) -> None:
        """
        Append a timeline event to browser_sessions.events JSONB array.
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": content,
            "metadata": metadata,
            "screenshot_path": screenshot_path,
        }
        self.cursor.execute(
            """
            UPDATE browser_sessions
            SET events = events || %(event)s::jsonb
            WHERE session_id = %(session_id)s
            """,
            {"session_id": session_id, "event": Json([event])},
        )

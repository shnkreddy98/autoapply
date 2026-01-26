import logging
import psycopg2

from psycopg2.extras import RealDictCursor, Json
from contextlib import contextmanager
from datetime import date
from typing import Optional

from autoapply.env import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from autoapply.models import (
    Contact,
    Job,
    JobExperience,
    Education,
    Certification,
    Skills,
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

    def insert_job(self, job: Job) -> str:
        """
        Insert or update job post.
        Returns the URL of the inserted/updated job.
        """
        self.cursor.execute(
            """
            INSERT INTO jobs (url, role, company_name, date_posted, date_applied, jd_filepath, cloud, resume_filepath, resume_score, detailed_explanation)
            VALUES (%(url)s, %(role)s, %(company_name)s, %(date_posted)s, %(date_applied)s, %(jd_filepath)s, %(cloud)s, %(resume_filepath)s, %(resume_score)s, %(detailed_explanation)s)
            ON CONFLICT (url) DO UPDATE SET
                role = EXCLUDED.role,
                company_name = EXCLUDED.company_name,
                date_posted = EXCLUDED.date_posted,
                date_applied = EXCLUDED.date_applied,
                jd_filepath = EXCLUDED.jd_filepath,
                cloud = EXCLUDED.cloud,
                resume_filepath = EXCLUDED.resume_filepath,
                resume_score = EXCLUDED.resume_score,
                detailed_explanation = EXCLUDED.detailed_explanation
            RETURNING url
            """,
            {
                "url": job.url,
                "role": job.role,
                "company_name": job.company_name,
                "date_posted": job.date_posted,
                "date_applied": job.date_applied,
                "jd_filepath": job.jd_filepath,
                "cloud": job.cloud,
                "resume_filepath": job.resume_filepath,
                "resume_score": job.resume_score,
                "detailed_explanation": job.detailed_explanation,
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
        List all jobs, optionally filtered by date posted.
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

    def insert_resume(self) -> int:
        self.cursor.execute(
            """
            INSERT INTO resume_no DEFAULT VALUES
            RETURNING id
            """
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError("Errored creating resume")
        return result["id"]

    def insert_contact_details(self, resume_id: int, contact: Contact) -> None:
        self.cursor.execute(
            """
            INSERT INTO contact (name, email, location, phone, linkedin, github, resume_id)
            VALUES (%(name)s, %(email)s, %(location)s, %(phone)s, %(linkedin)s, %(github)s, %(resume_id)s)
            """,
            {
                "name": contact.name,
                "email": contact.email,
                "location": contact.location,
                "phone": contact.phone,
                "linkedin": contact.linkedin,
                "github": contact.github,
                "resume_id": resume_id
            },
        )


    def insert_job_exp(self, resume_id: int, job_exp: list[JobExperience]) -> None:
        for job in job_exp:
            self.cursor.execute(
                """
                INSERT INTO job_experience (company_name, job_title, location, from_date, to_date, experience, resume_id)
                VALUES (%(company_name)s, %(job_title)s, %(location)s, %(from_date)s, %(to_date)s, %(experience)s, %(resume_id)s)
                """,
                {
                    "company_name": job.company_name,
                    "job_title": job.job_title,
                    "location": job.location,
                    "from_date": job.from_,
                    "to_date": job.to_,
                    "experience": Json(job.experience),
                    "resume_id": resume_id
                },
            )

    def insert_education(self, resume_id: int, education_list: list[Education]) -> None:
        for education in education_list:
            self.cursor.execute(
                """
                INSERT INTO education (degree, major, college, from_date, to_date, resume_id)
                VALUES (%(degree)s, %(major)s, %(college)s, %(from_date)s, %(to_date)s, %(resume_id)s)
                """,
                {
                    "degree": education.degree,
                    "major": education.major,
                    "college": education.college,
                    "from_date": education.from_,
                    "to_date": education.to_,
                    "resume_id": resume_id
                },
            )

    def insert_skills(self, resume_id: int, skills: list[Skills]) -> None:
        for skill in skills:
            self.cursor.execute(
                """
                INSERT INTO skills (title, skills, resume_id)
                VALUES (%(title)s, %(skills)s, %(resume_id)s)
                """,
                {
                    "title": skill.title,
                    "skills": Json(skill.skills),
                    "resume_id": resume_id
                },
            )

    def insert_certifications(self, resume_id: int, certifications: list[Certification]) -> None:
        for certification in certifications:
            self.cursor.execute(
                """
                INSERT INTO certifications (title, obtained_date, expiry_date, resume_id)
                VALUES (%(title)s, %(obtained_date)s, %(expiry_date)s, %(resume_id)s)
                """,
                {
                    "title": certification.title,
                    "obtained_date": certification.obtained_date,
                    "expiry_date": certification.expiry_date,
                    "resume_id": resume_id
                },
            )


    def list_contact(
        self,
        resume_id: int
    ) -> list[tuple]:
        sql = """
            SELECT * FROM contact
            WHERE resume_id=%(resume_id)s
        """
        
        self.cursor.execute(sql, {"resume_id": resume_id})

        return self.cursor.fetchall()

    def list_job_exps(
        self,
        resume_id: int
    ) -> list[tuple]:
        sql = """
            SELECT * FROM job_experience
            WHERE resume_id=%(resume_id)s
        """

        self.cursor.execute(sql, {"resume_id": resume_id})

        results = self.cursor.fetchall()

        # Convert text dates to date objects where applicable
        from datetime import datetime
        for job in results:
            if isinstance(job['to_date'], str) and job['to_date'].lower() not in ['current', 'present']:
                try:
                    # Try to parse the date string
                    parsed_date = datetime.strptime(job['to_date'].strip(), '%Y-%m-%d').date()
                    job['to_date'] = parsed_date
                except (ValueError, AttributeError):
                    # If parsing fails, keep as string
                    pass

        return results

    def list_education(
        self,
        resume_id: int
    ) -> list[tuple]:
        sql = """
            SELECT * FROM education
            WHERE resume_id=%(resume_id)s
        """
        
        self.cursor.execute(sql, {"resume_id": resume_id})

        return self.cursor.fetchall()

    def list_certifications(
        self,
        resume_id: int
    ) -> list[tuple]:
        sql = """
            SELECT * FROM certifications
            WHERE resume_id=%(resume_id)s
        """
        
        self.cursor.execute(sql, {"resume_id": resume_id})

        return self.cursor.fetchall()

    def list_skills(
        self,
        resume_id: int
    ) -> list[tuple]:
        sql = """
            SELECT * FROM skills
            WHERE resume_id=%(resume_id)s
        """
        
        self.cursor.execute(sql, {"resume_id": resume_id})

        return self.cursor.fetchall()
    
    def list_resumes(
        self,
    ) -> list[tuple]:
        sql = """
            SELECT id
            FROM resume_no
        """

        self.cursor.execute(sql)
        return self.cursor.fetchall()



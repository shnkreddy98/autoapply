import logging
import psycopg2

from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import date
from typing import Optional

from autoapply.env import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from autoapply.models import Job
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
            INSERT INTO jobs (url, role, company_name, date_posted, date_applied, jd_filepath, cloud, resume_filepath, resume_score, detailed_explaination)
            VALUES (%(url)s, %(role)s, %(company_name)s, %(date_posted)s, %(date_applied)s, %(jd_filepath)s, %(cloud)s, %(resume_filepath)s, %(resume_score)s, %(detailed_explaination)s)
            ON CONFLICT (url) DO UPDATE SET
                role = EXCLUDED.role,
                company_name = EXCLUDED.company_name,
                date_posted = EXCLUDED.date_posted,
                date_applied = EXCLUDED.date_applied,
                jd_filepath = EXCLUDED.jd_filepath,
                cloud = EXCLUDED.cloud,
                resume_filepath = EXCLUDED.resume_filepath,
                resume_score = EXCLUDED.resume_score,
                detailed_explaination = EXCLUDED.detailed_explaination
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
                "detailed_explaination": job.detailed_explaination,
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

import logging
import psycopg2

from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import date
from typing import Literal, Optional

from autoapply.env import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
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

    def insert_job(
        self, 
        url: str,
        date_applied: date = None,
        role: Optional[str] = None,
        company_name: Optional[str] = None,
        date_posted: Optional[date] = None,
        jd_filepath: Optional[str] = None,
        cloud: Optional[Literal["aws", "gcp", "azu"]] = None,
        resume_filepath: Optional[str] = None,
        resume_score: Optional[float] = None,
    ) -> str:
        """
        Insert or update job post.
        Returns the URL of the inserted/updated job.
        """
        self.cursor.execute(
            """
            INSERT INTO jobs (url, role, company_name, date_posted, date_applied, jd_filepath, cloud, resume_filepath, resume_score)
            VALUES (%(url)s, %(role)s, %(company_name)s, %(date_posted)s, %(date_applied)s, %(jd_filepath)s, %(cloud)s, %(resume_filepath)s, %(resume_score)s)
            ON CONFLICT (url) DO UPDATE SET
                role = EXCLUDED.role,
                company_name = EXCLUDED.company_name,
                date_posted = EXCLUDED.date_posted,
                date_applied = EXCLUDED.date_applied,
                jd_filepath = EXCLUDED.jd_filepath,
                cloud = EXCLUDED.cloud,
                resume_filepath = EXCLUDED.resume_filepath,
                resume_score = EXCLUDED.resume_score
            RETURNING url
            """,
            {
                "url": url,
                "role": role,
                "company_name": company_name,
                "date_posted": date_posted,
                "date_applied": date_applied,
                "jd_filepath": jd_filepath,
                "cloud": cloud,
                "resume_filepath": resume_filepath,
                "resume_score": resume_score
            },
        )
        result = self.cursor.fetchone()
        if not result:
            raise RuntimeError(f"Failed to insert/update job: {url}")
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
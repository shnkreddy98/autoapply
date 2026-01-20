from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date, datetime

class PostJobsParams(BaseModel):
    urls: list[str]

class ListJobsResponse(BaseModel):
    url: str
    role: Optional[str] = None
    company_name: Optional[str] = None
    date_posted: Optional[datetime] = None
    date_applied: date
    jd_filepath: Optional[str] = None
    cloud: Optional[Literal["aws", "gcp", "azu"]] = None
    resume_filepath: Optional[str] = None
    resume_score: Optional[float] = None
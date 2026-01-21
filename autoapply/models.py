from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date


class PostJobsParams(BaseModel):
    urls: list[str]


class LLMResponse(BaseModel):
    url: str = Field(description="URL for the job post")
    role: str = Field(description="Job roles name")
    company_name: str = Field(description="Name of the company that posted the job")
    date_posted: Optional[date] = Field(
        description="Job Posted date if mentioned", default=None
    )
    cloud: Literal["aws", "gcp", "azu"] = Field(
        description="The dominant/prefered cloud technology", default="aws"
    )
    resume_score: float = Field(
        description="The resume score on a scale of 0 to 100", 
        le=100, 
        ge=0
    )
    detailed_explaination: str = Field(
        description="Explaination of how well the resume does for this JD"
    )


class Job(LLMResponse):
    date_applied: date
    jd_filepath: Optional[str] = None
    resume_filepath: Optional[str] = None


class NormalResponse(BaseModel):
    reply: str

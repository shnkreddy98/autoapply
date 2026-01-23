from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date


class PostJobsParams(BaseModel):
    urls: list[str]


class NormalResponse(BaseModel):
    reply: str


class Contact(BaseModel):
    email: str
    location: str
    phone: str
    linkedin: str
    github: str


class Education(BaseModel):
    degree: str
    major: str
    college: str
    from_: date
    to_: date


class JobExperience(BaseModel):
    job_title: str
    company_name: str
    location: str
    from_: date
    to_: date | str
    experience: list[str]


class Skills(BaseModel):
    skills_title: str
    skills: str


class CompanyExperience(BaseModel):
    company_name: str = Field(description="The name of the company as it appears in resume (no role or nothing)")
    experience_points: list[str] = Field(description="List of experience bullet points")


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
        description="The resume score on a scale of 0 to 100", le=100, ge=0
    )
    detailed_explaination: str = Field(
        description="Explaination of how well the resume does for this JD"
    )
    new_summary: str = Field(description="New description if the score is below 80")
    new_job_experience: list[CompanyExperience] = Field(
        description="New set of job experience points old and new based on the new JD for each company in resume if score is below 80"
    )
    new_skills_section: list[Skills] = Field(
        description="New Skills section with new additions of tools if score below 80"
    )
    new_resume_score: float = Field(
        description="New Score after adding the new resume points you suggested."
    )


class Job(BaseModel):
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
        description="The resume score on a scale of 0 to 100", le=100, ge=0
    )
    detailed_explaination: str
    date_applied: date
    jd_filepath: Optional[str] = None
    resume_filepath: Optional[str] = None


def get_gemini_compatible_schema(model: type[BaseModel]) -> dict:
    """
    Generates a JSON schema from a Pydantic model and recursively
    resolves $ref dependencies because Gemini API does not support $defs/$ref.
    """
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            # If we find a reference, define it inline
            if "$ref" in node:
                ref_key = node["$ref"].split("/")[-1]
                if ref_key in defs:
                    # Recursively resolve the referenced definition
                    return resolve(defs[ref_key])
            # Otherwise, just recurse into the dictionary
            return {k: resolve(v) for k, v in node.items()}
        elif isinstance(node, list):
            # Recurse into lists
            return [resolve(item) for item in node]
        return node

    return resolve(schema)

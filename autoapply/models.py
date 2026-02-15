from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date, datetime


class PostJobsParams(BaseModel):
    tailor: bool = Field(
        default=False,
        description="Set to true if you want to tailor the resumes based on JD/job listings",
    )
    urls: list[str]
    resume_id: str = Field(description="Version of the resume uploaded")


class NormalResponse(BaseModel):
    reply: str


class UploadResumeParams(BaseModel):
    path: str


class Contact(BaseModel):
    name: str
    email: str
    location: str
    phone: str
    country_code: str = "+1"
    linkedin: str
    github: str


class Education(BaseModel):
    degree: str
    major: str
    college: str
    from_: date = Field(alias="from_date")
    to_: date = Field(alias="to_date")

    class Config:
        populate_by_name = True


class JobExperience(BaseModel):
    job_title: str
    company_name: str
    location: str
    from_: date = Field(alias="from_date")
    to_: date | str = Field(alias="to_date")
    experience: list[str]

    class Config:
        populate_by_name = True


class Certification(BaseModel):
    title: str
    obtained_date: date
    expiry_date: date | None


class Skills(BaseModel):
    title: str
    skills: str


class CompanyExperience(BaseModel):
    company_name: str = Field(
        description="The name of the company as it appears in resume (no role or nothing)"
    )
    experience_points: list[str] = Field(description="List of experience bullet points")


class TailoredResume(BaseModel):
    role: str = Field(description="Job roles name")
    company_name: str = Field(description="Name of the company that posted the job")
    date_posted: Optional[datetime] = Field(
        description="Job Posted date if mentioned", default=None
    )
    cloud: Literal["aws", "gcp", "azu"] = Field(
        description="The dominant/prefered cloud technology", default="aws"
    )
    resume_score: float = Field(
        description="The resume score on a scale of 0 to 100", le=100, ge=0
    )
    job_match_summary: str = Field(
        description="Explanation of how well the resume does for this JD"
    )
    new_resume_score: float = Field(
        description="New Score after adding the new resume points you suggested."
    )


class Job(BaseModel):
    url: str = Field(description="URL for the job post")
    role: str = Field(description="Job roles name")
    company_name: str = Field(description="Name of the company that posted the job")
    date_posted: Optional[datetime] = Field(
        description="Job Posted date if mentioned", default=None
    )
    cloud: Literal["aws", "gcp", "azu"] = Field(
        description="The dominant/prefered cloud technology", default="aws"
    )
    resume_score: float = Field(
        description="The resume score on a scale of 0 to 100", le=100, ge=0
    )
    job_match_summary: str
    date_applied: datetime
    jd_filepath: Optional[str] = None
    resume_filepath: Optional[str] = None
    application_qnas: Optional[dict] = Field(
        default=None,
        description="Agent doesn't have to fill this, it can be null"
    )


class Resume(BaseModel):
    contact: Contact
    summary: str
    job_exp: list[JobExperience]
    skills: list[Skills]
    education: list[Education]
    certifications: list[Certification]


class ApplicationAnswer(BaseModel):
    questions: str
    answer: str


class ApplicationAnswers(BaseModel):
    all_answers: list[ApplicationAnswer]


class QuestionRequest(BaseModel):
    url: str
    questions: str


class SearchParams(BaseModel):
    role: str = Field(description="Role name to search")
    company: str = Field(
        default="", description="Name of the company to search the roles"
    )
    ats_sites: list[str] = Field(
        default=None, description="List of sites you want to search for"
    )
    pages: int = Field(default=5, description="Number of pages to scrape")
    force: bool = Field(
        default=False, description="Boolean flag which will fetch google cookies"
    )

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum

class EmploymentType(str, Enum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    EITHER = "Either"

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    NON_BINARY = "Non-binary"
    PREFER_NOT_TO_ANSWER = "Prefer not to answer"

class RaceEthnicity(str, Enum):
    HISPANIC_LATINO = "Hispanic or Latino"
    WHITE = "White"
    BLACK_AFRICAN_AMERICAN = "Black or African American"
    ASIAN = "Asian"
    AMERICAN_INDIAN_ALASKA_NATIVE = "American Indian or Alaska Native"
    NATIVE_HAWAIIAN_PACIFIC_ISLANDER = "Native Hawaiian or Other Pacific Islander"
    TWO_OR_MORE_RACES = "Two or More Races"
    PREFER_NOT_TO_ANSWER = "Prefer not to answer"

class VeteranStatus(str, Enum):
    DISABLED_VETERAN = "Disabled veteran"
    RECENTLY_SEPARATED_VETERAN = "Recently separated veteran"
    ACTIVE_WARTIME_VETERAN = "Active wartime veteran"
    ARMED_FORCES_SERVICE_MEDAL_VETERAN = "Armed Forces service medal veteran"
    OTHER_PROTECTED_VETERAN = "Other protected veteran"
    NOT_A_VETERAN = "Not a veteran"
    PREFER_NOT_TO_ANSWER = "Prefer not to answer"

class DisabilityStatus(str, Enum):
    YES = "Yes, I have a disability"
    NO = "No, I do not have a disability"
    PREFER_NOT_TO_ANSWER = "Prefer not to answer"

class YesNoNA(str, Enum):
    YES = "Yes"
    NO = "No"
    NA = "N/A"

class UserOnboarding(BaseModel):
    # Personal Information
    full_name: str = Field(..., description="Full legal name")
    street_address: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    zip_code: str = Field(..., description="ZIP code")
    phone_number: str = Field(..., description="Phone number")
    email_address: EmailStr = Field(..., description="Email address")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (MM/DD/YYYY)")
    age_18_or_older: bool = Field(..., description="Are you 18 years of age or older?")
    
    # Work Authorization
    work_eligible_us: bool = Field(..., description="Are you legally eligible to work in the United States?")
    visa_sponsorship: bool = Field(..., description="Do you now or will you in the future require visa sponsorship?")
    
    # Position Details
    available_start_date: str = Field(..., description="When are you available to start?")
    employment_type: EmploymentType = Field(..., description="What type of employment are you seeking?")
    willing_relocate: bool = Field(..., description="Are you willing to relocate?")
    willing_travel: bool = Field(..., description="Are you willing to travel?")
    travel_percentage: Optional[str] = Field(None, description="If yes, what percentage of travel?")
    
    # Compensation
    desired_salary: str = Field(..., description="Desired salary/wage")
    
    # EEO Information (Voluntary)
    gender: Optional[Gender] = Field(None, description="Gender (voluntary)")
    race_ethnicity: Optional[RaceEthnicity] = Field(None, description="Race/Ethnicity (voluntary)")
    veteran_status: Optional[VeteranStatus] = Field(None, description="Veteran Status (voluntary)")
    disability_status: Optional[DisabilityStatus] = Field(None, description="Disability Status (voluntary)")
    
    # Employment History
    current_employee: bool = Field(..., description="Are you a current employee of this company?")
    ever_terminated: bool = Field(..., description="Have you ever been terminated or asked to resign from any position?")
    termination_explanation: Optional[str] = Field(None, description="If yes, please explain")
    
    # Job-Specific Requirements
    security_clearance: YesNoNA = Field(..., description="Are you eligible for security clearance?")
    
    # Certifications and Declarations
    cert_accuracy: bool = Field(..., description="I certify that all information provided is true and accurate")
    cert_dismissal: bool = Field(..., description="I understand that false statements may result in dismissal")
    cert_background_check: bool = Field(..., description="I authorize background/reference checks")
    cert_drug_testing: bool = Field(..., description="I authorize drug testing (if applicable)")
    cert_at_will: bool = Field(..., description="I understand this is at-will employment")
    cert_job_description: bool = Field(..., description="I have read and understand the job description")
    cert_privacy_notice: bool = Field(..., description="I acknowledge receipt of privacy notice")
    cert_data_processing: bool = Field(..., description="I consent to processing of personal data")
    
    # Signature
    electronic_signature: str = Field(..., description="Electronic signature")
    signature_date: str = Field(..., description="Date (MM/DD/YYYY)")

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

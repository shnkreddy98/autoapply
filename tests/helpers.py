from datetime import datetime, date

from autoapply.models import (
    Contact,
    Job,
    Resume,
    JobExperience,
    Education,
    Skills,
    Certification,
    Project,
    Achievement,
    UserOnboarding,
    EmploymentType,
    YesNoNA,
)


def make_contact(suffix: str = "") -> Contact:
    return Contact(
        name=f"Test User{suffix}",
        email=f"testuser{suffix}@example.com",
        location="New York, NY",
        phone="5551234567",
        country_code="+1",
        linkedin="https://linkedin.com/in/testuser",
        github="https://github.com/testuser",
    )


def make_resume(contact: Contact) -> Resume:
    return Resume(
        contact=contact,
        summary="Experienced software engineer",
        job_exp=[
            JobExperience(
                job_title="Software Engineer",
                company_name="Acme Corp",
                location="New York, NY",
                from_date=date(2020, 1, 1),
                to_date=date(2023, 6, 1),
                experience=["Built APIs", "Led team of 3"],
            )
        ],
        skills=[Skills(title="Languages", skills="Python, Go")],
        education=[
            Education(
                degree="BS",
                major="Computer Science",
                college="State University",
                from_date=date(2016, 9, 1),
                to_date=date(2020, 5, 1),
            )
        ],
        certifications=[
            Certification(
                title="AWS Solutions Architect",
                obtained_date=date(2021, 3, 15),
                expiry_date=date(2024, 3, 15),
            )
        ],
        projects=[
            Project(
                title="AutoApply",
                description="Job application automation",
                technologies=["Python", "Playwright"],
            )
        ],
        achievements=[
            Achievement(
                title="Hackathon Winner",
                description="Won company hackathon 2022",
            )
        ],
    )


def make_job(url: str, resume_path: str = "/tmp/resume.pdf") -> Job:
    return Job(
        url=url,
        role="Software Engineer",
        company_name="Test Corp",
        date_posted=datetime(2024, 1, 15),
        cloud="aws",
        resume_score=85.0,
        job_match_summary="Strong technical match",
        date_applied=datetime.now(),
        jd_filepath="/tmp/jd.txt",
        resume_filepath=resume_path,
        application_qnas=None,
    )


def make_onboarding(email: str) -> UserOnboarding:
    return UserOnboarding(
        full_name="Test User",
        street_address="123 Main St",
        city="New York",
        state="NY",
        zip_code="10001",
        phone_number="+1 5551234567",
        email_address=email,
        date_of_birth="01/15/1990",
        age_18_or_older=True,
        work_eligible_us=True,
        visa_sponsorship=False,
        available_start_date="2024-03-01",
        employment_type=EmploymentType.FULL_TIME,
        willing_relocate=True,
        willing_travel=False,
        travel_percentage=None,
        desired_salary="120000",
        gender=None,
        race_ethnicity=None,
        veteran_status=None,
        disability_status=None,
        current_employee=False,
        ever_terminated=False,
        termination_explanation=None,
        security_clearance=YesNoNA.NO,
        cert_accuracy=True,
        cert_dismissal=True,
        cert_background_check=True,
        cert_drug_testing=True,
        cert_at_will=True,
        cert_job_description=True,
        cert_privacy_notice=True,
        cert_data_processing=True,
        electronic_signature="Test User",
        signature_date="03/11/2026",
    )


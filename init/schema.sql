/*
User
- id
- name
- email (PK)
- phone
- linkedin
- github
- location

Resume
- id (PK)
- email
- path
- summary
- job experience
- education
- skills

Jobs
- url
- role
- company name
- date posted
- date applied
- jd path
- id (resume)
- score
- match summary
- application questions+answers (jsonb)
*/


CREATE TABLE IF NOT EXISTS users (
    name TEXT NOT NULL,
    email TEXT PRIMARY KEY,
    phone TEXT NOT NULL,
    linkedin TEXT NOT NULL,
    github TEXT NOT NULL,
    location TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,
    user_email TEXT,
    path TEXT,
    summary TEXT NOT NULL,
    job_experience JSONB NOT NULL,
    education JSONB NOT NULL, 
    skills JSONB NOT NULL,
    certifications JSONB NOT NULL,
    FOREIGN KEY (user_email) REFERENCES users(email)
);

CREATE TABLE IF NOT EXISTS jobs (
    url TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    company_name TEXT NOT NULL,
    date_posted TIMESTAMPTZ,
    date_applied TIMESTAMPTZ DEFAULT now(),
    jd_path TEXT NOT NULL,
    resume_id INT NOT NULL,
    resume_score REAL NOT NULL,
    job_match_summary TEXT NOT NULL,
    application_qnas JSONB NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resumes(id)
);

-- User application data table (stores detailed user information for job applications)
CREATE TABLE IF NOT EXISTS user_data (
    email TEXT PRIMARY KEY,
    -- Personal Information
    full_name TEXT NOT NULL,
    street_address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    date_of_birth TEXT,
    age_18_or_older BOOLEAN NOT NULL,

    -- Work Authorization
    work_eligible_us BOOLEAN NOT NULL,
    visa_sponsorship BOOLEAN NOT NULL,

    -- Position Details
    available_start_date TEXT NOT NULL,
    employment_type TEXT NOT NULL,
    willing_relocate BOOLEAN NOT NULL,
    willing_travel BOOLEAN NOT NULL,
    travel_percentage TEXT,

    -- Compensation
    desired_salary TEXT NOT NULL,

    -- EEO Information (Voluntary)
    gender TEXT,
    race_ethnicity TEXT,
    veteran_status TEXT,
    disability_status TEXT,

    -- Employment History
    current_employee BOOLEAN NOT NULL,
    ever_terminated BOOLEAN NOT NULL,
    termination_explanation TEXT,

    -- Job-Specific Requirements
    security_clearance TEXT NOT NULL,

    -- Certifications and Declarations
    cert_accuracy BOOLEAN NOT NULL,
    cert_dismissal BOOLEAN NOT NULL,
    cert_background_check BOOLEAN NOT NULL,
    cert_drug_testing BOOLEAN NOT NULL,
    cert_at_will BOOLEAN NOT NULL,
    cert_job_description BOOLEAN NOT NULL,
    cert_privacy_notice BOOLEAN NOT NULL,
    cert_data_processing BOOLEAN NOT NULL,

    -- Signature
    electronic_signature TEXT NOT NULL,
    signature_date TEXT NOT NULL,

    -- Foreign key to users table
    FOREIGN KEY (email) REFERENCES users(email)
);


-- Indexes for performance optimization

-- Index on resumes.user_email for faster joins with users table
CREATE INDEX IF NOT EXISTS idx_resumes_user_email ON resumes(user_email);

-- Index on jobs.resume_id for faster joins with resumes table
CREATE INDEX IF NOT EXISTS idx_jobs_resume_id ON jobs(resume_id);

-- Index on jobs.date_applied for filtering and sorting (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_jobs_date_applied ON jobs(date_applied DESC);

-- Index on jobs.date_posted for filtering by posting date
CREATE INDEX IF NOT EXISTS idx_jobs_date_posted ON jobs(date_posted DESC);

-- Composite index for searching jobs by company and role
CREATE INDEX IF NOT EXISTS idx_jobs_company_role ON jobs(company_name, role);

-- Index on jobs.resume_score for filtering by match score
CREATE INDEX IF NOT EXISTS idx_jobs_resume_score ON jobs(resume_score DESC);

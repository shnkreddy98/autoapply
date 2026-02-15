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
    country_code TEXT DEFAULT '+1',
    linkedin TEXT NOT NULL,
    github TEXT NOT NULL,
    location TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,
    user_email TEXT,
    path TEXT,
    summary TEXT,
    job_experience JSONB,
    education JSONB,
    skills JSONB,
    certifications JSONB,
    projects JSONB DEFAULT '[]'::jsonb,
    achievements JSONB DEFAULT '[]'::jsonb,
    FOREIGN KEY (user_email) REFERENCES users(email)
);

-- Drop dependent tables first
DROP INDEX IF EXISTS idx_timeline_session;
DROP TABLE IF EXISTS application_timeline_events CASCADE;
DROP INDEX IF EXISTS idx_session_status;
DROP INDEX IF EXISTS idx_session_created;
DROP TABLE IF EXISTS job_application_sessions CASCADE;
DROP INDEX IF EXISTS idx_conversations_session_id;
DROP INDEX IF EXISTS idx_conversations_user_email;
DROP INDEX IF EXISTS idx_conversations_job_url;
DROP INDEX IF EXISTS idx_conversations_endpoint;
DROP INDEX IF EXISTS idx_conversations_created_at;
DROP TABLE IF EXISTS conversations CASCADE;

-- Drop jobs table and its indexes
DROP INDEX IF EXISTS idx_jobs_resume_id;
DROP INDEX IF EXISTS idx_jobs_date_applied;
DROP INDEX IF EXISTS idx_jobs_date_posted;
DROP INDEX IF EXISTS idx_jobs_company_role;
DROP INDEX IF EXISTS idx_jobs_resume_score;
DROP TABLE IF EXISTS jobs CASCADE;

CREATE TABLE jobs (
    url TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    company_name TEXT NOT NULL,
    date_posted TIMESTAMPTZ,
    date_applied TIMESTAMPTZ DEFAULT now(),
    jd_path TEXT,  -- Nullable for direct applications without JD extraction
    resume_id INT NOT NULL,
    resume_path TEXT,
    resume_score REAL NOT NULL,
    job_match_summary TEXT NOT NULL,
    application_qnas JSONB,  -- Nullable for applications without Q&A
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

-- Agent conversations table to store agent interaction history
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    job_url TEXT,
    endpoint TEXT NOT NULL CHECK (endpoint IN ('applytojobs', 'tailortojobs')),
    agent_type TEXT NOT NULL,
    messages JSONB NOT NULL,
    usage_metrics JSONB NOT NULL,
    iterations INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    FOREIGN KEY (user_email) REFERENCES users(email),
    FOREIGN KEY (job_url) REFERENCES jobs(url) ON DELETE SET NULL
);

-- Indexes for conversations table
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_email ON conversations(user_email);
CREATE INDEX IF NOT EXISTS idx_conversations_job_url ON conversations(job_url);
CREATE INDEX IF NOT EXISTS idx_conversations_endpoint ON conversations(endpoint);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);

-- Job application sessions table for real-time monitoring
CREATE TABLE IF NOT EXISTS job_application_sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    job_url TEXT NOT NULL,
    resume_id INT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'paused', 'completed', 'failed')),
    current_step TEXT,
    current_thought TEXT,
    screenshot_dir TEXT,
    tab_index INT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (job_url) REFERENCES jobs(url) ON DELETE CASCADE,
    FOREIGN KEY (resume_id) REFERENCES resumes(id)
);

-- Indexes for job_application_sessions table
CREATE INDEX IF NOT EXISTS idx_session_status ON job_application_sessions(status);
CREATE INDEX IF NOT EXISTS idx_session_created ON job_application_sessions(created_at DESC);

-- Application timeline events table for detailed agent action tracking
CREATE TABLE IF NOT EXISTS application_timeline_events (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('thought', 'tool_call', 'screenshot', 'error', 'pause', 'resume')),
    timestamp TIMESTAMPTZ DEFAULT now(),
    content TEXT NOT NULL,
    metadata JSONB,
    screenshot_path TEXT,
    FOREIGN KEY (session_id) REFERENCES job_application_sessions(session_id) ON DELETE CASCADE
);

-- Index for application_timeline_events table
CREATE INDEX IF NOT EXISTS idx_timeline_session ON application_timeline_events(session_id, timestamp);

CREATE TABLE IF NOT EXISTS users (
    id           SERIAL PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    phone        TEXT NOT NULL,
    country_code TEXT DEFAULT '+1',
    location     TEXT NOT NULL,
    linkedin     TEXT NOT NULL,
    github       TEXT NOT NULL
);

-- 1:1 with users, stores autofill data used by the LLM agent during applications
CREATE TABLE IF NOT EXISTS autofill (
    user_id                 INT PRIMARY KEY REFERENCES users(id),
    full_name               TEXT NOT NULL,
    street_address          TEXT NOT NULL,
    city                    TEXT NOT NULL,
    state                   TEXT NOT NULL,
    zip_code                TEXT NOT NULL,
    date_of_birth           TEXT,
    age_18_or_older         BOOLEAN NOT NULL DEFAULT false,
    work_eligible_us        BOOLEAN NOT NULL,
    visa_sponsorship        BOOLEAN NOT NULL,
    available_start_date    TEXT NOT NULL,
    employment_type         TEXT NOT NULL,
    willing_relocate        BOOLEAN NOT NULL,
    willing_travel          BOOLEAN NOT NULL,
    travel_percentage       TEXT,
    desired_salary          TEXT NOT NULL,
    gender                  TEXT,
    race_ethnicity          TEXT,
    veteran_status          TEXT,
    disability_status       TEXT,
    current_employee        BOOLEAN NOT NULL,
    ever_terminated         BOOLEAN NOT NULL,
    termination_explanation TEXT,
    security_clearance      TEXT,
    certs                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    electronic_signature    TEXT NOT NULL,
    signature_date          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resumes (
    id         SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    path       TEXT,
    parsed     JSONB  -- {summary, experience, education, skills, certifications, projects, achievements}
);

-- Job postings deduplicated by URL, independent of any user
CREATE TABLE IF NOT EXISTS jobs (
    url              TEXT PRIMARY KEY,
    role             TEXT NOT NULL,
    company          TEXT NOT NULL,
    date_posted      TIMESTAMPTZ,
    yoe_required     INT,
    visa_sponsorship BOOLEAN,
    jd_path          TEXT
);

-- A user's application to a job using a specific resume
CREATE TABLE IF NOT EXISTS applications (
    id            SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES users(id),
    job_url       TEXT NOT NULL REFERENCES jobs(url),
    resume_id     INT NOT NULL REFERENCES resumes(id),
    resume_path   TEXT,
    date_applied  TIMESTAMPTZ DEFAULT now(),
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'applied', 'failed')),
    score         REAL,
    match_summary TEXT,
    qnas          JSONB DEFAULT '[]'::jsonb,  -- [{question, answer}]
    UNIQUE (user_id, job_url)
);

-- One agent run record per application attempt
CREATE TABLE IF NOT EXISTS agent_runs (
    id             SERIAL PRIMARY KEY,
    application_id INT REFERENCES applications(id),
    agent_type     TEXT NOT NULL,
    iterations     INT NOT NULL DEFAULT 0,
    model          TEXT NOT NULL,
    messages       JSONB NOT NULL,
    usage_metrics  JSONB NOT NULL,
    success        BOOLEAN NOT NULL,
    error_message  TEXT,
    created_at     TIMESTAMPTZ DEFAULT now()
);

-- Browser automation session state (can be paused and resumed)
CREATE TABLE IF NOT EXISTS browser_sessions (
    id              SERIAL PRIMARY KEY,
    session_id      TEXT UNIQUE NOT NULL,
    application_id  INT NOT NULL REFERENCES applications(id),
    status          TEXT NOT NULL DEFAULT 'running'
                    CHECK (status IN ('queued', 'running', 'paused', 'completed', 'failed')),
    current_step    TEXT,
    current_thought TEXT,
    tab_index       INT,
    screenshot_dir  TEXT,
    events          JSONB DEFAULT '[]'::jsonb,  -- [{type, timestamp, content, metadata, screenshot_path}]
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_resumes_user_id          ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_user_id     ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_job_url     ON applications(job_url);
CREATE INDEX IF NOT EXISTS idx_applications_status      ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_date        ON applications(date_applied DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_app           ON agent_runs(application_id);
CREATE INDEX IF NOT EXISTS idx_browser_sessions_app     ON browser_sessions(application_id);
CREATE INDEX IF NOT EXISTS idx_browser_sessions_status  ON browser_sessions(status);

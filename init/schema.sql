/*
jobs
- job url
- company name
- job role
- date posted
- job desc filepath
- cloud category
- resume filepath
- resume score
*/

CREATE TABLE IF NOT EXISTS jobs (
    url TEXT PRIMARY KEY,
    role TEXT,
    company_name TEXT,
    date_posted TIMESTAMP,
    date_applied TIMESTAMP,
    jd_filepath TEXT,
    cloud CHAR(3),
    resume_filepath TEXT,
    resume_score REAL,
    detailed_explanation TEXT
);

CREATE TABLE IF NOT EXISTS resume_no (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS contact (
    contact_id SERIAL PRIMARY KEY,
    resume_id INT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    location TEXT NOT NULL,
    phone TEXT NOT NULL,
    linkedin TEXT NOT NULL,
    github TEXT NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resume_no(id)
);

CREATE TABLE IF NOT EXISTS summary (
    summary_id SERIAL PRIMARY KEY,
    summary TEXT,
    resume_id INT NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resume_no(id)
);

CREATE TABLE IF NOT EXISTS job_experience (
    job_experience_id SERIAL PRIMARY KEY,
    resume_id INT NOT NULL,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    location TEXT NOT NULL,
    from_date TIMESTAMP NOT NULL,
    to_date TEXT NOT NULL,
    experience JSONB NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resume_no(id)
);

CREATE TABLE IF NOT EXISTS education (
    education_id SERIAL PRIMARY KEY,
    resume_id INT NOT NULL,
    degree TEXT NOT NULL,
    major TEXT NOT NULL,
    college TEXT NOT NULL,
    from_date TIMESTAMP NOT NULL,
    to_date TIMESTAMP NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resume_no(id)
);

CREATE TABLE IF NOT EXISTS certifications (
    certifications_id SERIAL PRIMARY KEY,
    resume_id INT NOT NULL,
    title TEXT NOT NULL,
    obtained_date TIMESTAMP NOT NULL,
    expiry_date TEXT,
    FOREIGN KEY (resume_id) REFERENCES resume_no(id)
);

CREATE TABLE IF NOT EXISTS skills (
    skills_id SERIAL PRIMARY KEY,
    resume_id INT NOT NULL,
    title TEXT NOT NULL,
    skills JSONB NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resume_no(id)
);

CREATE INDEX IF NOT EXISTS date_applied_idx ON jobs(date_applied);
CREATE INDEX IF NOT EXISTS cloud_idx ON jobs(cloud);
CREATE INDEX IF NOT EXISTS resume_score_idx ON jobs(resume_score);
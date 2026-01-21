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
    detailed_explaination TEXT
);

CREATE INDEX IF NOT EXISTS date_applied_idx ON jobs(date_applied);
CREATE INDEX IF NOT EXISTS cloud_idx ON jobs(cloud);
CREATE INDEX IF NOT EXISTS resume_score_idx ON jobs(resume_score);
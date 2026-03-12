"""Integration tests for db.py against the running Docker DB (localhost:25432)."""
import uuid
from datetime import datetime, date

import pytest

from tests.helpers import *

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_upsert_user(repo):
    contact = make_contact("_u1")
    user_id = repo.upsert_user(contact)
    assert isinstance(user_id, int)
    assert user_id > 0

    # Re-upsert same email returns same id
    user_id2 = repo.upsert_user(contact)
    assert user_id == user_id2


def test_insert_resume(repo):
    contact = make_contact("_r1")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path="/tmp/test_resume.pdf")
    assert isinstance(resume_id, int)
    assert resume_id > 0


def test_upsert_resume(repo):
    contact = make_contact("_r2")
    resume = make_resume(contact)
    # Insert first
    repo.insert_resume(resume, path="/tmp/upsert_test.pdf")

    # Now upsert (update by path)
    resume_id = repo.upsert_resume(resume, path="/tmp/upsert_test.pdf")
    assert isinstance(resume_id, int)
    assert resume_id > 0


def test_insert_job(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    job = make_job(job_url)
    returned_url = repo.insert_job(job, resume_id)

    assert returned_url == job_url

    # Verify both rows exist
    repo.cursor.execute("SELECT url FROM jobs WHERE url = %s", (job_url,))
    assert repo.cursor.fetchone() is not None

    repo.cursor.execute("SELECT id FROM applications WHERE job_url = %s", (job_url,))
    assert repo.cursor.fetchone() is not None


def test_list_jobs(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    job = make_job(job_url)
    repo.insert_job(job, resume_id)

    jobs = repo.list_jobs()
    urls = [j["url"] for j in jobs]
    assert job_url in urls

    # Filter by today's date (use UTC to match DB's AT TIME ZONE 'UTC' cast)
    from datetime import timezone
    today_utc = datetime.now(timezone.utc).date()
    jobs_today = repo.list_jobs(date=today_utc)
    urls_today = [j["url"] for j in jobs_today]
    assert job_url in urls_today


def test_get_jd_resume(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    job = make_job(job_url)
    repo.insert_job(job, resume_id)

    result = repo.get_jd_resume(job_url)
    assert result is not None
    assert result["jd_path"] == "/tmp/jd.txt"
    assert result["resume_id"] == resume_id


def test_update_qnas(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    repo.insert_job(make_job(job_url), resume_id)

    qnas = [{"question": "Why do you want this role?", "answer": "I love automation"}]
    returned_url = repo.update_qnas(qnas, job_url)
    assert returned_url == job_url

    repo.cursor.execute("SELECT qnas FROM applications WHERE job_url = %s", (job_url,))
    row = repo.cursor.fetchone()
    assert row["qnas"] == qnas


def test_fill_autofill(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    repo.upsert_user(contact)

    onboarding = make_onboarding(contact.email)
    email = repo.fill_user_information(onboarding)
    assert email == contact.email

    # Verify certs JSONB structure
    repo.cursor.execute(
        "SELECT certs FROM autofill af JOIN users u ON af.user_id = u.id WHERE u.email = %s",
        (contact.email,),
    )
    row = repo.cursor.fetchone()
    assert row is not None
    certs = row["certs"]
    assert "cert_accuracy" in certs
    assert certs["cert_accuracy"] is True
    assert "cert_data_processing" in certs

    # Re-upsert changes desired_salary
    onboarding2 = make_onboarding(contact.email)
    onboarding2.desired_salary = "150000"  # type: ignore[assignment]
    repo.fill_user_information(onboarding2)
    repo.cursor.execute(
        "SELECT desired_salary FROM autofill af JOIN users u ON af.user_id = u.id WHERE u.email = %s",
        (contact.email,),
    )
    row2 = repo.cursor.fetchone()
    assert row2["desired_salary"] == "150000"


def test_get_candidate_data(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    onboarding = make_onboarding(contact.email)
    repo.fill_user_information(onboarding)

    data = repo.get_candidate_data(resume_id)

    assert data["email"] == contact.email
    assert data["first_name"] == "Test"
    assert "resume_text" in data
    assert "Summary" in data["resume_text"]
    assert "work_authorization" in data
    assert data["desired_salary"] == "120000"
    assert "user_data" in data
    assert "cert_accuracy" in data["user_data"]


def test_insert_agent_run(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    repo.insert_job(make_job(job_url), resume_id)

    run_id = repo.insert_conversation(
        session_id=f"sess-{uid}",
        user_email=contact.email,
        job_url=job_url,
        endpoint="anthropic/claude-haiku-4.5",
        agent_type="application",
        messages=[{"role": "user", "content": "Apply"}],
        usage_metrics={"input_tokens": 100, "output_tokens": 50},
        iterations=3,
        success=True,
        error_message=None,
    )
    assert isinstance(run_id, int)
    assert run_id > 0

    repo.cursor.execute("SELECT * FROM agent_runs WHERE id = %s", (run_id,))
    row = repo.cursor.fetchone()
    assert row["agent_type"] == "application"
    assert row["iterations"] == 3
    assert row["usage_metrics"]["endpoint"] == "anthropic/claude-haiku-4.5"


def test_insert_agent_run_no_job(repo):
    """Agent runs with no job_url should still insert (application_id nullable)."""
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    repo.upsert_user(contact)

    run_id = repo.insert_conversation(
        session_id=f"sess-nojob-{uid}",
        user_email=contact.email,
        job_url=None,
        endpoint="anthropic/claude-haiku-4.5",
        agent_type="resume_parser",
        messages=[],
        usage_metrics={},
        iterations=1,
        success=True,
    )
    assert isinstance(run_id, int)

    repo.cursor.execute("SELECT application_id FROM agent_runs WHERE id = %s", (run_id,))
    row = repo.cursor.fetchone()
    assert row["application_id"] is None


def test_create_browser_session(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    repo.insert_job(make_job(job_url), resume_id)

    session_id = f"browser-{uid}"
    returned = repo.create_application_session(
        session_id=session_id,
        job_url=job_url,
        resume_id=resume_id,
        screenshot_dir="/tmp/screenshots",
    )
    assert returned == session_id

    # Lookup by session_id
    sess = repo.get_application_session(session_id)
    assert sess is not None
    assert sess["session_id"] == session_id
    assert sess["status"] == "running"
    assert sess["screenshot_dir"] == "/tmp/screenshots"


def test_update_session_status(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    repo.insert_job(make_job(job_url), resume_id)

    session_id = f"browser-{uid}"
    repo.create_application_session(session_id, job_url, resume_id)

    repo.update_session_status(session_id, "completed")
    sess = repo.get_application_session(session_id)
    assert sess["status"] == "completed"
    assert sess["completed_at"] is not None

    # Update with error
    repo.update_session_status(session_id, "failed", error="Timeout")
    sess = repo.get_application_session(session_id)
    assert sess["status"] == "failed"
    assert sess["error_message"] == "Timeout"


def test_insert_timeline_event(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    repo.insert_job(make_job(job_url), resume_id)

    session_id = f"browser-{uid}"
    repo.create_application_session(session_id, job_url, resume_id)

    # Append two events
    repo.insert_timeline_event(session_id, "page_load", "Loaded job application page")
    repo.insert_timeline_event(
        session_id,
        "form_fill",
        "Filled name field",
        metadata={"field": "name"},
        screenshot_path="/tmp/s1.png",
    )

    sess = repo.get_application_session(session_id)
    events = sess["events"]
    assert len(events) == 2
    assert events[0]["type"] == "page_load"
    assert events[1]["type"] == "form_fill"
    assert events[1]["metadata"]["field"] == "name"
    assert events[1]["screenshot_path"] == "/tmp/s1.png"


def test_get_user_email_by_resume(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    email = repo.get_user_email_by_resume(resume_id)
    assert email == contact.email


def test_get_resume(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume, path=f"/tmp/resume_{uid}.pdf")

    job_url = f"https://example.com/job/{uid}"
    resume_path = f"/tmp/tailored_{uid}.pdf"
    job = make_job(job_url, resume_path=resume_path)
    repo.insert_job(job, resume_id)

    result = repo.get_resume(job_url)
    assert result == resume_path


def test_list_contact(repo):
    uid = str(uuid.uuid4())[:8]
    contact = make_contact(f"_{uid}")
    resume = make_resume(contact)
    resume_id = repo.insert_resume(resume)

    contacts = repo.list_contact(resume_id)
    assert len(contacts) == 1
    assert contacts[0]["email"] == contact.email
    assert contacts[0]["name"] == contact.name

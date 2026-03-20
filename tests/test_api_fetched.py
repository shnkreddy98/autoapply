"""Functional tests for fetched-url endpoints (TestClient with mocked DB/browser)."""

from datetime import date
from unittest.mock import AsyncMock, patch


def test_fetched_urls_no_params(client):
    client.tx.list_fetched_urls.return_value = []

    response = client.get("/fetched-urls")

    assert response.status_code == 200
    client.tx.list_fetched_urls.assert_called_once_with(date.today(), user_email=None)


def test_fetched_urls_with_date_and_email(client):
    client.tx.list_fetched_urls.return_value = []

    response = client.get("/fetched-urls?date=2026-03-15&email=user@example.com")

    assert response.status_code == 200
    client.tx.list_fetched_urls.assert_called_once_with(
        date(2026, 3, 15), user_email="user@example.com"
    )


def test_fetched_urls_response_shape(client):
    client.tx.list_fetched_urls.return_value = [
        {"url": "https://example.com/job1", "action": "tailor"},
        {"url": "https://example.com/job2", "action": "apply"},
    ]

    response = client.get("/fetched-urls?email=user@example.com")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert all("url" in item and "action" in item for item in data)


def test_tailortojobs_inserts_with_tailor_action(client):
    client.tx.get_user_email_by_resume.return_value = "user@example.com"
    urls = ["https://job1.com", "https://job2.com"]
    resume_id = 42

    with patch("autoapply.api.batch_process", new_callable=AsyncMock, return_value=[]):
        response = client.post(
            "/tailortojobs", json={"urls": urls, "resume_id": resume_id}
        )

    assert response.status_code == 200
    client.tx.insert_fetched_urls.assert_called_once_with(
        urls, "user@example.com", resume_id, "tailor"
    )


def test_tailortojobs_skips_insert_when_no_email(client):
    client.tx.get_user_email_by_resume.return_value = None
    urls = ["https://job1.com"]

    with patch("autoapply.api.batch_process", new_callable=AsyncMock, return_value=[]):
        response = client.post(
            "/tailortojobs", json={"urls": urls, "resume_id": 1}
        )

    assert response.status_code == 200
    client.tx.insert_fetched_urls.assert_not_called()


def test_applytojobs_inserts_with_apply_action(client):
    client.tx.get_user_email_by_resume.return_value = "user@example.com"
    urls = ["https://job1.com"]
    resume_id = 7

    with patch("asyncio.create_task", side_effect=lambda coro: coro.close()):
        response = client.post(
            "/applytojobs", json={"urls": urls, "resume_id": resume_id}
        )

    assert response.status_code == 200
    client.tx.insert_fetched_urls.assert_called_once_with(
        urls, "user@example.com", resume_id, "apply"
    )


def test_applytojobs_skips_insert_when_no_email(client):
    client.tx.get_user_email_by_resume.return_value = None
    urls = ["https://job1.com"]

    with patch("asyncio.create_task"):
        response = client.post(
            "/applytojobs", json={"urls": urls, "resume_id": 1}
        )

    assert response.status_code == 200
    client.tx.insert_fetched_urls.assert_not_called()

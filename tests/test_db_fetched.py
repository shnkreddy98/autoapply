"""Unit tests for insert_fetched_urls and list_fetched_urls (mocked cursor, no DB)."""

from datetime import date
from unittest.mock import call


def test_insert_single_url(repo, mock_cursor):
    repo.insert_fetched_urls(["https://example.com/job1"], "user@example.com", 5, "tailor")

    mock_cursor.executemany.assert_called_once()
    params = mock_cursor.executemany.call_args.args[1]
    assert params == [("https://example.com/job1", "user@example.com", 5, "tailor")]


def test_insert_multiple_urls(repo, mock_cursor):
    urls = ["https://job1.com", "https://job2.com", "https://job3.com"]
    repo.insert_fetched_urls(urls, "user@example.com", 10, "apply")

    mock_cursor.executemany.assert_called_once()
    params = mock_cursor.executemany.call_args.args[1]
    assert len(params) == 3
    assert all(t[1] == "user@example.com" and t[3] == "apply" for t in params)
    assert [t[0] for t in params] == urls


def test_insert_empty_list(repo, mock_cursor):
    repo.insert_fetched_urls([], "user@example.com", 1, "tailor")

    mock_cursor.executemany.assert_called_once()
    params = mock_cursor.executemany.call_args.args[1]
    assert params == []


def test_insert_null_resume_id(repo, mock_cursor):
    repo.insert_fetched_urls(["https://job.com"], "user@example.com", None, "tailor")

    params = mock_cursor.executemany.call_args.args[1]
    assert params[0][2] is None


def test_list_no_email_returns_empty(repo, mock_cursor):
    result = repo.list_fetched_urls(date.today(), user_email=None)

    assert result == []
    mock_cursor.execute.assert_not_called()


def test_list_executes_correct_sql(repo, mock_cursor):
    target_date = date(2026, 3, 15)
    repo.list_fetched_urls(target_date, user_email="user@example.com")

    mock_cursor.execute.assert_called_once()
    _, kwargs = mock_cursor.execute.call_args
    # params are passed as second positional arg
    call_args = mock_cursor.execute.call_args[0]
    params = call_args[1]
    assert params["date"] == target_date
    assert params["user_email"] == "user@example.com"


def test_list_returns_fetchall_result(repo, mock_cursor):
    expected = [{"url": "https://job.com", "action": "tailor"}]
    mock_cursor.fetchall.return_value = expected

    result = repo.list_fetched_urls(date.today(), user_email="user@example.com")

    assert result == expected

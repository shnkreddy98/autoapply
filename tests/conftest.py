from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv
from starlette.testclient import TestClient

# Load dev env vars before any autoapply imports so autoapply.env resolves correctly
load_dotenv(Path(__file__).parent.parent / "dev.env")


@pytest.fixture
def mock_cursor():
    return MagicMock()


@pytest.fixture
def mock_conn():
    return MagicMock()


@pytest.fixture
def repo(mock_cursor, mock_conn):
    from autoapply.services.db import AutoApply

    return AutoApply(mock_cursor, mock_conn)


@pytest.fixture
def client():
    mock_tx = MagicMock()
    mock_Txc = MagicMock()
    mock_Txc.return_value.__enter__ = MagicMock(return_value=mock_tx)
    mock_Txc.return_value.__exit__ = MagicMock(return_value=False)

    with (
        patch("autoapply.api.browser_manager.initialize", new_callable=AsyncMock),
        patch("autoapply.api.browser_manager.shutdown", new_callable=AsyncMock),
        patch("autoapply.api.Txc", mock_Txc),
    ):
        from autoapply.api import app

        with TestClient(app) as c:
            c.tx = mock_tx
            yield c

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import create_app, lifespan


@pytest.fixture
async def app():
    """FastAPI app with lifespan startup/shutdown managed per test."""
    application = create_app()
    async with lifespan(application):
        yield application


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    """HTTP client that talks to the app in-process (no real server needed)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest.fixture
async def client_with_db_down(app) -> AsyncIterator[AsyncClient]:
    """Client with a database session that always fails on query."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = Exception("database unreachable")

    async def failing_get_db() -> AsyncIterator[AsyncSession]:
        yield mock_session

    app.dependency_overrides[get_db] = failing_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()

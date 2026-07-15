import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal


async def database_is_reachable() -> bool:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.integration
async def test_health_returns_ok_when_database_is_available(client: AsyncClient):
    if not await database_is_reachable():
        pytest.skip("PostgreSQL is not running; start it to run this integration test")

    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"


async def test_health_returns_error_when_database_is_down(
    client_with_db_down: AsyncClient,
):
    response = await client_with_db_down.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "disconnected"
    assert "detail" in body

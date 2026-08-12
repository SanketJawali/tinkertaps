import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps.auth import AuthContext
from app.core.config import settings
from app.db.session import get_db
from app.main import create_app
from app.models.jobs import Job, JobStatus, Operation
from app.models.users import User
from app.api.deps import get_auth_context


@pytest.fixture
def anonymous_user() -> User:
    return User(
        id=uuid.uuid4(),
        clerk_user_id=None,
        anonymous_id=uuid.uuid4(),
        credits=3,
    )


@pytest.fixture
def clerk_user() -> User:
    return User(
        id=uuid.uuid4(),
        clerk_user_id="user_clerk_123",
        anonymous_id=None,
        credits=10,
    )


@pytest.fixture
async def job_client(anonymous_user: User):
    application = create_app()
    mock_db = AsyncMock()

    async def override_db():
        yield mock_db

    async def override_auth():
        return AuthContext(
            user=anonymous_user,
            is_anonymous=True,
            set_anon_cookie=True,
            anon_cookie_value=str(anonymous_user.anonymous_id),
        )

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_auth_context] = override_auth

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        yield client, anonymous_user

    application.dependency_overrides.clear()


@pytest.fixture
async def clerk_job_client(clerk_user: User):
    application = create_app()
    mock_db = AsyncMock()

    async def override_db():
        yield mock_db

    async def override_auth():
        return AuthContext(user=clerk_user, is_anonymous=False)

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_auth_context] = override_auth

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        yield client, clerk_user

    application.dependency_overrides.clear()


async def test_presign_creates_draft_job_and_sets_anon_cookie(job_client):
    client, user = job_client
    job_id = uuid.uuid4()
    input_key = f"uploads/{user.id}/{job_id}/photo.png"
    draft = Job(
        id=job_id,
        user_id=user.id,
        operation=Operation.COMPRESS,
        status=JobStatus.DRAFT,
        input_key=input_key,
    )

    with patch(
        "app.api.routes.job.job_service.create_draft_job_with_presign",
        new=AsyncMock(
            return_value=(draft, "https://s3.example/presigned", 3600),
        ),
    ) as create_mock:
        response = await client.post(
            "/jobs/presign",
            json={
                "operation": "compress",
                "filename": "photo.png",
                "content_type": "image/png",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == str(job_id)
    assert body["upload_url"] == "https://s3.example/presigned"
    assert body["input_key"] == input_key
    assert body["expires_in"] == 3600
    assert settings.anon_cookie_name in response.cookies
    create_mock.assert_awaited_once()


async def test_presign_rejects_insufficient_credits(job_client):
    client, _user = job_client

    from fastapi import HTTPException

    with patch(
        "app.api.routes.job.job_service.create_draft_job_with_presign",
        new=AsyncMock(
            side_effect=HTTPException(
                status_code=402,
                detail="Insufficient credits to start a new job",
            ),
        ),
    ):
        response = await client.post(
            "/jobs/presign",
            json={
                "operation": "convert",
                "filename": "doc.png",
                "content_type": "image/png",
            },
        )

    assert response.status_code == 402
    assert "Insufficient credits" in response.json()["detail"]


async def test_start_job_verifies_upload_and_returns_credits(clerk_job_client):
    client, user = clerk_job_client
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        user_id=user.id,
        operation=Operation.CONVERT,
        status=JobStatus.PENDING,
        input_key=f"uploads/{user.id}/{job_id}/a.png",
    )
    user.credits = 9

    with patch(
        "app.api.routes.job.job_service.start_draft_job",
        new=AsyncMock(return_value=job),
    ) as start_mock:
        response = await client.post(f"/jobs/{job_id}/start")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(job_id)
    assert body["status"] == "pending"
    assert body["credits_remaining"] == 9
    start_mock.assert_awaited_once()


async def test_start_job_not_found(clerk_job_client):
    client, _user = clerk_job_client
    missing_id = uuid.uuid4()

    from fastapi import HTTPException

    with patch(
        "app.api.routes.job.job_service.start_draft_job",
        new=AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Job not found"),
        ),
    ):
        response = await client.post(f"/jobs/{missing_id}/start")

    assert response.status_code == 404


async def test_ensure_credits_accounts_for_existing_drafts():
    from app.services.jobs import ensure_credits_for_new_draft

    user = User(
        id=uuid.uuid4(),
        clerk_user_id="user_abc",
        anonymous_id=None,
        credits=1,
    )
    db = AsyncMock()

    with patch(
        "app.services.jobs.count_draft_jobs",
        new=AsyncMock(return_value=1),
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await ensure_credits_for_new_draft(db, user)

    assert exc_info.value.status_code == 402


async def test_build_input_key_sanitizes_filename(clerk_user: User):
    from app.services.jobs import build_input_key

    job_id = uuid.uuid4()
    key = build_input_key(
        user_id=clerk_user.id,
        job_id=job_id,
        filename="../weird name!!!.PNG",
    )
    assert key == f"uploads/{clerk_user.id}/{job_id}/weird_name_.PNG"

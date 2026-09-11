import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.core.errors import ErrorCode
from app.models.jobs import Job, JobStatus, Operation
from app.models.users import User
from app.services import jobs as job_service
from app.services import s3  # , job_queue


def _client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "test"}},
        "HeadObject",
    )


def _mock_db_with_job(job: Job | None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = job
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.fixture
def user() -> User:
    return User(
        id=uuid.uuid4(),
        clerk_user_id="user_abc",
        anonymous_id=None,
        credits=5,
    )


@pytest.fixture
def draft_job(user: User) -> Job:
    job_id = uuid.uuid4()
    return Job(
        id=job_id,
        user_id=user.id,
        operation=Operation.COMPRESS,
        status=JobStatus.DRAFT,
        input_key=f"uploads/{user.id}/{job_id}/photo.png",
    )


async def test_start_draft_job_not_found(user: User):
    db = _mock_db_with_job(None)

    with pytest.raises(HTTPException) as exc_info:
        await job_service.start_draft_job(
            db=db,
            user=user,
            job_id=uuid.uuid4(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == ErrorCode.JOB_NOT_FOUND


async def test_start_draft_job_forbidden(user: User, draft_job: Job):
    db = _mock_db_with_job(draft_job)
    other_user = User(
        id=uuid.uuid4(),
        clerk_user_id="other",
        anonymous_id=None,
        credits=5,
    )

    with pytest.raises(HTTPException) as exc_info:
        await job_service.start_draft_job(
            db=db,
            user=other_user,
            job_id=draft_job.id,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == ErrorCode.JOB_FORBIDDEN


async def test_start_draft_job_not_draft(user: User, draft_job: Job):
    draft_job.status = JobStatus.PENDING
    db = _mock_db_with_job(draft_job)

    with pytest.raises(HTTPException) as exc_info:
        await job_service.start_draft_job(
            db=db,
            user=user,
            job_id=draft_job.id,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == ErrorCode.JOB_NOT_DRAFT


async def test_start_draft_job_upload_missing(user: User, draft_job: Job):
    db = _mock_db_with_job(draft_job)

    with patch(
        "app.services.jobs.s3.verify_upload_exists",
        new=AsyncMock(
            side_effect=HTTPException(
                status_code=400,
                detail={
                    "code": ErrorCode.UPLOAD_NOT_FOUND,
                    "message": "Uploaded file not found in storage. Complete the upload first.",
                },
            ),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await job_service.start_draft_job(
                db=db,
                user=user,
                job_id=draft_job.id,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == ErrorCode.UPLOAD_NOT_FOUND
    db.commit.assert_not_awaited()


async def test_start_draft_job_insufficient_credits(user: User, draft_job: Job):
    user.credits = 0
    db = _mock_db_with_job(draft_job)

    with patch(
        "app.services.jobs.s3.verify_upload_exists",
        new=AsyncMock(),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await job_service.start_draft_job(
                db=db,
                user=user,
                job_id=draft_job.id,
            )

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["code"] == ErrorCode.INSUFFICIENT_CREDITS


async def test_start_draft_job_queue_failure_rolls_back(user: User, draft_job: Job):
    db = _mock_db_with_job(draft_job)

    with (
        patch("app.services.jobs.s3.verify_upload_exists", new=AsyncMock()),
        patch(
            "app.services.jobs.job_queue.enqueue_job",
            new=AsyncMock(
                side_effect=HTTPException(
                    status_code=503,
                    detail={
                        "code": ErrorCode.QUEUE_UNAVAILABLE,
                        "message": "Failed to enqueue job for processing",
                    },
                ),
            ),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await job_service.start_draft_job(
                db=db,
                user=user,
                job_id=draft_job.id,
            )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == ErrorCode.QUEUE_UNAVAILABLE
    assert user.credits == 5
    assert draft_job.status == JobStatus.DRAFT
    assert db.commit.await_count == 2


async def test_start_draft_job_success(user: User, draft_job: Job):
    db = _mock_db_with_job(draft_job)

    with (
        patch("app.services.jobs.s3.verify_upload_exists", new=AsyncMock()),
        patch("app.services.jobs.job_queue.enqueue_job", new=AsyncMock()),
    ):
        job = await job_service.start_draft_job(
            db=db,
            user=user,
            job_id=draft_job.id,
        )

    assert job.status == JobStatus.PENDING
    assert user.credits == 4


async def test_create_draft_job_presign_failure_rolls_back(user: User):
    db = AsyncMock()

    with (
        patch(
            "app.services.jobs.count_draft_jobs",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.services.jobs.s3.create_presigned_upload_url_async",
            new=AsyncMock(
                side_effect=HTTPException(
                    status_code=503,
                    detail={
                        "code": ErrorCode.STORAGE_UNAVAILABLE,
                        "message": "Failed to generate upload URL",
                    },
                ),
            ),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await job_service.create_draft_job_with_presign(
                db=db,
                user=user,
                operation=Operation.COMPRESS,
                filename="photo.png",
                content_type="image/png",
            )

    assert exc_info.value.detail["code"] == ErrorCode.STORAGE_UNAVAILABLE
    db.delete.assert_awaited_once()
    assert db.commit.await_count == 2


def test_s3_object_exists_returns_false_for_missing_key():
    client = MagicMock()
    client.head_object.side_effect = _client_error("404")

    with patch("app.services.s3.get_s3_client", return_value=client):
        assert s3.object_exists("uploads/missing.png") is False


def test_s3_object_exists_raises_on_storage_error():
    client = MagicMock()
    client.head_object.side_effect = _client_error("AccessDenied")

    with patch("app.services.s3.get_s3_client", return_value=client):
        with pytest.raises(HTTPException) as exc_info:
            s3.object_exists("uploads/denied.png")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == ErrorCode.STORAGE_UNAVAILABLE


def test_s3_presign_failure_raises_storage_unavailable():
    client = MagicMock()
    client.generate_presigned_url.side_effect = _client_error("AccessDenied")

    with patch("app.services.s3.get_s3_client", return_value=client):
        with pytest.raises(HTTPException) as exc_info:
            s3.create_presigned_upload_url(
                key="uploads/test.png",
                content_type="image/png",
            )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == ErrorCode.STORAGE_UNAVAILABLE


# ================ Removed because of switch from Redis to SQS ================
# async def test_job_enqueue_failure_raises_queue_unavailable():
#     mock_client = AsyncMock()
#     mock_client.lpush.side_effect = jobConnectionError("connection refused")
#
#     with patch("app.services.job_queue.get_redis_client", return_value=mock_client):
#         with pytest.raises(HTTPException) as exc_info:
#             await job_queue.enqueue_job("job-123")
#
#     assert exc_info.value.status_code == 503
#     assert exc_info.value.detail["code"] == ErrorCode.QUEUE_UNAVAILABLE
#

def test_sanitize_filename_rejects_empty():
    with pytest.raises(HTTPException) as exc_info:
        job_service.sanitize_filename("   ")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == ErrorCode.INVALID_FILENAME

from app.services.job_queue import enqueue_job
from app.core.logging import get_logger
from app.core.errors import ErrorCode, raise_api_error
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, Response, status
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, apply_anon_cookie, get_auth_context
from app.db.session import get_db
from app.schemas.jobs import (
    JobStatusPollResponse,
    PresignRequest,
    PresignResponse,
    StartJobResponse,
)
from app.services import jobs as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

logger = get_logger(__name__)


@router.post(
    "/presign",
    response_model=PresignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_presigned_upload(
    body: PresignRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> PresignResponse:
    """
    Create a draft job and return an S3 presigned upload URL.

    Authenticated Clerk users are preferred. Without a Bearer token the
    request is treated as anonymous and tracked via an HTTP-only cookie.
    """
    job, upload_url, expires_in = await job_service.create_draft_job_with_presign(
        db=db,
        user=auth.user,
        operation=body.operation,
        filename=body.filename,
        content_type=body.content_type,
    )
    apply_anon_cookie(response, auth)
    return PresignResponse(
        job_id=job.id,
        upload_url=upload_url,
        input_key=job.input_key,
        expires_in=expires_in,
    )


@router.get(
    "/{job_id}/job-status-poll",
    response_model=JobStatusPollResponse,
    status_code=status.HTTP_200_OK,
)
async def job_status_poll(
    job_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> JobStatusPollResponse:
    """
    Return the current job status for polling clients.

    When the job is completed, also return a short-lived S3 download URL.
    When failed, include the stored error_message.
    """
    job, download_url, download_expires_in = await job_service.build_job_status_poll(
        db=db,
        user=auth.user,
        job_id=job_id,
    )
    apply_anon_cookie(response, auth)
    return JobStatusPollResponse(
        id=job.id,
        status=job.status,
        operation=job.operation,
        error_message=job.error_message,
        download_url=download_url,
        download_expires_in=download_expires_in,
    )


@router.post(
    "/{job_id}/start",
    response_model=StartJobResponse,
    status_code=status.HTTP_200_OK,
)
async def start_job(
    job_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> StartJobResponse:
    """
    Verify the S3 upload for a draft job, deduct one credit, mark the job
    pending, and enqueue it for background processing.
    """
    logger.debug(
        "Starting job",
        extra={
            "job_id": str(job_id),
            "user_id": str(auth.user.id),
        },
    )

    try:
        job = await job_service.start_draft_job(
            db=db,
            user=auth.user,
            job_id=job_id,
        )

    except Exception as exc:
        logger.exception(
            "Failed to prepare job for processing",
            extra={
                "job_id": str(job_id),
                "user_id": str(auth.user.id),
            },
        )
        raise

    try:
        logger.debug(
            "Enqueuing job for background processing",
            extra={"job_id": str(job_id)},
        )

        message_id = await run_in_threadpool(
            enqueue_job,
            str(job.id),
        )

        logger.info(
            "Job successfully queued",
            extra={
                "job_id": str(job.id),
                "message_id": message_id,
            },
        )

    except Exception as exc:
        logger.exception(
            "Failed to enqueue job",
            extra={"job_id": str(job.id)},
        )

        raise_api_error(
            code=ErrorCode.QUEUE_UNAVAILABLE,
            message="Job could not be queued for processing",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            logger=logger,
            log_message="SQS enqueue failed",
            exc=exc,
            job_id=str(job.id),
        )

    apply_anon_cookie(response, auth)

    return StartJobResponse(
        id=job.id,
        status=job.status,
        operation=job.operation,
        input_key=job.input_key,
        credits_remaining=auth.user.credits,
    )

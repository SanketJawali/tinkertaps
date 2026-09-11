from __future__ import annotations

import re
import uuid
from pathlib import PurePosixPath

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode, raise_api_error
from app.core.logging import get_logger
from app.models.jobs import Job, JobStatus, Operation
from app.models.users import User
from app.services import s3, job_queue

logger = get_logger(__name__)

_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    name = PurePosixPath(filename).name.strip()
    if not name:
        raise_api_error(
            code=ErrorCode.INVALID_FILENAME,
            message="filename is required",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    cleaned = _UNSAFE_FILENAME.sub("_", name)
    return cleaned[:200]


def build_input_key(*, user_id: uuid.UUID, job_id: uuid.UUID, filename: str) -> str:
    safe_name = sanitize_filename(filename)
    return f"uploads/{user_id}/{job_id}/{safe_name}"


async def count_draft_jobs(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Job)
        .where(Job.user_id == user_id, Job.status == JobStatus.DRAFT)
    )
    return int(result.scalar_one())


async def ensure_credits_for_new_draft(db: AsyncSession, user: User) -> None:
    draft_count = await count_draft_jobs(db, user.id)
    if user.credits < draft_count + 1:
        raise_api_error(
            code=ErrorCode.INSUFFICIENT_CREDITS,
            message="Insufficient credits to start a new job",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
        )


async def create_draft_job_with_presign(
    *,
    db: AsyncSession,
    user: User,
    operation: Operation,
    filename: str,
    content_type: str,
) -> tuple[Job, str, int]:
    await ensure_credits_for_new_draft(db, user)

    job_id = uuid.uuid4()
    input_key = build_input_key(
        user_id=user.id, job_id=job_id, filename=filename)

    job = Job(
        id=job_id,
        user_id=user.id,
        operation=operation,
        status=JobStatus.DRAFT,
        input_key=input_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    try:
        upload_url = await s3.create_presigned_upload_url_async(
            key=input_key,
            content_type=content_type,
        )
    except HTTPException:
        await db.delete(job)
        await db.commit()
        raise

    return job, upload_url, settings.s3_presign_expiry_seconds


async def start_draft_job(
    *,
    db: AsyncSession,
    user: User,
    job_id: uuid.UUID,
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise_api_error(
            code=ErrorCode.JOB_NOT_FOUND,
            message="Job not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if job.user_id != user.id:
        raise_api_error(
            code=ErrorCode.JOB_FORBIDDEN,
            message="Not allowed to start this job",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    if job.status != JobStatus.DRAFT:
        raise_api_error(
            code=ErrorCode.JOB_NOT_DRAFT,
            message=f"Job is not in draft status (current: {
                job.status.value})",
            status_code=status.HTTP_409_CONFLICT,
            logger=logger,
            job_id=str(job_id),
            current_status=job.status.value,
        )

    await s3.verify_upload_exists(job.input_key)

    if user.credits < 1:
        raise_api_error(
            code=ErrorCode.INSUFFICIENT_CREDITS,
            message="Insufficient credits to start this job",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
        )

    user.credits -= 1
    job.status = JobStatus.PENDING
    await db.commit()
    await db.refresh(job)
    await db.refresh(user)

    try:
        await job_queue.enqueue_job(str(job.id))
    except HTTPException:
        user.credits += 1
        job.status = JobStatus.DRAFT
        await db.commit()
        raise

    return job

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

import boto3
from botocore.config import Config
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.jobs import Job, JobStatus, Operation

from scripts.image.format_convertor import convert_image


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# Lambda executions are independent workers. Keep the pool deliberately
# small so concurrency does not multiply into a large number of DB
# connections.
#
# Example:
#
#   20 concurrent Lambda executions
#   x 1 DB connection per worker
#   = roughly 20 DB connections
#
# This is much safer than giving every Lambda execution a large pool.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=1,
    max_overflow=0,
    echo=settings.debug,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

@lru_cache
def get_s3_client():
    """
    Create and cache the S3 client.

    The API already uses the internal endpoint for server-side S3
    operations. The worker is also a server-side component, so it uses
    the same endpoint.
    """

    client_kwargs: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.aws_region,
        "config": Config(
            signature_version="s3v4",
            s3={
                "addressing_style": "path",
            },
        ),
    }

    if (
        settings.aws_access_key_id
        and settings.aws_secret_access_key
    ):
        client_kwargs["aws_access_key_id"] = (
            settings.aws_access_key_id
        )
        client_kwargs["aws_secret_access_key"] = (
            settings.aws_secret_access_key
        )

    if settings.aws_internal_endpoint_url:
        client_kwargs["endpoint_url"] = (
            settings.aws_internal_endpoint_url
        )
    elif settings.aws_region:
        client_kwargs["endpoint_url"] = (
            f"https://s3.{settings.aws_region}.amazonaws.com"
        )

    return boto3.client(**client_kwargs)


# ---------------------------------------------------------------------------
# Output key
# ---------------------------------------------------------------------------

def build_output_key(input_key: str) -> str:
    """
    Temporary fallback for output_key.

    Currently the API doesn't populate Job.output_key, so for the
    prototype we convert:

        uploads/<user>/<job>/photo.jpeg

    into:

        outputs/<user>/<job>/photo.png

    Later, when the requested output format is stored in the Job,
    this function can be replaced/expanded.
    """

    path = PurePosixPath(input_key)

    if len(path.parts) >= 2 and path.parts[0] == "uploads":
        output_parts = (
            "outputs",
            *path.parts[1:-1],
            f"{path.stem}.png",
        )

        return str(PurePosixPath(*output_parts))

    # Generic fallback if the input key doesn't follow the expected
    # uploads/<user>/<job>/<filename> structure.
    return str(path.with_suffix(".png"))


# ---------------------------------------------------------------------------
# Job claiming
# ---------------------------------------------------------------------------

async def claim_job(
    db: AsyncSession,
    job_id: UUID,
) -> Job | None:
    """
    Atomically claim a job.

    Only PENDING or FAILED jobs can be claimed.

    The important part is that the status check and status update
    happen inside the same SQL UPDATE statement.

    If two Lambda executions receive the same SQS message, only one
    of them should successfully change the job to PROCESSING.
    """

    now = datetime.now(timezone.utc)

    stmt = (
        update(Job)
        .where(
            Job.id == job_id,
            Job.status.in_(
                [
                    JobStatus.PENDING,
                    JobStatus.FAILED,
                ]
            ),
        )
        .values(
            status=JobStatus.PROCESSING,
            started_at=now,
            finished_at=None,
            error_message=None,
            retry_count=Job.retry_count + 1,
        )
        .returning(Job)
    )

    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if job is None:
        await db.rollback()

        # The job may already be completed or currently being
        # processed by another Lambda execution.
        result = await db.execute(
            select(Job).where(Job.id == job_id)
        )
        existing_job = result.scalar_one_or_none()

        if existing_job is None:
            raise ValueError(
                f"Job {job_id} does not exist"
            )

        logger.info(
            "Job %s was not claimed; current status is %s",
            job_id,
            existing_job.status.value,
        )

        return None

    await db.commit()

    logger.info(
        "Job %s claimed successfully",
        job_id,
    )

    return job


# ---------------------------------------------------------------------------
# S3 operations
# ---------------------------------------------------------------------------

def download_from_s3(
    *,
    bucket: str,
    key: str,
    destination: str,
) -> None:
    """
    Download an S3 object to a local file.

    boto3 is synchronous, so the caller runs this function in a
    worker thread.
    """

    logger.info(
        "Downloading s3://%s/%s -> %s",
        bucket,
        key,
        destination,
    )

    get_s3_client().download_file(
        bucket,
        key,
        destination,
    )


def upload_to_s3(
    *,
    bucket: str,
    key: str,
    source: str,
) -> None:
    """
    Upload a processed file to S3.
    """

    logger.info(
        "Uploading %s -> s3://%s/%s",
        source,
        bucket,
        key,
    )

    get_s3_client().upload_file(
        source,
        bucket,
        key,
        ExtraArgs={
            "ContentType": "image/png",
        },
    )


# ---------------------------------------------------------------------------
# Job status updates
# ---------------------------------------------------------------------------

async def mark_job_completed(
    db: AsyncSession,
    job_id: UUID,
    output_key: str,
) -> None:
    """
    Mark a successfully processed job as COMPLETED.
    """

    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JobStatus.COMPLETED,
            output_key=output_key,
            finished_at=datetime.now(timezone.utc),
            error_message=None,
        )
    )

    await db.commit()

    logger.info(
        "Job %s marked COMPLETED",
        job_id,
    )


async def mark_job_failed(
    db: AsyncSession,
    job_id: UUID,
    error: Exception,
) -> None:
    """
    Mark a job as FAILED.

    The exception is still re-raised by process_job() afterwards so
    Lambda/SQS knows that this particular record failed.
    """

    error_message = str(error)

    # Avoid putting an arbitrarily large exception into the DB.
    error_message = error_message[:4000]

    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JobStatus.FAILED,
            finished_at=datetime.now(timezone.utc),
            error_message=error_message,
        )
    )

    await db.commit()

    logger.exception(
        "Job %s failed: %s",
        job_id,
        error_message,
    )


# ---------------------------------------------------------------------------
# Job processing
# ---------------------------------------------------------------------------

async def process_job(
    job_id: UUID,
) -> None:
    """
    Process one Tinkertaps job.

    Flow:

        DB
         ↓
        claim
         ↓
        S3 download
         ↓
        image converter
         ↓
        S3 upload
         ↓
        DB COMPLETED
    """

    logger.info(
        "Starting job %s",
        job_id,
    )

    async with SessionLocal() as db:

        # ---------------------------------------------------------------
        # 1. Atomically claim the job
        # ---------------------------------------------------------------

        job = await claim_job(
            db=db,
            job_id=job_id,
        )

        if job is None:
            # Another Lambda invocation already owns the job, or the
            # job has already completed.
            return

        # ---------------------------------------------------------------
        # 2. Validate the operation
        # ---------------------------------------------------------------

        if job.operation != Operation.CONVERT:
            error = ValueError(
                f"Unsupported operation: {job.operation.value}"
            )

            await mark_job_failed(
                db,
                job_id,
                error,
            )

            raise error

        input_key = job.input_key

        # Use the DB value when it exists.
        #
        # Currently it doesn't get populated by the API, so the
        # temporary fallback creates a PNG output key.
        output_key = (
            job.output_key
            or build_output_key(input_key)
        )

        # ---------------------------------------------------------------
        # 3. Create Lambda temporary directory
        # ---------------------------------------------------------------

        job_directory = Path("/tmp") / str(job_id)

        input_path = job_directory / Path(
            PurePosixPath(input_key).name
        )

        output_path = job_directory / Path(
            PurePosixPath(output_key).name
        )

        job_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            # -----------------------------------------------------------
            # 4. Download input from S3
            # -----------------------------------------------------------

            await asyncio.to_thread(
                download_from_s3,
                bucket=settings.s3_bucket_name,
                key=input_key,
                destination=str(input_path),
            )

            # -----------------------------------------------------------
            # 5. Run the image converter
            # -----------------------------------------------------------

            logger.info(
                "Converting %s -> %s",
                input_path,
                output_path,
            )
            print(
                f"input_path={input_path!r}, "
                f"type={type(input_path)}, "
                f"output_path={output_path!r}, "
                f"type={type(output_path)}"
            )
            await asyncio.to_thread(
                convert_image,
                input_path,
                output_path,
            )

            # -----------------------------------------------------------
            # 6. Upload converted file to S3
            # -----------------------------------------------------------

            await asyncio.to_thread(
                upload_to_s3,
                bucket=settings.s3_bucket_name,
                key=output_key,
                source=str(output_path),
            )

            # -----------------------------------------------------------
            # 7. Mark job completed
            # -----------------------------------------------------------

            await mark_job_completed(
                db=db,
                job_id=job_id,
                output_key=output_key,
            )

            logger.info(
                "Job %s completed successfully",
                job_id,
            )

        except Exception as exc:
            # -----------------------------------------------------------
            # Processing failed.
            #
            # Record the failure in PostgreSQL, then re-raise so the
            # Lambda/SQS integration knows that this SQS record failed.
            # -----------------------------------------------------------

            try:
                await db.rollback()

                await mark_job_failed(
                    db=db,
                    job_id=job_id,
                    error=exc,
                )

            except Exception:
                # If updating the failure state itself fails, don't hide
                # the original processing exception.
                logger.exception(
                    "Could not update FAILED state for job %s",
                    job_id,
                )

            raise

        finally:
            # Lambda's /tmp directory is temporary. Clean up this job's
            # files so repeated invocations don't unnecessarily consume
            # ephemeral storage.
            shutil.rmtree(
                job_directory,
                ignore_errors=True,
            )


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

async def handle_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Process all SQS records in one Lambda invocation.

    Returns partial batch failures so that a failed message can be
    retried without forcing successful messages in the same batch
    to be retried.
    """

    batch_item_failures: list[dict[str, str]] = []

    records = event.get("Records", [])

    logger.info(
        "Received %d SQS record(s)",
        len(records),
    )

    for record in records:

        message_id = record.get("messageId")

        try:
            body = json.loads(record["body"])

            job_id = UUID(body["job_id"])

            logger.info(
                "Received SQS message %s for job %s",
                message_id,
                job_id,
            )

            await process_job(job_id)

        except Exception:
            logger.exception(
                "Failed to process SQS message %s",
                message_id,
            )

            if message_id:
                batch_item_failures.append(
                    {
                        "itemIdentifier": message_id,
                    }
                )

    return {
        "batchItemFailures": batch_item_failures,
    }


def lambda_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """
    AWS Lambda entry point.

    AWS invokes this synchronously, so we create the asyncio event
    loop for the invocation and run the async worker code inside it.
    """

    return asyncio.run(
        handle_event(event)
    )

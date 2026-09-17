from __future__ import annotations

import json
from functools import lru_cache

import boto3
from botocore.client import BaseClient

from app.core.config import settings
from app.core.errors import ErrorCode, raise_api_error
from app.core.logging import get_logger

logger = get_logger(__name__)


def _ensure_sqs_configured() -> None:
    if not settings.sqs_queue_url:
        raise_api_error(
            code=ErrorCode.QUEUE_UNAVAILABLE,
            message="SQS queue is not configured",
            status_code=503,
            logger=logger,
            log_message="SQS queue URL is missing",
        )


@lru_cache
def get_sqs_client() -> BaseClient:
    """Return a cached SQS client."""
    _ensure_sqs_configured()
    return boto3.client(
        "sqs",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
        endpoint_url=settings.aws_internal_endpoint_url
    )


def enqueue_job(job_id: str) -> str:
    """Send a job message to the SQS queue."""
    try:
        sqs = get_sqs_client()
        if not sqs:
            raise_api_error(
                code=ErrorCode.QUEUE_UNAVAILABLE,
                message="SQS client is not available",
                logger=logger,
                log_message="SQS client is None",
                job_id=job_id,
            )
            return

        message_body = json.dumps({"job_id": job_id})

        request = {
            "QueueUrl": settings.sqs_queue_url,
            "MessageBody": message_body,
        }

        response = sqs.send_message(**request)

        message_id = response["MessageId"]

        logger.info(
            "Job enqueued successfully",
            extra={
                "job_id": job_id,
                "message_id": message_id,
            },
        )

        return message_id

    except Exception as exc:
        raise_api_error(
            code=ErrorCode.QUEUE_UNAVAILABLE,
            message="Failed to enqueue job for processing",
            status_code=503,
            logger=logger,
            log_message="SQS enqueue failed",
            exc=exc,
            job_id=job_id,
        )


def receive_job() -> dict | None:
    """Receive a single job message from SQS.

    Returns the raw SQS message or None when the queue is empty.
    """
    try:
        sqs = get_sqs_client()

        response = sqs.receive_message(
            QueueUrl=settings.sqs_queue_url,
            MaxNumberOfMessages=1,
            MessageAttributeNames=["All"],
            AttributeNames=["All"],
            VisibilityTimeout=30,
            WaitTimeSeconds=10,
        )

        messages = response.get("Messages", [])

        if not messages:
            return None

        return messages[0]

    except Exception as exc:
        raise_api_error(
            code=ErrorCode.QUEUE_UNAVAILABLE,
            message="Failed to receive job from SQS",
            status_code=503,
            logger=logger,
            log_message="SQS receive failed",
            exc=exc,
        )


def delete_message(receipt_handle: str) -> None:
    """Delete a successfully processed message from SQS."""
    try:
        sqs = get_sqs_client()

        sqs.delete_message(
            QueueUrl=settings.sqs_queue_url,
            ReceiptHandle=receipt_handle,
        )

    except Exception as exc:
        raise_api_error(
            code=ErrorCode.QUEUE_UNAVAILABLE,
            message="Failed to delete SQS message",
            status_code=503,
            logger=logger,
            log_message="SQS message deletion failed",
            exc=exc,
        )

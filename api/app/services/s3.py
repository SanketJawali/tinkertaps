from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.errors import ErrorCode, raise_api_error
from app.core.logging import get_logger

logger = get_logger(__name__)


def _ensure_s3_configured() -> None:
    if not settings.s3_bucket_name:
        raise_api_error(
            code=ErrorCode.STORAGE_NOT_CONFIGURED,
            message="Object storage is not configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            logger=logger,
            log_message="S3 bucket name is missing",
        )


@lru_cache
def get_s3_client() -> BaseClient:
    _ensure_s3_configured()

    # Force the regional endpoint. boto3 often signs URLs against
    # s3.amazonaws.com even when region_name is set; browsers then hit
    # redirects / Host mismatches that show up as PUT 403.
    client_kwargs: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.aws_region,
        "config": Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
        ),
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.s3_endpoint_url:
        logger.debug("Using custom S3 endpoint URL: %s", settings.s3_endpoint_url)
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url
    elif settings.aws_region:
        client_kwargs["endpoint_url"] = (
            f"https://s3.{settings.aws_region}.amazonaws.com"
        )

    return boto3.client(**client_kwargs)


def create_presigned_upload_url(
    *,
    key: str,
    content_type: str,
    expires_in: int | None = None,
) -> str:
    client = get_s3_client()
    expiry = expires_in or settings.s3_presign_expiry_seconds
    try:
        return client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expiry,
        )
    except (ClientError, BotoCoreError) as exc:
        raise_api_error(
            code=ErrorCode.STORAGE_UNAVAILABLE,
            message="Failed to generate upload URL",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            logger=logger,
            log_message="S3 presign failed",
            exc=exc,
            key=key,
        )


def object_exists(key: str) -> bool:
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.s3_bucket_name, Key=key)
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise_api_error(
            code=ErrorCode.STORAGE_UNAVAILABLE,
            message="Failed to verify uploaded file",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            logger=logger,
            log_message="S3 head_object failed",
            exc=exc,
            key=key,
        )
    except BotoCoreError as exc:
        raise_api_error(
            code=ErrorCode.STORAGE_UNAVAILABLE,
            message="Failed to verify uploaded file",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            logger=logger,
            log_message="S3 head_object failed",
            exc=exc,
            key=key,
        )


async def create_presigned_upload_url_async(
    *,
    key: str,
    content_type: str,
    expires_in: int | None = None,
) -> str:
    return await asyncio.to_thread(
        create_presigned_upload_url,
        key=key,
        content_type=content_type,
        expires_in=expires_in,
    )


async def verify_upload_exists(key: str) -> None:
    exists = await asyncio.to_thread(object_exists, key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCode.UPLOAD_NOT_FOUND,
                "message": (
                    "Uploaded file not found in storage. Complete the upload first."
                ),
            },
        )

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app.core.config import settings


@lru_cache
def get_s3_client() -> BaseClient:
    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME is not configured")

    client_kwargs: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.aws_region,
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url

    return boto3.client(**client_kwargs)


def create_presigned_upload_url(
    *,
    key: str,
    content_type: str,
    expires_in: int | None = None,
) -> str:
    client = get_s3_client()
    expiry = expires_in or settings.s3_presign_expiry_seconds
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expiry,
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
        raise


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
            detail="Uploaded file not found in storage. Complete the upload first.",
        )

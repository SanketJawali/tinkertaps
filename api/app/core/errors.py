from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException


class ErrorCode:
    AUTH_NOT_CONFIGURED = "auth_not_configured"
    INVALID_FILENAME = "invalid_filename"
    INSUFFICIENT_CREDITS = "insufficient_credits"
    JOB_NOT_FOUND = "job_not_found"
    JOB_FORBIDDEN = "job_forbidden"
    JOB_NOT_DRAFT = "job_not_draft"
    UPLOAD_NOT_FOUND = "upload_not_found"
    STORAGE_NOT_CONFIGURED = "storage_not_configured"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    QUEUE_UNAVAILABLE = "queue_unavailable"


def api_error(
    *,
    code: str,
    message: str,
    status_code: int,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def raise_api_error(
    *,
    code: str,
    message: str,
    status_code: int,
    logger: logging.Logger | None = None,
    log_message: str | None = None,
    exc: BaseException | None = None,
    **context: Any,
) -> None:
    if logger is not None:
        extra = {"error_code": code, **context}
        if exc is not None:
            logger.error(log_message or message, extra=extra, exc_info=exc)
        else:
            logger.warning(log_message or message, extra=extra)

    raise api_error(code=code, message=message, status_code=status_code) from exc

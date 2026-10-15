import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.jobs import JobStatus, Operation
from app.core.logging import get_logger

logger = get_logger(__name__)


class OperationOptions(BaseModel):
    target_size_bytes: int | None = Field(default=None, gt=0)
    max_width: int | None = Field(default=None, gt=0)
    max_height: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid")


class PresignRequest(BaseModel):
    operation: Operation
    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[\w.+-]+/[\w.+-]+$",
    )
    operation_options: OperationOptions | None = None

    @model_validator(mode="after")
    def validate_operation_options(self) -> "PresignRequest":
        options = self.operation_options
        if options is None:
            return self

        if self.operation == Operation.COMPRESS:
            if options.max_width is not None or options.max_height is not None:
                raise ValueError(
                    "max_width and max_height are only valid for downsample"
                )
        elif self.operation == Operation.DOWNSAMPLE:
            if options.target_size_bytes is not None:
                raise ValueError(
                    "target_size_bytes is only valid for compress"
                )
        else:
            raise ValueError(
                "operation_options are only valid for compress or downsample"
            )

        return self


class PresignResponse(BaseModel):
    job_id: uuid.UUID
    upload_url: str
    input_key: str
    expires_in: int


class StartJobRequest(BaseModel):
    """Optional body for starting a draft job after upload completes."""

    logger.debug("StartJobRequest model initialized")


class StartJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    operation: Operation
    operation_options: dict[str, Any] | None = None
    input_key: str
    credits_remaining: int


class JobStatusPollResponse(BaseModel):
    id: uuid.UUID
    status: JobStatus
    operation: Operation
    operation_options: dict[str, Any] | None = None
    error_message: str | None = None
    download_url: str | None = None
    download_expires_in: int | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    operation: Operation
    operation_options: dict[str, Any] | None = None
    status: JobStatus
    input_key: str
    output_key: str | None
    retry_count: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

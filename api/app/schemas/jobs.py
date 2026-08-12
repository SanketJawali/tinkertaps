import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.jobs import JobStatus, Operation


class PresignRequest(BaseModel):
    operation: Operation
    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(..., min_length=1, max_length=255)


class PresignResponse(BaseModel):
    job_id: uuid.UUID
    upload_url: str
    input_key: str
    expires_in: int


class StartJobRequest(BaseModel):
    """Optional body for starting a draft job after upload completes."""

    pass


class StartJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    operation: Operation
    input_key: str
    credits_remaining: int


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    operation: Operation
    status: JobStatus
    input_key: str
    output_key: str | None
    retry_count: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

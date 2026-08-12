import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, apply_anon_cookie, get_auth_context
from app.db.session import get_db
from app.schemas.jobs import PresignRequest, PresignResponse, StartJobResponse
from app.services import jobs as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


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
    pending, and push it onto the Redis processing queue.
    """
    job = await job_service.start_draft_job(
        db=db,
        user=auth.user,
        job_id=job_id,
    )
    apply_anon_cookie(response, auth)
    return StartJobResponse(
        id=job.id,
        status=job.status,
        operation=job.operation,
        input_key=job.input_key,
        credits_remaining=auth.user.credits,
    )

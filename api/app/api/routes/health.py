from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    payload = {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "connected",
    }

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        payload["status"] = "error"
        payload["database"] = "disconnected"
        payload["detail"] = str(exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)

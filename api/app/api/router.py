from fastapi import APIRouter

from app.api.routes import health, job

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(job.router)

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.session import engine
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.request_id import RequestIdMiddleware

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (%s)",
        settings.app_name,
        settings.environment,
    )
    yield
    await engine.dispose()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        redirect_slashes=True,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.include_router(api_router)

    register_exception_handlers(app)
    return app


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception",
            extra={"request_id": getattr(request.state, "request_id", None)},
        )
        detail: Any = "Internal server error"
        if settings.debug:
            detail = str(exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": detail,
                "request_id": getattr(request.state, "request_id", None),
            },
        )


app = create_app()

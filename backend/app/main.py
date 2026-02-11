import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routers.health import router as health_router
from app.api.routers.progress import router as progress_router
from app.api.routers.reflections import router as reflections_router
from app.api.routers.scenes import router as scenes_router
from app.api.routers.sessions import router as sessions_router
from app.core.config import settings
from app.core.errors import (
    ApiError,
    ErrorCode,
    build_error_payload,
    map_status_to_error_code,
)

logger = logging.getLogger("nvc.api")


def _request_id_from(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return str(uuid4())


def _error_response(status_code: int, error_code: ErrorCode, message: str, request: Request):
    return JSONResponse(
        status_code=status_code,
        content=build_error_payload(
            error_code=error_code,
            message=message,
            request_id=_request_id_from(request),
        ),
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="NVC Practice Coach API",
        version="0.1.0",
        description="FastAPI backend for NVC Practice Coach MVP",
    )

    origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if "*" not in origins else ["*"],
        allow_origin_regex=settings.cors_origin_regex if "*" not in origins else None,
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id_header(request: Request, call_next):
        request_id = request.headers.get("x-request-id", "").strip() or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return _error_response(exc.status_code, exc.error_code, exc.message, request)

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        message = str(first.get("msg", "request validation failed"))
        return _error_response(400, ErrorCode.VALIDATION_ERROR, message, request)

    @app.exception_handler(HTTPException)
    async def fastapi_http_exception_handler(request: Request, exc: HTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "request failed"
        return _error_response(
            exc.status_code,
            map_status_to_error_code(exc.status_code),
            message,
            request,
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "request failed"
        return _error_response(
            exc.status_code,
            map_status_to_error_code(exc.status_code),
            message,
            request,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception", extra={"request_id": _request_id_from(request)})
        return _error_response(
            500,
            ErrorCode.INTERNAL_ERROR,
            "internal server error",
            request,
        )

    app.include_router(health_router)
    app.include_router(scenes_router)
    app.include_router(sessions_router)
    app.include_router(reflections_router)
    app.include_router(progress_router)

    return app


app = create_app()

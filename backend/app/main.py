import json
import logging
from time import perf_counter
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
from app.core.observability import observability_registry

logger = logging.getLogger("nvc.api")
request_logger = logging.getLogger("nvc.api.request")


def _request_id_from(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return str(uuid4())


def _route_template_from(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if isinstance(template, str) and template:
        return template
    return request.url.path


def _configure_logging() -> None:
    normalized = settings.log_level.strip().upper()
    level = getattr(logging, normalized, logging.INFO)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    logger.setLevel(level)
    request_logger.setLevel(level)


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
    _configure_logging()
    observability_registry.configure(
        max_recent_errors=settings.observability_recent_error_limit
    )
    observability_registry.reset()
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
        started_at = perf_counter()
        response = None
        status_code = 500
        path = request.url.path
        route = path
        try:
            response = await call_next(request)
            status_code = response.status_code
            route = _route_template_from(request)
            return response
        finally:
            latency_ms = (perf_counter() - started_at) * 1000
            is_slow = latency_ms >= settings.slow_request_ms
            observability_registry.observe(
                request_id=request_id,
                method=request.method,
                path=path,
                route=route,
                status_code=status_code,
                latency_ms=latency_ms,
                is_slow=is_slow,
            )
            request_logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": request.method,
                        "path": path,
                        "route": route,
                        "status_code": status_code,
                        "latency_ms": round(latency_ms, 2),
                        "is_slow": is_slow,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id

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

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from slowapi.errors import RateLimitExceeded

from app.core.logging import security_logger


def error_response(
    status_code: int,
    code: str,
    message: str,
    details=None,
):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        423: "ACCOUNT_LOCKED",
        429: "RATE_LIMIT_EXCEEDED",
    }

    return error_response(
        status_code=exc.status_code,
        code=code_map.get(exc.status_code, "HTTP_ERROR"),
        message=str(exc.detail),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Invalid request data",
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    security_logger.exception(
        "Unhandled exception: path=%s method=%s",
        request.url.path,
        request.method,
    )

    return error_response(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    return error_response(
        status_code=429,
        code="RATE_LIMIT_EXCEEDED",
        message="Too many requests. Please try again later.",
        details={
            "limit": str(exc.detail),
        },
    )
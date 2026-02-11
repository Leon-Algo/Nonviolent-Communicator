from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    error_code: ErrorCode
    message: str


def map_status_to_error_code(status_code: int) -> ErrorCode:
    if status_code in (400, 422):
        return ErrorCode.VALIDATION_ERROR
    if status_code == 401:
        return ErrorCode.UNAUTHORIZED
    if status_code == 403:
        return ErrorCode.FORBIDDEN
    if status_code == 404:
        return ErrorCode.NOT_FOUND
    if status_code == 409:
        return ErrorCode.CONFLICT
    if status_code == 429:
        return ErrorCode.RATE_LIMITED
    return ErrorCode.INTERNAL_ERROR


def build_error_payload(error_code: ErrorCode, message: str, request_id: str) -> dict:
    return {
        "error_code": error_code.value,
        "message": message,
        "request_id": request_id,
    }

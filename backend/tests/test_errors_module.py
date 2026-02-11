from app.core.errors import ErrorCode, map_status_to_error_code


def test_map_status_to_error_code():
    assert map_status_to_error_code(400) == ErrorCode.VALIDATION_ERROR
    assert map_status_to_error_code(422) == ErrorCode.VALIDATION_ERROR
    assert map_status_to_error_code(401) == ErrorCode.UNAUTHORIZED
    assert map_status_to_error_code(403) == ErrorCode.FORBIDDEN
    assert map_status_to_error_code(404) == ErrorCode.NOT_FOUND
    assert map_status_to_error_code(409) == ErrorCode.CONFLICT
    assert map_status_to_error_code(429) == ErrorCode.RATE_LIMITED
    assert map_status_to_error_code(500) == ErrorCode.INTERNAL_ERROR

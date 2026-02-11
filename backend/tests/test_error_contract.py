from fastapi.testclient import TestClient

from app.main import create_app

TEST_USER_HEADER = {
    "Authorization": "Bearer mock_8a4c3f2a-2f88-4c74-9bc0-3123d26df302"
}


def _assert_error_contract(payload: dict):
    assert set(payload.keys()) == {"error_code", "message", "request_id"}
    assert isinstance(payload["error_code"], str) and payload["error_code"]
    assert isinstance(payload["message"], str) and payload["message"]
    assert isinstance(payload["request_id"], str) and payload["request_id"]


def test_404_response_uses_error_contract():
    client = TestClient(create_app())
    response = client.get("/path-not-exist")
    assert response.status_code == 404

    payload = response.json()
    _assert_error_contract(payload)
    assert payload["error_code"] == "NOT_FOUND"
    assert response.headers.get("X-Request-ID")


def test_401_response_uses_error_contract():
    client = TestClient(create_app())
    response = client.post("/api/v1/scenes", json={})
    assert response.status_code == 401

    payload = response.json()
    _assert_error_contract(payload)
    assert payload["error_code"] == "UNAUTHORIZED"


def test_validation_error_uses_error_contract():
    client = TestClient(create_app())
    response = client.get("/api/v1/progress/weekly", headers=TEST_USER_HEADER)
    assert response.status_code == 400

    payload = response.json()
    _assert_error_contract(payload)
    assert payload["error_code"] == "VALIDATION_ERROR"

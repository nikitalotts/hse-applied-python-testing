import json
import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from src.links.exception_handlers import api_error_handler, global_exception_handler
from src.links.exceptions import APIError


@pytest.fixture
def mock_request():
    return Request(scope={"type": "http"})


@pytest.mark.anyio
@pytest.mark.parametrize("status_code, detail, headers", [
    (400, "Bad request", {"X-Error": "test"}),
    (404, "Not found", None),
    (409, "Conflict", {"Retry-After": "120"}),
])
async def test_api_error_handler(mock_request, status_code, detail, headers):
    exc = APIError(status_code=status_code, detail=detail, headers=headers)

    response = await api_error_handler(mock_request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status_code
    assert response.body == b'{"detail":"%s"}' % detail.encode()
    assert response.headers.get("content-type") == "application/json"

    if headers:
        for key, value in headers.items():
            assert response.headers.get(key) == value
    else:
        assert not any(key.startswith("X-") for key in response.headers)


@pytest.mark.anyio
@pytest.mark.parametrize("exception", [
    ValueError("Test error"),
    KeyError("Missing key"),
    TypeError("Invalid type"),
])
async def test_global_exception_handler(mock_request, exception):
    response = await global_exception_handler(mock_request, exception)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    assert json.loads(response.body.decode("utf-8")) == {"detail": "Internal server error"}
    assert response.headers.get("content-type") == "application/json"

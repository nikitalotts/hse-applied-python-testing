import sys
import pytest
import runpy
from httpx import AsyncClient, ASGITransport
from fastapi.middleware.cors import CORSMiddleware
from unittest.mock import patch

from src.main import app, current_user
from src.links.exceptions import APIError


@pytest.mark.anyio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_exception_handlers_registration():
    handlers = app.exception_handlers
    assert APIError in handlers
    assert Exception in handlers


@pytest.mark.anyio
async def test_cors_middleware_added():
    middleware_classes = [m.cls for m in app.user_middleware]
    assert CORSMiddleware in middleware_classes


@pytest.mark.anyio
async def test_router_inclusion():
    paths = [route.path for route in app.routes]
    assert "/health" in paths


@pytest.mark.anyio
async def test_current_user_callable():
    assert callable(current_user)


def test_uvicorn_run():
    run_called = False

    def fake_run(app_str, host, port, reload):
        nonlocal run_called
        run_called = True
        assert app_str == "main:app"
        assert host == "localhost"
        assert port == 8000
        assert reload is True
    with patch("uvicorn.run", fake_run):
        if 'src.main' in sys.modules:
            module = sys.modules.pop('src.main')
            try:
                runpy.run_module("src.main", run_name="__main__")
            finally:
                sys.modules['src.main'] = module
        else:
            runpy.run_module("src.main", run_name="__main__")
    assert run_called

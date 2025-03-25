import pytest
import runpy
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from src.admin.router import _get_all_cache_keys
from src.main import app
from src.auth.users import get_admin_user
from src.auth.models import User


@pytest.fixture(autouse=True)
def override_get_admin_user():
    dummy_admin = User(id=1, email="admin@example.com", is_superuser=True)
    app.dependency_overrides[get_admin_user] = lambda: dummy_admin
    yield
    app.dependency_overrides.pop(get_admin_user, None)


@pytest.mark.anyio
async def test_get_cache_keys():
    mock_keys = ["key1", "key2", "key3"]
    with patch("src.admin.router._get_all_cache_keys", new=AsyncMock(return_value=mock_keys)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/admin/cache-keys")
        assert response.status_code == 200
        assert response.json() == mock_keys


@pytest.mark.anyio
async def test__get_all_cache_keys():
    mock_redis = MagicMock()
    async def mock_scan_iter():
        yield b"key1"
        yield b"key2"
    mock_redis.scan_iter.return_value = mock_scan_iter()
    with patch("src.admin.router.aioredis.from_url", return_value=mock_redis):
        keys = await _get_all_cache_keys()
    assert keys == ["key1", "key2"]
    mock_redis.scan_iter.assert_called_once_with(match="*")


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
        import sys
        if "src.main" in sys.modules:
            del sys.modules["src.main"]
        runpy.run_module("src.main", run_name="__main__")
    assert run_called

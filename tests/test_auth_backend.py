import sys
import pytest
import importlib
from unittest.mock import AsyncMock, patch
from fastapi_users.authentication import (
    BearerTransport,
    CookieTransport,
    JWTStrategy,
    RedisStrategy,
)
from src.auth.backend import (
    bearer_transport,
    cookie_transport,
    get_jwt_strategy,
    get_redis_strategy,
    auth_backend,
    redis,
    Settings
)


@pytest.mark.asyncio
def test_transports():
    assert isinstance(bearer_transport, BearerTransport)
    assert isinstance(cookie_transport, CookieTransport)
    assert cookie_transport.cookie_name == "su"
    assert cookie_transport.cookie_max_age == 3600


@pytest.mark.asyncio
def test_get_jwt_strategy():
    with patch("src.auth.backend.Settings") as mock_settings:
        mock_settings.return_value.JWT_SECRET_KEY = "secret"
        strategy = get_jwt_strategy()
        assert isinstance(strategy, JWTStrategy)
        assert strategy.secret == "secret"
        assert strategy.lifetime_seconds == 3600


@pytest.mark.asyncio
async def test_get_redis_strategy():
    mock_redis = AsyncMock()
    with patch("src.auth.backend.redis", mock_redis):
        strategy = get_redis_strategy()
        assert isinstance(strategy, RedisStrategy)
        assert strategy.redis is mock_redis
        assert strategy.lifetime_seconds == 3600


@pytest.mark.asyncio
def test_auth_backend():
    assert auth_backend.name == "cookie"
    assert auth_backend.transport is cookie_transport
    strategy = auth_backend.get_strategy()
    assert isinstance(strategy, RedisStrategy)
    assert strategy.redis is redis
    assert strategy.lifetime_seconds == 3600


@pytest.mark.asyncio
def test_redis_initialization():
    with patch("redis.asyncio.Redis.from_url") as mock_from_url:
        if 'src.auth.backend' in sys.modules:
            original_redis = sys.modules['src.auth.backend'].redis
        import src.auth.backend
        importlib.reload(src.auth.backend)
        mock_from_url.assert_called_once_with(
            Settings().MESSAGE_BROKER_URL,
            decode_responses=True
        )
        assert src.auth.backend.redis is mock_from_url.return_value
        if 'original_redis' in locals():
            sys.modules['src.auth.backend'].redis = original_redis

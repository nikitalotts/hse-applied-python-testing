import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from src.database import (
    DbBase,
    engine,
    async_session_maker,
    sync_engine,
    sync_session_maker,
    get_async_session
)


@pytest.mark.anyio
def test_db_base_class():
    assert issubclass(DbBase, AsyncAttrs)
    assert issubclass(DbBase, DeclarativeBase)


@pytest.mark.anyio
def test_async_engine_initialization():
    assert "asyncpg" in str(engine.url)
    assert engine.echo is True


@pytest.mark.anyio
def test_async_session_maker():
    assert async_session_maker.kw["expire_on_commit"] is False
    assert async_session_maker.kw["bind"] is engine


@pytest.mark.anyio
def test_sync_engine():
    assert "postgresql" in str(sync_engine.url)
    assert "asyncpg" not in str(sync_engine.url)


@pytest.mark.anyio
def test_sync_session_maker():
    assert sync_session_maker.kw["expire_on_commit"] is False
    assert sync_session_maker.kw["bind"] is sync_engine


@pytest.mark.anyio
async def test_get_async_session():
    mock_session = MagicMock(spec=AsyncSession)
    with patch("src.database.async_session_maker") as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        gen = get_async_session()
        session = await gen.__anext__()
        assert session == mock_session
        mock_session_maker.assert_called_once()

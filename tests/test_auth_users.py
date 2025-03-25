import pytest
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch
from src.auth.users import (
    User,
    UserManager,
    get_user_db,
    get_user_manager
)


@pytest.mark.anyio
def test_user_model():
    assert User.__tablename__ == "user"
    assert hasattr(User, "email")
    assert hasattr(User, "hashed_password")
    assert hasattr(User, "is_active")
    assert hasattr(User, "is_superuser")
    assert User.__table__.columns["email"].type.__class__.__name__ == "String"
    assert User.__table__.columns["is_superuser"].type.__class__.__name__ == "Boolean"


@pytest.mark.anyio
def test_user_manager_config():
    assert issubclass(UserManager, IntegerIDMixin)
    assert issubclass(UserManager, BaseUserManager)


@pytest.mark.anyio
async def test_get_user_db():
    mock_session = AsyncMock(spec=AsyncSession)
    with patch("src.database.get_async_session", return_value=mock_session):
        user_db_gen = get_user_db()
        user_db = await user_db_gen.__anext__()
        assert isinstance(user_db, SQLAlchemyUserDatabase)
        assert user_db.user_table == User


@pytest.mark.anyio
async def test_get_user_manager():
    mock_user_db = MagicMock(spec=SQLAlchemyUserDatabase)
    async def mock_get_user_db():
        yield mock_user_db
    with patch("src.auth.users.get_user_db", side_effect=mock_get_user_db):
        user_manager_gen = get_user_manager()
        user_manager = await user_manager_gen.__anext__()
        assert isinstance(user_manager, UserManager)

import uuid
from datetime import datetime
from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.backend import auth_backend
from src.config import Settings
from src.database import get_async_session, DbBase
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import Integer, String, DateTime, Column, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.auth.models import User


SECRET = Settings().PASSWORD_SECRET_KEY


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])
get_current_user_or_none = fastapi_users.current_user(optional=True)
get_current_user = fastapi_users.current_user()
get_admin_user = fastapi_users.current_user(superuser=True)

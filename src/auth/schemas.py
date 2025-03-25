import uuid
from fastapi_users import schemas
from datetime import datetime


class UserRead(schemas.BaseUser[int]):
    email: str
    registered_at: datetime


class UserCreate(schemas.BaseUserCreate):
    email: str
    password: str


class UserUpdate(schemas.BaseUserUpdate):
    pass
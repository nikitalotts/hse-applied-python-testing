from fastapi import APIRouter, Depends
from redis import asyncio as aioredis

from src.auth.models import User
from src.auth.users import get_admin_user
from src.config import Settings

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)


@router.get("/cache-keys", response_model=list[str])
async def get_cache_keys(
        superuser: User = Depends(get_admin_user)
):
    keys = await _get_all_cache_keys()
    return keys


async def _get_all_cache_keys(pattern: str = "*") -> list[str]:
    redis = aioredis.from_url(Settings().MESSAGE_BROKER_URL)
    keys = []
    async for key in redis.scan_iter(match=pattern):
        keys.append(key.decode("utf-8"))
    return keys

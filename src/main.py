import aioredis
import uvicorn
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from src.admin.router import router as admin_router
from src.auth.router import add_auth_routers
from src.auth.users import fastapi_users
from src.config import Settings
from src.links.exception_handlers import api_error_handler, global_exception_handler
from src.links.exceptions import APIError
from src.links.router import router as links_router
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url(Settings().MESSAGE_BROKER_URL)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    yield

app = FastAPI(
    lifespan=lifespan,
    proxy_headers=True,
    title="Short URL API",
)

app.include_router(links_router)
app.include_router(admin_router)
add_auth_routers(app)

current_user = fastapi_users.current_user(active=True)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=[Settings().SITE_IP],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, global_exception_handler)


if __name__ == '__main__':
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)

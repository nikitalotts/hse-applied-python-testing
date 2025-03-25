from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.links.service import LinkService


async def get_link_service(
    session: AsyncSession = Depends(get_async_session)
) -> LinkService:
    return LinkService(session)

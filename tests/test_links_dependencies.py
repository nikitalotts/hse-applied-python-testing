
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
from src.links.dependencies import get_link_service
from src.links.service import LinkService


@pytest.mark.asyncio
async def test_get_link_service_creation():
    mock_session = AsyncMock(spec=AsyncSession)
    with patch("src.database.get_async_session", return_value=mock_session):
        link_service = await get_link_service()
        assert isinstance(link_service, LinkService)


@pytest.mark.asyncio
async def test_dependency_resolution_chain():
    mock_session = AsyncMock(spec=AsyncSession)
    with patch("src.database.get_async_session", return_value=mock_session):
        link_service = await get_link_service()
        assert isinstance(link_service, LinkService)

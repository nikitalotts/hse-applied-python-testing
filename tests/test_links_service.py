import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.auth.models import User
from src.config import Settings
from src.links.models import Link
from src.links.schemes import UpdateLinkRequest
from src.links.service import LinkService
from src.links.exceptions import (
    NonUniqueAliasError,
    AliasLengthError,
    UrlAlreadyExists,
    LinkNotFoundError,
    NonUniqueShortCodeError,
    PermissionDenied,
)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def link_service(mock_session):
    return LinkService(mock_session)


@pytest.fixture
def user():
    return User(id=1, email="test@mail.com")


@pytest.mark.anyio
async def test_find_by_long_url_found(link_service, mock_session):
    test_url = "http://test.com"
    mock_link = Link(long_url=test_url)
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))

    result = await link_service.find_by_long_url(test_url)
    assert result == mock_link


@pytest.mark.anyio
async def test_find_by_long_url_not_found(link_service, mock_session):
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    with pytest.raises(LinkNotFoundError):
        await link_service.find_by_long_url("http://test.com")


@pytest.mark.anyio
async def test_get_link_found(link_service, mock_session):
    mock_link = Link(short_code="short")
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
    result = await link_service.get("short")
    assert result == mock_link


@pytest.mark.anyio
async def test_get_link_not_found(link_service, mock_session):
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    with pytest.raises(LinkNotFoundError):
        await link_service.get("short")


@pytest.mark.anyio
async def test_get_stats(link_service, mock_session):
    mock_link = Link(short_code="short", redirect_counter=5)
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
    result = await link_service.get_stats("short")
    assert result.redirect_counter == 5


@pytest.mark.anyio
async def test_get_stats_link_not_found(link_service, mock_session):
    with pytest.raises(LinkNotFoundError):
        mock_link = None
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
        result = await link_service.get_stats("short")
        assert result.redirect_counter == 5

@pytest.mark.anyio
async def test_create(link_service, mock_session, user):
    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]
    link = await link_service.create(
        long_url="http://test.com",
        custom_alias=None,
        user=user
    )
    assert link.long_url == "http://test.com"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()

@pytest.mark.anyio
async def test_create_with_custom_alias_success(link_service, mock_session, user):
    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]
    link = await link_service.create(
        long_url="http://test.com",
        custom_alias="short",
        user=user
    )
    assert link.short_code == "short"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_create_with_non_unique_alias(link_service, mock_session):
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=Link()))
    with pytest.raises(UrlAlreadyExists):
        await link_service.create("http://test.com", custom_alias="short")


@pytest.mark.anyio
async def test_create_with_duplicate_url(link_service, mock_session):
    mock_session.execute.return_value = (
        MagicMock(scalar_one_or_none=MagicMock(return_value=Link(long_url="http://test.com"))))
    with pytest.raises(UrlAlreadyExists):
        await link_service.create(long_url="http://test.com")


@pytest.mark.anyio
async def test_create_with_alias_length_error(link_service, mock_session):
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    with pytest.raises(AliasLengthError):
        await link_service.create(long_url="http://test.com", custom_alias="sho")


@pytest.mark.anyio
async def test_delete_success(link_service, mock_session, user):
    mock_link = Link(short_code="short", author_id=user.id)
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
    with patch('src.links.utils.FastAPICache') as mock_fastapi_cache:
        mock_backend = AsyncMock()
        mock_fastapi_cache.get_backend.return_value = mock_backend
        result = await link_service.delete("short", user)
        mock_backend.clear.assert_called()
    mock_session.execute.assert_awaited()
    mock_session.commit.assert_awaited_once()
    assert result == mock_link


@pytest.mark.anyio
async def test_delete_permission_denied(link_service, mock_session, user):
    mock_link = Link(short_code="short", author_id=42)
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
    with pytest.raises(PermissionDenied):
        await link_service.delete("short", user)


@pytest.mark.anyio
async def test_delete_link_not_found(link_service, mock_session, user):
    mock_link = None
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
    with pytest.raises(LinkNotFoundError):
        await link_service.delete("short", user)


@pytest.mark.anyio
async def test_update_success(link_service, mock_session, user):
    mock_link = Link(
        short_code="short1",
        long_url="http://test.com",
        expires_at=None,
        author_id=user.id
    )
    update_data = UpdateLinkRequest(
        original_url="http://testnew.com",
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]
    with patch('src.links.utils.FastAPICache') as mock_fastapi_cache:
        mock_backend = AsyncMock()
        mock_fastapi_cache.get_backend.return_value = mock_backend
        result = await link_service.update("short1", user, update_data)
        mock_backend.clear.assert_called()
    assert result.long_url == "http://testnew.com"
    mock_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_short_code_unique_or_raise_should_raise_error(link_service):
    short_code = "short"
    with patch.object(link_service, '_is_short_code_unique', return_value=False):
        with pytest.raises(NonUniqueShortCodeError):
            await link_service._short_code_unique_or_raise(short_code)


@pytest.mark.anyio
async def test_create_should_raise_value_error_on_exceeded_attempts(link_service):
    with patch.object(link_service, '_url_unique_or_raise', return_value=None), \
         patch.object(link_service, '_alias_unique_or_raise', return_value=None), \
         patch.object(link_service, '_generate_short_code', return_value="short"), \
         patch.object(link_service, '_is_short_code_unique', return_value=False):
        with pytest.raises(ValueError, match="Cannot create short link"):
            await link_service.create(long_url="https://test.com")


@pytest.mark.anyio
async def test_update_permission_denied(link_service, mock_session):
    user = User(id=2)
    mock_link = MagicMock(author_id=1)
    update_data = UpdateLinkRequest(
        original_url="http://test.com",
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
    with pytest.raises(PermissionDenied):
        await link_service.update("short", user, update_data)


@pytest.mark.anyio
async def test_update_link_not_found(link_service, mock_session):
    user = User(id=2)
    mock_link = None
    update_data = UpdateLinkRequest(
        original_url="http://test.com",
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
    with pytest.raises(LinkNotFoundError):
        await link_service.update("short", user, update_data)


@pytest.mark.anyio
async def test_get_all_redirect_links(link_service, mock_session):
    mock_links = [Link(), Link()]
    mock_session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_links))))
    result = await link_service.get_all_redirect_links()
    assert len(result) == 2


@pytest.mark.anyio
async def test_get_links_by_author(link_service, mock_session, user):
    mock_links = [Link(author_id=user.id), Link(author_id=user.id)]
    mock_session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_links))))
    result = await link_service.get_links_by_author(user.id)
    assert len(result) == 2


@pytest.mark.anyio
async def test_increment_counter(link_service, mock_session):
    mock_link = Link(redirect_counter=0)
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_link))
    await link_service.increment_counter("short")
    assert mock_link.redirect_counter == 1
    mock_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_generate_short_code(link_service):
    code = await link_service._generate_short_code("http://test.com")
    assert len(code) == Settings().SHORT_CODE_LENGTH


@pytest.mark.anyio
async def test_alias_unique_check_fail(link_service, mock_session):
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=Link()))
    with pytest.raises(NonUniqueAliasError):
        await link_service._alias_unique_or_raise("short")


@pytest.mark.anyio
async def test_short_code_unique_check(link_service, mock_session):
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    assert await link_service._is_short_code_unique("short") is True


@pytest.mark.anyio
async def test_url_unique_check_fail(link_service, mock_session):
    mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=Link()))
    with pytest.raises(UrlAlreadyExists):
        await link_service._url_unique_or_raise("http://test.com")


@pytest.mark.anyio
async def test_create_auto_generate_code_retry(link_service, mock_session):
    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=Link())),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]
    with patch.object(link_service, '_generate_short_code', side_effect=["nounique", "short"]):
        link = await link_service.create("http://test.com")
        assert link.short_code == "short"

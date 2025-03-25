import pytest
from unittest.mock import AsyncMock, patch
from src.links.utils import (
    search_cache_key_builder,
    get_link_cache_key_builder,
    get_all_links_key_builder,
    invalidate_cache
)


def test_search_cache_key_builder_with_direct_original_url():
    def test_func(): pass

    result = search_cache_key_builder(
        test_func,
        namespace="test",
        original_url="https://test.com"
    )

    expected = f"{test_func.__module__}:{test_func.__name__}:https://test.com"
    assert result == expected


def test_search_cache_key_builder_with_kwargs_original_url():
    def test_func(): pass

    result = search_cache_key_builder(
        test_func,
        namespace="test",
        kwargs={"original_url": "https://test.com"}
    )

    expected = f"{test_func.__module__}:{test_func.__name__}:https://test.com"
    assert result == expected


def test_get_link_cache_key_builder_with_direct_short_code():
    def test_func(): pass

    result = get_link_cache_key_builder(
        test_func,
        namespace="test",
        short_code="short"
    )

    expected = f"{test_func.__module__}:{test_func.__name__}:short"
    assert result == expected


def test_get_link_cache_key_builder_with_kwargs_short_code():
    def test_func(): pass

    result = get_link_cache_key_builder(
        test_func,
        namespace="test",
        kwargs={"short_code": "short"}
    )

    expected = f"{test_func.__module__}:{test_func.__name__}:short"
    assert result == expected


def test_get_all_links_key_builder():
    def test_func(): pass

    result = get_all_links_key_builder(
        test_func,
        namespace="test"
    )

    expected = f"{test_func.__module__}:{test_func.__name__}"
    assert result == expected


@pytest.mark.anyio
async def test_invalidate_cache_no_params():
    with patch('src.links.utils.FastAPICache') as mock_fastapi_cache:
        await invalidate_cache()
        mock_fastapi_cache.get_backend.assert_not_called()


@pytest.mark.anyio
async def test_invalidate_cache_with_short_code():
    class MockRouterModule:
        @staticmethod
        def redirect_link(): pass

        @staticmethod
        def link_stats(): pass

        @staticmethod
        def search_link_by_original_url(): pass

    mock_router = MockRouterModule()
    mock_backend = AsyncMock()

    with patch('src.links.utils.FastAPICache') as mock_fastapi_cache, \
            patch('src.links.utils.get_link_cache_key_builder') as mock_key_builder, \
            patch.dict('sys.modules', {'src.links.router': mock_router}):
        mock_fastapi_cache.get_backend.return_value = mock_backend
        mock_key_builder.side_effect = ["redirect_key", "stats_key"]

        await invalidate_cache(short_code="abc123")

        mock_fastapi_cache.get_backend.assert_called_once()
        assert mock_key_builder.call_count == 2
        assert mock_backend.clear.call_count == 2
        mock_backend.clear.assert_any_call(key="redirect_key", namespace="")
        mock_backend.clear.assert_any_call(key="stats_key", namespace="")


@pytest.mark.anyio
async def test_invalidate_cache_with_original_url():
    class MockRouterModule:
        @staticmethod
        def redirect_link(): pass

        @staticmethod
        def link_stats(): pass

        @staticmethod
        def search_link_by_original_url(): pass

    mock_router = MockRouterModule()
    mock_backend = AsyncMock()

    with patch('src.links.utils.FastAPICache') as mock_fastapi_cache, \
            patch('src.links.utils.search_cache_key_builder') as mock_key_builder, \
            patch.dict('sys.modules', {'src.links.router': mock_router}):
        mock_fastapi_cache.get_backend.return_value = mock_backend
        mock_key_builder.return_value = "search_key"

        await invalidate_cache(original_url="https://test.com")

        mock_fastapi_cache.get_backend.assert_called_once()
        mock_key_builder.assert_called_once()
        mock_backend.clear.assert_called_once_with("search_key")


@pytest.mark.anyio
async def test_invalidate_cache_with_both_params():
    class MockRouterModule:
        @staticmethod
        def redirect_link(): pass

        @staticmethod
        def link_stats(): pass

        @staticmethod
        def search_link_by_original_url(): pass

    mock_router = MockRouterModule()
    mock_backend = AsyncMock()
    with patch('src.links.utils.FastAPICache') as mock_fastapi_cache, \
            patch('src.links.utils.get_link_cache_key_builder') as mock_link_key_builder, \
            patch('src.links.utils.search_cache_key_builder') as mock_search_key_builder, \
            patch.dict('sys.modules', {'src.links.router': mock_router}):
        mock_fastapi_cache.get_backend.return_value = mock_backend
        mock_link_key_builder.side_effect = ["redirect_key", "stats_key"]
        mock_search_key_builder.return_value = "search_key"

        await invalidate_cache(
            short_code="short",
            original_url="https://test.com"
        )
        mock_fastapi_cache.get_backend.assert_called_once()
        assert mock_link_key_builder.call_count == 2
        mock_search_key_builder.assert_called_once()
        assert mock_backend.clear.call_count == 3
        mock_backend.clear.assert_any_call(key="redirect_key", namespace="")
        mock_backend.clear.assert_any_call(key="stats_key", namespace="")
        mock_backend.clear.assert_any_call("search_key")

from fastapi_cache import FastAPICache


def search_cache_key_builder(
    func,
    namespace: str = "",
    original_url: str = None,
    *args,
    **kwargs
) -> str:
    if not original_url:
        original_url = kwargs.get("kwargs", {}).get("original_url")
    return f"{func.__module__}:{func.__name__}:{original_url}"


def get_link_cache_key_builder(
    func,
    namespace: str = "",
    short_code: str = None,
    *args,
    **kwargs
) -> str:
    if not short_code:
        short_code = kwargs.get("kwargs", {}).get("short_code")
    return f"{func.__module__}:{func.__name__}:{short_code}"


def get_all_links_key_builder(
    func,
    namespace: str = "",
    *args,
    **kwargs
) -> str:
    return f"{func.__module__}:{func.__name__}"


async def invalidate_cache(short_code: str = None, original_url: str = None):
    if short_code is None and original_url is None:
        return

    backend = FastAPICache.get_backend()

    if short_code:
        from src.links.router import redirect_link
        redirect_key = get_link_cache_key_builder(
            func=redirect_link,
            short_code=short_code
        )
        from src.links.router import link_stats
        stats_key = get_link_cache_key_builder(
            func=link_stats,
            short_code=short_code
        )

        await backend.clear(key=redirect_key, namespace="")
        await backend.clear(key=stats_key, namespace="")

    if original_url:
        from src.links.router import search_link_by_original_url
        search_key = search_cache_key_builder(
            func=search_link_by_original_url,
            original_url=original_url
        )
        await backend.clear(search_key)
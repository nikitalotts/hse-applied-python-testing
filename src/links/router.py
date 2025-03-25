import csv
import time
from io import StringIO
from typing import Union
from fastapi import APIRouter, Request, Depends, Query, BackgroundTasks
from fastapi.responses import Response
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from src.auth.users import get_current_user_or_none, get_current_user, User
from src.database import get_async_session
from src.links.dependencies import get_link_service
from src.links.schemes import CreateLinkRequest, ShortenLinkResponse, UpdateLinkResponse, UpdateLinkRequest, \
    StatsLinkResponse, GetLinkResponse, GetAllLinksResponse, GetLinkShortResponse
from src.links.service import LinkService
from src.links.utils import search_cache_key_builder, get_link_cache_key_builder, get_all_links_key_builder
from src.tasks.tasks import clear_outdated_links_task

router = APIRouter(
    prefix="/links",
    tags=["links"]
)


@router.post("/shorten", response_model=ShortenLinkResponse, status_code=status.HTTP_201_CREATED)
async def shorten_link(
        request: Request,
        model: CreateLinkRequest,
        user: User = Depends(get_current_user_or_none),
        link_service: LinkService = Depends(get_link_service)
) -> ShortenLinkResponse:
    link = await link_service.create(
        long_url=model.original_url,
        custom_alias=model.custom_alias,
        expires_at=model.expires_at,
        user=user
    )

    return ShortenLinkResponse(
        link=f"{str(request.base_url).rstrip('/')}/links/{link.short_code}"
    )


@router.get("/search", response_model=GetLinkResponse, status_code=status.HTTP_200_OK)
@cache(expire=10, key_builder=search_cache_key_builder)
async def search_link_by_original_url(
    request: Request,
    original_url: str = Query(),
    link_service: LinkService = Depends(get_link_service)
) -> GetLinkResponse:
    link = await link_service.find_by_long_url(original_url)

    return GetLinkResponse(
        original_url=link.long_url,
        short_url=f"{str(request.base_url).rstrip('/')}/links/{link.short_code}",
        expires_at=link.expires_at,
        created_at=link.created_at
    )


@router.get("/all", response_model=GetAllLinksResponse, status_code=status.HTTP_200_OK)
# раз в минуту обновляем кэш
@cache(expire=60, key_builder=get_all_links_key_builder)
async def get_all_links(
        request: Request,
        user: User = Depends(get_current_user),
        link_service: LinkService = Depends(get_link_service)
) -> GetAllLinksResponse:
    links = await link_service.get_all_redirect_links()

    return GetAllLinksResponse(
        links=[
            GetLinkShortResponse(
                original_url=link.long_url,
                short_url=f"{str(request.base_url).rstrip('/')}/links/{link.short_code}"
            ) for link in links
        ]
    )


@router.get("/my-statistics", response_class=StreamingResponse)
async def get_user_statistics(
        request: Request,
        user: User = Depends(get_current_user),
        link_service: LinkService = Depends(get_link_service)
):
    links = await link_service.get_links_by_author(user.id)

    csv_data = StringIO()
    writer = csv.writer(csv_data)

    writer.writerow([
        "Short URL", "Original URL", "Created At",
        "Expires At", "Redirects", "Last Used"
    ])

    for link in links:
        writer.writerow([
            f"{str(request.base_url).rstrip('/')}/links/{link.short_code}",
            link.long_url,
            link.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            link.expires_at.strftime("%Y-%m-%d %H:%M:%S") if link.expires_at else "N/A",
            link.redirect_counter,
            link.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if link.last_used_at else "Never"
        ])

    csv_data.seek(0)
    return StreamingResponse(
        iter([csv_data.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=statistics.csv"
        }
    )


@router.get("/{short_code}")
# просто так навесить кэш не получится, так как тогда не будет обновляться счетчик ссылок
# @cache(expire=3600, key_builder=get_link_cache_key_builder)
async def redirect_link(
    short_code: str,
    background_tasks: BackgroundTasks,
    link_service: LinkService = Depends(get_link_service),
):
    backend = FastAPICache.get_backend()
    cache_key = get_link_cache_key_builder(func=redirect_link, short_code=short_code)

    cached_url = await backend.get(cache_key)

    if cached_url:
        cached_url = cached_url.decode("utf-8")
        background_tasks.add_task(link_service.increment_counter, short_code)
        return RedirectResponse(url=cached_url, status_code=302)
    else:
        link = await link_service.get(short_code)
        await backend.set(cache_key, link.long_url, expire=5*60)
        background_tasks.add_task(link_service.increment_counter, short_code)
        return RedirectResponse(url=link.long_url, status_code=302)


@router.delete("/{short_code}", response_class=Response, status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
        short_code: str,
        user: User = Depends(get_current_user),
        link_service: LinkService = Depends(get_link_service)
) -> Response:

    await link_service.delete(
        short_code=short_code,
        user=user
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{short_code}", response_model=UpdateLinkResponse, status_code=status.HTTP_202_ACCEPTED)
async def update_link(
        request: Request,
        short_code: str,
        model: UpdateLinkRequest,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
) -> UpdateLinkResponse:
    link_service = LinkService(session)

    link = await link_service.update(
        short_code=short_code,
        user=user,
        model=model
    )

    return UpdateLinkResponse(
        original_url=link.long_url,
        short_url=f"{str(request.base_url).rstrip('/')}/links/{link.short_code}",
        expires_at=link.expires_at
    )


@router.get("/{short_code}/stats", response_model=StatsLinkResponse, status_code=status.HTTP_200_OK)
@cache(expire=5, key_builder=get_link_cache_key_builder)
async def link_stats(
        short_code: str,
        link_service: LinkService = Depends(get_link_service)
) -> Union[Response, StatsLinkResponse]:

    link = await link_service.get_stats(
        short_code=short_code
    )

    return StatsLinkResponse(
        original_url=link.long_url,
        creation_datetime=link.created_at.strftime("%m/%d/%Y, %H:%M:%S"),
        redirect_amount=link.redirect_counter,
        last_used_datetime=link.last_used_at.strftime("%m/%d/%Y, %H:%M:%S") if link.last_used_at else None
    )


# current_active_user = fastapi_users.current_user(active=True)


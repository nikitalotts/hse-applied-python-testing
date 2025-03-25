import hashlib
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import delete, select, and_, or_

from src.auth.models import User
from src.config import Settings
from src.database import AsyncSession
from src.links.exceptions import NonUniqueAliasError, AliasLengthError, UrlAlreadyExists, LinkNotFoundError, \
    NonUniqueShortCodeError, PermissionDenied
from src.links.models import Link
from src.links.schemes import UpdateLinkRequest
from src.links.utils import invalidate_cache

settings = Settings()


class LinkService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_expired_filter(self):
        return or_(
            Link.expires_at.is_(None),
            and_(
                Link.expires_at.isnot(None),
                Link.expires_at > datetime.utcnow()
            )
        )

    async def find_by_long_url(self, long_url: str) -> Optional[Link]:
        url_to_search = [long_url.strip()]
        if not long_url.startswith(('http://', 'https://')):
            url_to_search.append('https://' + long_url.strip())
            url_to_search.append('http://' + long_url.strip())
        link = (await self.session.execute(
            select(Link).filter(
                Link.long_url.in_(url_to_search)
            )
        )).scalar_one_or_none()
        if not link:
            raise LinkNotFoundError()
        return link


    async def get(self, short_code: str) -> Optional[Link]:
        link = await self._get_link_by_short_code(short_code)

        if not link:
            raise LinkNotFoundError()

        return link

    async def get_stats(self, short_code: str) -> Optional[Link]:
        link = await self._get_link_by_short_code(short_code)
        if not link:
            raise LinkNotFoundError()
        return link

    async def create(
            self,
            long_url: str,
            custom_alias: Optional[str] = None,
            expires_at: Optional[datetime] = None,
            user: Optional[User] = None
    ) -> Link:

        long_url = long_url.strip() if long_url else None
        custom_alias = custom_alias.strip() if custom_alias else None

        await self._url_unique_or_raise(long_url)

        if custom_alias:
            await self._alias_unique_or_raise(custom_alias)
            short_code = custom_alias
        else:
            short_code = await self._generate_short_code(long_url)
            short_code_is_unique = await self._is_short_code_unique(short_code)
            if not short_code_is_unique:
                attempts = Settings().CODE_GENERATION_ATTEMPTS
                secret = Settings().CODE_GENERATION_SECRET
                for i in range(attempts):
                    short_code = await self._generate_short_code(short_code + secret)
                    short_code_is_unique = await self._is_short_code_unique(short_code)
                    if short_code_is_unique:
                        break
            # нужно на будущее, на тот случай, если все варианты закончатся,
            # чтобы по логам можно было увидеть, что такая ошибка часто падает
            # и что то нужно делать
            if not short_code_is_unique:
                raise ValueError("Cannot create short link")

        link = Link(
            long_url=long_url,
            short_code=short_code,
            expires_at=expires_at.replace(tzinfo=None) if expires_at else None
                if expires_at else None,
            author_id=user.id if user else None
        )

        try:
            self.session.add(link)
            await self.session.commit()
        except Exception as ex:
            await self.session.rollback()
            raise ex

        return link

    async def delete(
            self,
            short_code: str,
            user: User = None
    ) -> Link:

        link = await self._get_link_by_short_code(short_code)

        if not link:
            raise LinkNotFoundError()

        if link.author_id != user.id:
            raise PermissionDenied()

        original_url=link.long_url

        try:
            await self.session.execute(
                delete(Link).where(Link.short_code == short_code)
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()

        await invalidate_cache(short_code=link.short_code, original_url=original_url)

        return link

    async def update(
            self,
            short_code: str,
            user: User,
            model: UpdateLinkRequest
    ) -> Link:
        link = await self._get_link_by_short_code(short_code)

        if not link:
            raise LinkNotFoundError()

        if link.author_id != user.id:
            raise PermissionDenied()

        if link.long_url != model.original_url:
            await self._url_unique_or_raise(model.original_url)
            link.long_url = model.original_url

        # if model.custom_alias:
        #     if link.short_code != model.custom_alias:
        #         await self._short_code_unique_or_raise(model.custom_alias)
        #         link.short_code = model.custom_alias

        if link.expires_at != model.expires_at:
            link.expires_at = model.expires_at.replace(tzinfo=None) if model.expires_at else None

        original_url = link.long_url

        try:
            await self.session.commit()
            await self.session.refresh(link)
            await invalidate_cache(short_code=short_code, original_url=original_url)
            return link
        except Exception as ex:
            await self.session.rollback()
            raise ex

    async def get_all_redirect_links(self) -> List[Link]:
        # result = (await self.session.execute(
        #     select(Link).filter(
        #       self._get_expired_filter()
        #     ))).scalars().all()
        result = (await self.session.execute(
            select(Link))).scalars().all()
        return [row for row in result]

    async def get_links_by_author(self, user_id: int) -> List[Link]:
        result = (await self.session.execute(
            select(Link).filter(
                (Link.author_id == user_id) # & self._get_expired_filter()
            ).order_by(Link.created_at.desc())
        )).scalars().all()
        return [row for row in result]

    async def _get_link_by_short_code(self, short_code: str) -> Optional[Link]:
        return (await self.session.execute(
            select(Link).filter(
                (Link.short_code == short_code.strip())
            )
        )).scalar_one_or_none()

    async def increment_counter(self, short_code: str) -> None:
        link = await self._get_link_by_short_code(short_code)
        if link:
            link.redirect_counter += 1
            link.last_used_at = datetime.utcnow().replace(second=0, microsecond=0)
            await self.session.commit()

    async def _generate_short_code(self, long_url: str) -> str:
        # генерируем хэш и берем первые N символом
        # всего вариантов 62^N ([a-z] + [A-Z] + [0-9])
        hash_object = hashlib.sha1(long_url.encode())
        return hash_object.hexdigest()[:settings.SHORT_CODE_LENGTH]

    async def _alias_unique_or_raise(self, alias: str) -> None:
        if not await self._is_short_code_unique(alias):
            raise NonUniqueAliasError(alias)
        if len(alias) > 16 or len(alias) < 4:
            raise AliasLengthError(alias)

    async def _is_short_code_unique(self, short_code: str) -> None:
        # query = select(Link).filter(
        #     and_(
        #         Link.short_code == short_code,
        #         self._get_expired_filter()
        #     )
        # )
        query = select(Link).filter(
            Link.short_code == short_code
        )
        result = (await self.session.execute(query)).scalar_one_or_none()
        return result is None

    async def _short_code_unique_or_raise(self, short_code: str) -> None:
        if not await self._is_short_code_unique(short_code):
            raise NonUniqueShortCodeError(short_code)

    async def _url_unique_or_raise(self, url: str) -> None:
        # query = select(Link).where(
        #     and_(
        #         Link.long_url == url.strip(),
        #         self._get_expired_filter()
        #     )
        # )
        query = select(Link).where(
            Link.long_url == url.strip()
        )
        f = datetime.utcnow()
        result = (await self.session.execute(query)).scalar_one_or_none()
        if result is not None:
            raise UrlAlreadyExists(url)

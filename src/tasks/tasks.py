import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from src.config import Settings
from src.database import sync_session_maker
from src.links.models import Link
from src.links.utils import invalidate_cache
from src.tasks.app import app

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@app.task(ignore_result=True, acks_late=True)
def clear_outdated_links_task():
    ttl_limit = datetime.utcnow().replace(tzinfo=None) - timedelta(days=Settings().LINK_TTL_IN_DAYS)
    with sync_session_maker() as session:
        # print(Link.updated_at + timedelta(days=Settings().LINK_TTL_IN_DAYS),
        #       datetime.utcnow().replace(tzinfo=None),
        #       Link.updated_at + timedelta(days=Settings().LINK_TTL_IN_DAYS) < datetime.utcnow().replace(tzinfo=None))
        stmt = session.execute(
            select(Link).filter(
                # если нет срока истечения ссылки
                Link.expires_at.is_(None) & (
                    # то удаляем ее если с момента создания/обновленияя ссылки прошло более N дней
                    (
                            Link.updated_at + timedelta(days=Settings().LINK_TTL_IN_DAYS)
                                < datetime.utcnow().replace(tzinfo=None)
                    )
                    # и ее вообще не использовали, или с момента последнего использования прошло N дней
                    & (Link.last_used_at.is_(None) | (Link.last_used_at < ttl_limit))
                )
                # или если есть срок истечения ссылки и он прошел
                | (Link.expires_at.isnot(None) & (Link.expires_at < datetime.utcnow().replace(tzinfo=None)))
            )
        )

        outdated_links = stmt.scalars().all()

        logger.info(f"outdated_links len == {len(outdated_links)}")

        if outdated_links:
            for link in outdated_links:
                logger.info(f"Deleting link {link.short_code}")
                session.delete(link)
                loop = asyncio.get_event_loop()
                loop.create_task(invalidate_cache(short_code=link.short_code, original_url=link.long_url))

            session.commit()

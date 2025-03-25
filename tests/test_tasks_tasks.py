import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call
from src.links.models import Link
from src.tasks.tasks import clear_outdated_links_task


@pytest.fixture
def mock_settings(mocker):
    mock = mocker.patch('src.tasks.tasks.Settings')
    mock.return_value.LINK_TTL_IN_DAYS = 7
    return mock


@pytest.fixture
def mock_session(mocker):
    session = MagicMock()
    mocker.patch(
        'src.tasks.tasks.sync_session_maker',
        return_value=MagicMock(__enter__=MagicMock(return_value=session)))
    return session


@pytest.fixture
def mock_loop(mocker):
    loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=loop)
    return loop


def test_no_links_to_delete(mock_settings, mock_session, mock_loop):
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    clear_outdated_links_task()
    mock_session.delete.assert_not_called()
    mock_session.commit.assert_not_called()


def test_multiple_links_deletion_and_cache_invalidation(mock_settings, mock_session, mock_loop):
    old_updated = datetime.utcnow() - timedelta(days=8)
    link1 = Link(id=6, short_code='short1', long_url='http://test.com',
                 expires_at=None, updated_at=old_updated, last_used_at=None)
    link2 = Link(id=7, short_code='short2', long_url='http://test.com',
                 expires_at=datetime.utcnow() - timedelta(days=1), updated_at=datetime.utcnow())
    mock_session.execute.return_value.scalars.return_value.all.return_value = [link1, link2]
    clear_outdated_links_task()
    assert mock_session.delete.call_count == 2
    mock_session.delete.assert_has_calls([call(link1), call(link2)], any_order=True)
    mock_session.commit.assert_called_once()
    assert mock_loop.create_task.call_count == 2


def test_logging(mock_settings, mock_session, mock_loop, mocker):
    mock_logger = mocker.patch('src.tasks.tasks.logger')
    link = Link(id=8, short_code='short', long_url='http://test.com',
                expires_at=datetime.utcnow() - timedelta(days=1))
    mock_session.execute.return_value.scalars.return_value.all.return_value = [link]
    clear_outdated_links_task()
    mock_logger.info.assert_any_call("outdated_links len == 1")
    mock_logger.info.assert_any_call("Deleting link short")

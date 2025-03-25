import uuid
import pytest
from src.main import app
from fastapi import status
from sqlalchemy import StaticPool
from fastapi_cache import FastAPICache
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from src.database import DbBase, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def test_db():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(DbBase.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(DbBase.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(test_db):
    async_session = async_sessionmaker(
        test_db, expire_on_commit=False, class_=AsyncSession
    )
    yield async_session


@pytest.fixture(scope="function")
async def client(async_session):
    mock_redis = AsyncMock()
    mock_cache_backend = AsyncMock()
    mock_cache_backend.get.return_value = None
    mock_cache_backend.set.return_value = None
    mock_cache_backend.delete.return_value = None
    with patch('src.auth.backend.redis', mock_redis), \
         patch('src.links.utils.FastAPICache.get_backend', return_value=mock_cache_backend):
        FastAPICache.init(backend=mock_cache_backend, prefix="test-cache")

        async def override_get_async_session():
            async with async_session() as session:
                yield session

        app.dependency_overrides[get_async_session] = override_get_async_session
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False
        ) as client:
            yield client
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(client):
    user_data = {
        "email": "test@test.com",
        "password": "password123"
    }
    response = await client.post(
        "/auth/register",
        json=user_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    return user_data


@pytest.fixture(scope="function")
async def auth_cookies(client, test_user):
    response = await client.post(
        "/auth/jwt/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    return {key: value for key, value in response.cookies.items()}


def _get_link_data():
    return {
        "original_url": f"http://google.com/search?q={uuid.uuid4()}",
        "custom_alias": f"{uuid.uuid4().hex[:16]}",
        "expires_at": "2026-01-01T00:00:00"
    }


@pytest.mark.asyncio
async def test_health(client, auth_cookies):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_register_new_user(client):
    user_data = {
        "email": "test2@test.com",
        "password": "password123"
    }
    response = await client.post(
        "/auth/register",
        json=user_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["email"] == user_data["email"]
    assert "id" in response.json()


@pytest.mark.asyncio
async def test_register_existing_user(client, test_user):
    response = await client.post(
        "/auth/register",
        json={
            "email": test_user["email"],
            "password": "anotherpassword"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'REGISTER_USER_ALREADY_EXISTS' in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    response = await client.post(
        "/auth/jwt/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert "su" in response.cookies.keys()


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    response = await client.post(
        "/auth/jwt/login",
        data={
            "username": test_user["email"],
            "password": "wrongpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "LOGIN_BAD_CREDENTIALS" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await client.post(
        "/auth/jwt/login",
        data={
            "username": "notexist@user.com",
            "password": "password123"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "LOGIN_BAD_CREDENTIALS" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_invalid_format(client):
    response = await client.post(
        "/auth/jwt/login",
        # json а не application/x-www-form-urlencoded
        json={
            "username": "test@test.com",
            "password": "password"
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_logout(client, auth_cookies):
    protected_response = await client.get("/links/all", cookies=auth_cookies)
    assert protected_response.status_code == status.HTTP_200_OK
    logout_response = await client.post("/auth/jwt/logout", cookies=auth_cookies)
    assert logout_response.status_code == status.HTTP_204_NO_CONTENT
    protected_response_after_logout = await client.get("/links/all")
    assert protected_response_after_logout.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_short_link(client, auth_cookies):
    response = await client.post(
        "/links/shorten",
        json=_get_link_data(),
        cookies=auth_cookies
    )
    assert response.status_code == 201
    assert "links/" in response.json()["link"]


@pytest.mark.asyncio
async def test_redirect_link(client, auth_cookies):
    data = _get_link_data()
    original_url = data['original_url']
    create_resp = await client.post(
        "/links/shorten",
        json=data,
        cookies=auth_cookies
    )
    short_code = create_resp.json()["link"].split("/")[-1]
    response = await client.get(f"/links/{short_code}", cookies=auth_cookies)
    assert response.status_code == 302
    assert response.headers["location"] == original_url


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    response = await client.get("/links/my-statistics")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_link(client, auth_cookies):
    data = _get_link_data()
    create_resp = await client.post(
        "/links/shorten",
        json=data,
        cookies=auth_cookies
    )
    assert create_resp.status_code == 201
    create_data = create_resp.json()
    short_code = create_data["link"].split("/")[-1]
    data = _get_link_data()
    new_url = data['original_url']
    update_resp = await client.put(
        f"/links/{short_code}",
        json=data,
        cookies=auth_cookies
    )
    assert update_resp.status_code == 202
    assert new_url == update_resp.json()["original_url"]


@pytest.mark.asyncio
async def test_update_link_unauthorized(client, auth_cookies):
    data = _get_link_data()
    create_resp = await client.post(
        "/links/shorten", json=data,
        cookies=auth_cookies
    )
    short_code = create_resp.json()["link"].split("/")[-1]
    update_resp = await client.put(f"/links/{short_code}", json=data)
    assert update_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_delete_link(client, auth_cookies):
    data = _get_link_data()
    create_resp = await client.post("/links/shorten", json=data, cookies=auth_cookies)
    short_code = create_resp.json()["link"].split("/")[-1]
    delete_resp = await client.delete(f"/links/{short_code}", cookies=auth_cookies)
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT
    get_resp = await client.get(f"/links/{short_code}", cookies=auth_cookies)
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND
    delete_resp = await client.delete(f"/links/invalid_code", cookies=auth_cookies)
    assert delete_resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_link_unauthorized(client, auth_cookies):
    data = _get_link_data()
    create_resp = await client.post(
        "/links/shorten", json=data,
        cookies=auth_cookies
    )
    short_code = create_resp.json()["link"].split("/")[-1]
    delete_resp = await client.delete(f"/links/{short_code}")
    assert delete_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_search_link(client, auth_cookies):
    data = _get_link_data()
    original_url = data["original_url"]
    create_resp = await client.post("/links/shorten", json=data, cookies=auth_cookies)
    assert create_resp.status_code == status.HTTP_201_CREATED
    search_resp = await client.get(f"/links/search?original_url={original_url}", cookies=auth_cookies)
    assert search_resp.status_code == status.HTTP_200_OK
    assert search_resp.json()["original_url"] == original_url
    assert search_resp.json()["short_url"] == create_resp.json()["link"]


@pytest.mark.asyncio
async def test_get_all_links(client, auth_cookies):
    data1 = _get_link_data()
    data2 = _get_link_data()
    await client.post("/links/shorten", json=data1, cookies=auth_cookies)
    await client.post("/links/shorten", json=data2, cookies=auth_cookies)
    get_all_resp = await client.get("/links/all", cookies=auth_cookies)
    assert get_all_resp.status_code == status.HTTP_200_OK
    links = get_all_resp.json()["links"]
    assert len(links) == 2


@pytest.mark.asyncio
async def test_user_statistics_csv(client, auth_cookies):
    data = _get_link_data()
    create_resp = await client.post("/links/shorten", json=data, cookies=auth_cookies)
    short_code = create_resp.json()["link"].split("/")[-1]
    stats_resp = await client.get("/links/my-statistics", cookies=auth_cookies)
    assert stats_resp.status_code == status.HTTP_200_OK
    content = stats_resp.content.decode()
    assert "Short URL,Original URL,Created At,Expires At,Redirects,Last Used" in content
    assert short_code in content
    assert data["original_url"] in content


@pytest.mark.asyncio
async def test_link_stats(client, auth_cookies):
    data = _get_link_data()
    create_resp = await client.post("/links/shorten", json=data, cookies=auth_cookies)
    short_code = create_resp.json()["link"].split("/")[-1]
    stats_resp = await client.get(f"/links/{short_code}/stats", cookies=auth_cookies)
    assert stats_resp.status_code == status.HTTP_200_OK
    assert stats_resp.json()["redirect_amount"] == 0
    await client.get(f"/links/{short_code}", cookies=auth_cookies)
    stats_resp = await client.get(f"/links/{short_code}/stats", cookies=auth_cookies)
    assert stats_resp.json()["redirect_amount"] == 1


@pytest.mark.asyncio
async def test_create_link_invalid_url(client, auth_cookies):
    invalid_data = _get_link_data()
    invalid_data["original_url"] = "invalidurl"
    response = await client.post("/links/shorten", json=invalid_data, cookies=auth_cookies)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Wrong URL" in response.text


@pytest.mark.asyncio
async def test_create_link_invalid_alias_length(client, auth_cookies):
    invalid_data = _get_link_data()
    invalid_data["custom_alias"] = "a" * 3
    response = await client.post("/links/shorten", json=invalid_data, cookies=auth_cookies)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    invalid_data["custom_alias"] = "a" * 100
    response = await client.post("/links/shorten", json=invalid_data, cookies=auth_cookies)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_link_duplicate_custom_alias(client, auth_cookies):
    data = _get_link_data()
    data["custom_alias"] = "testalias"
    await client.post("/links/shorten", json=data, cookies=auth_cookies)
    data = _get_link_data()
    data["custom_alias"] = "testalias"
    response = await client.post("/links/shorten", json=data, cookies=auth_cookies)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_link_duplicate_original_url(client, auth_cookies):
    data = _get_link_data()
    original_url = data["original_url"]
    await client.post("/links/shorten", json=data, cookies=auth_cookies)
    data = _get_link_data()
    data["original_url"] = original_url
    response = await client.post("/links/shorten", json=data, cookies=auth_cookies)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already has been shorten" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_link_without_custom_alias(client, auth_cookies):
    data = _get_link_data()
    data["custom_alias"] = None
    response = await client.post("/links/shorten", json=data, cookies=auth_cookies)
    assert response.status_code == status.HTTP_201_CREATED
    assert "links/" in response.json()["link"]


@pytest.mark.asyncio
async def test_update_link_invalid_url(client, auth_cookies):
    create_resp = await client.post("/links/shorten", json=_get_link_data(), cookies=auth_cookies)
    short_code = create_resp.json()["link"].split("/")[-1]
    invalid_data = _get_link_data()
    invalid_data["original_url"] = "invalidurl"
    response = await client.put(f"/links/{short_code}", json=invalid_data, cookies=auth_cookies)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_update_link_wrong_expire_at(client, auth_cookies):
    create_resp = await client.post("/links/shorten", json=_get_link_data(), cookies=auth_cookies)
    short_code = create_resp.json()["link"].split("/")[-1]
    invalid_data = _get_link_data()
    invalid_data["expires_at"] = "2020-01-01T00:00:00"
    response = await client.put(f"/links/{short_code}", json=invalid_data, cookies=auth_cookies)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "future" in response.text


@pytest.mark.asyncio
async def test_update_non_existent_link(client, auth_cookies):
    non_existent_code = "noexist"
    data = _get_link_data()
    response = await client.put(
        f"/links/{non_existent_code}",
        json=data,
        cookies=auth_cookies
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_stats_no_exist_link(client, auth_cookies):
    response = await client.get("/links/notexist/stats", cookies=auth_cookies)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_all_links_unauthorized(client):
    response = await client.get("/links/all")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_search_link_not_found(client, auth_cookies):
    response = await client.get("/links/search?original_url=http://notexist.com", cookies=auth_cookies)
    assert response.status_code == status.HTTP_404_NOT_FOUND

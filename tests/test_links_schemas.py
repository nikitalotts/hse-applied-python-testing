import pytest
from pydantic import ValidationError
from datetime import datetime, timedelta
from src.links.schemes import (
    CreateLinkRequest,
    UpdateLinkRequest,
    DeleteLinkRequest,
    ShortenLinkResponse,
    UpdateLinkResponse,
    StatsLinkResponse,
    GetLinkResponse,
    GetLinkShortResponse,
    GetAllLinksResponse
)


def test_create_link_request_valid():
    valid_data = {
        "original_url": "https://google.com",
        "custom_alias": "google",
        "expires_at": datetime.utcnow() + timedelta(days=1)
    }
    assert CreateLinkRequest(**valid_data)


def test_create_link_request_url_autocorrection():
    data = CreateLinkRequest(
        original_url="google.com",
        expires_at=((datetime.utcnow() + timedelta(days=30))
                    .replace(second=30, microsecond=500, tzinfo=None))
    ).model_dump()
    assert data["original_url"].startswith("http://")


def test_create_link_request_invalid_url():
    with pytest.raises(ValidationError):
        CreateLinkRequest(original_url="invalid_url")


def test_create_link_request_alias_length():
    with pytest.raises(ValidationError):
        CreateLinkRequest(original_url="https://google.com", custom_alias="sho")


def test_create_link_request_past_expiration():
    with pytest.raises(ValidationError):
        CreateLinkRequest(
            original_url="https://google.com",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )


def test_update_link_request_valid():
    valid_data = {
        "original_url": "https://updated.com",
        "expires_at": datetime.utcnow() + timedelta(hours=2)
    }
    assert UpdateLinkRequest(**valid_data)


def test_update_link_request_invalid_url():
    with pytest.raises(ValidationError):
        UpdateLinkRequest(original_url="ftp://invalid.com")


def test_delete_link_request():
    assert DeleteLinkRequest(short_code="test1234")


def test_shorten_link_response():
    response = ShortenLinkResponse(link="http://localhost/abc123")
    assert response.link == "http://localhost/abc123"


def test_update_link_response():
    response = UpdateLinkResponse(
        original_url="https://original.com",
        short_url="http://short.ly/abc123",
        expires_at=datetime.utcnow()
    )
    assert all([response.original_url, response.short_url, response.expires_at])


def test_stats_link_response():
    response = StatsLinkResponse(
        original_url="https://stats.com",
        creation_datetime="2023-01-01T00:00:00",
        redirect_amount=100,
        last_used_datetime="2023-01-02T00:00:00"
    )
    assert response.redirect_amount == 100


def test_get_link_response():
    response = GetLinkResponse(
        original_url="https://get.com",
        short_url="http://short.ly/def456",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    assert response.expires_at > response.created_at


def test_get_all_links_response():
    links = [
        GetLinkShortResponse(
            original_url=f"https://link{i}.com",
            short_url=f"http://short.ly/{i}"
        ) for i in range(3)
    ]
    response = GetAllLinksResponse(links=links)
    assert len(response.links) == 3


def test_expires_at_rounding():
    request = CreateLinkRequest(
        original_url="https://time.com",
        expires_at=((datetime.utcnow() + timedelta(days=30))
                 .replace(second=30, microsecond=500, tzinfo=None))
    )
    assert request.expires_at.second == 0
    assert request.expires_at.microsecond == 0


def test_update_link_request_past_expiration():
    with pytest.raises(ValidationError):
        UpdateLinkRequest(
            original_url="https://google.com",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )

import validators
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator, Field


class CreateLinkRequest(BaseModel):
    original_url: str = Field(example="google.com")
    custom_alias: Optional[str] = Field(default=None, example=None)
    expires_at: Optional[datetime] = Field(
        example=f"{(datetime.utcnow() + timedelta(days=30)).replace(tzinfo=None, microsecond=0)}"
    )

    @field_validator('original_url')
    def validate_long_url(cls, value: str) -> str:
        if not value.startswith(('http://', 'https://')):
            value = 'http://' + value
        if validators.url(value) is not True:
            raise ValueError("Wrong URL")
        return value

    @field_validator('custom_alias')
    def validate_custom_alias(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and ((len(value) < 4) or len(value) > 16):
            raise ValueError("Alias length must be between 4 and 16 symbols")
        return value

    @field_validator('expires_at')
    def round_to_minute(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None:
            value = value.replace(second=0, microsecond=0)
        if value is not None and value < datetime.utcnow().replace(tzinfo=None):
            raise ValueError("Expires date must be in the future")
        return value


class UpdateLinkRequest(BaseModel):
    original_url: str = Field(example="google.com")
    # custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = Field(
        example=f"{(datetime.utcnow() + timedelta(days=30)).replace(tzinfo=None, microsecond=0)}"
    )

    @field_validator('original_url')
    def validate_long_url(cls, value: Optional[str]) -> Optional[str]:
        if not value.startswith(('http://', 'https://')):
            value = 'http://' + value
        if validators.url(value) is not True:
            raise ValueError("Wrong URL")
        return value

    # @field_validator('custom_alias')
    # def validate_custom_alias(cls, value: Optional[str]) -> Optional[str]:
    #     if value is not None and ((len(value) < 4) or len(value) > 16):
    #         raise ValueError("Alias length must be between 4 and 16 symbols")
    #     return value

    @field_validator('expires_at')
    def round_to_minute(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None:
            value = value.replace(second=0, microsecond=0)
        if value is not None and value < datetime.utcnow().replace(tzinfo=None):
            raise ValueError("Expires date must be in the future")
        return value


class DeleteLinkRequest(BaseModel):
    short_code: Optional[str]


class ShortenLinkResponse(BaseModel):
    link: str


class UpdateLinkResponse(BaseModel):
    original_url: str
    short_url: str
    expires_at: datetime | None = Field(default=None)


class StatsLinkResponse(BaseModel):
    original_url: str
    creation_datetime: str
    redirect_amount: int | None = Field(default=None)
    last_used_datetime: str | None = Field(default=None)


class GetLinkResponse(BaseModel):
    original_url: str
    short_url: str
    created_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)


class GetLinkShortResponse(BaseModel):
    original_url: str
    short_url: str


class GetAllLinksResponse(BaseModel):
    links: list[GetLinkShortResponse]

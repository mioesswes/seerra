from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_chat_id: int = Field(alias="ADMIN_CHAT_ID")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")
    database_url: str = Field(alias="DATABASE_URL")
    bot_owner_has_premium: bool = Field(default=True, alias="BOT_OWNER_HAS_PREMIUM")
    bot_name: str = Field(default="BJOKER", alias="BOT_NAME")
    topup_photo_url: str | None = Field(default=None, alias="TOPUP_PHOTO_URL")
    profile_image_path: Path = Field(default=Path("./profile.jpg"), alias="PROFILE_IMAGE_PATH")
    games_sticker_file_id: str | None = Field(default=None, alias="GAMES_STICKER_FILE_ID")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | list[int] | int) -> list[int]:
        if isinstance(value, int):
            return [value]
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [int(chunk.strip()) for chunk in value.split(",") if chunk.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

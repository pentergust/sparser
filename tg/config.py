"""Общие настройки бота."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    """Базовые настройки бота.

    загружаются один раз и не изменяются.
    """

    bot_token: str
    bot_admin: int
    db_url: str
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")

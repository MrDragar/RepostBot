from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids: List[int] = Field(alias="ADMIN_IDS", default_factory=list)
    proxy_url: str | None = Field(alias="PROXY_URL", default=None)
    messages_per_second: int = Field(alias="MESSAGES_PER_SECOND", default=25)
    temp_dir: str = Field(alias="TEMP_DIR", default="./temp")
    source_chat_id: str = Field(alias="SOURCE_CHAT_ID")


settings = Settings()

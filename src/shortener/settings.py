from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _ROOT / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Postgres settings.
    # NOTE: historically this project reused `HOST`/`PORT` for DB connection,
    # but the Dockerfile also uses them for uvicorn host/port. To avoid the
    # conflict, we support DB_* variables with HOST/PORT as fallback.
    host: str = Field(
        validation_alias=AliasChoices("DB_HOST", "POSTGRES_HOST", "HOST")
    )
    database: str = Field(
        validation_alias=AliasChoices("DB_DATABASE", "DB_NAME", "DATABASE")
    )
    user: str = Field(
        validation_alias=AliasChoices("DB_USER", "DB_USERNAME", "user")
    )
    password: str = Field(
        validation_alias=AliasChoices("DB_PASSWORD", "DB_PASS", "PASSWORD")
    )
    port: int = Field(
        validation_alias=AliasChoices("DB_PORT", "POSTGRES_PORT", "PORT")
    )
    logging_level: str = Field(validation_alias="LOGGING_LEVEL")
    logging_format: str = Field(validation_alias="LOGGING_FORMAT")


@lru_cache
def get_settings() -> Settings:
    return Settings()

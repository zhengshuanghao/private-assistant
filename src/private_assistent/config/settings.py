from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from private_assistent.config.paths import get_config_path, get_working_dir


class Settings(BaseSettings):
    """Runtime settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_prefix="PRIVATE_ASSISTENT_",
        env_file=".env",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    host: str = "127.0.0.1"
    port: int = 8088
    model_provider: str = "local"
    model_name: str = "qwen-local"
    working_dir: Path = Field(default_factory=get_working_dir)
    workspace_dir: Path = Path("data/workspace")
    memory_dir: Path = Path("data/memory")
    sessions_dir: Path = Path("data/sessions")
    config_path: Path = Field(default_factory=get_config_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

import threading
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- MongoDB ---
    MONGO_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI",
    )
    MONGO_DB_NAME: str = Field(
        default="chiefops",
        description="MongoDB database name",
    )

    # --- Redis ---
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URI",
    )

    # --- Citex Integration ---
    CITEX_API_URL: str = Field(
        default="http://localhost:20161",
        description="Base URL for the Citex extraction service",
    )

    # --- AI Adapter ---
    AI_ADAPTER: Literal["openrouter", "cli", "mock"] = Field(
        default="openrouter",
        description="Which AI backend to use: 'openrouter', 'cli', or 'mock'",
    )
    AI_CLI_TOOL: str = Field(
        default="claude",
        description="CLI tool binary name when AI_ADAPTER=cli",
    )
    AI_CLI_TIMEOUT: int = Field(
        default=120,
        description="Timeout in seconds for CLI AI calls",
    )

    # --- OpenRouter ---
    OPENROUTER_API_KEY: str = Field(
        default="",
        description="API key for OpenRouter",
    )
    OPENROUTER_MODEL: str = Field(
        default="anthropic/claude-sonnet-4",
        description="Model identifier on OpenRouter",
    )

    # --- Privacy ---
    PII_REDACTION_ENABLED: bool = Field(
        default=True,
        description="Whether to redact PII from ingested content",
    )

    # --- Logging ---
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application log level",
    )

    # --- Environment ---
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )

    # --- Upload Limits ---
    UPLOAD_MAX_FILE_SIZE_MB: int = Field(
        default=50,
        description="Maximum single file upload size in megabytes",
    )
    UPLOAD_MAX_BATCH_SIZE_MB: int = Field(
        default=200,
        description="Maximum total batch upload size in megabytes",
    )

    @property
    def upload_max_file_size_bytes(self) -> int:
        return self.UPLOAD_MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def upload_max_batch_size_bytes(self) -> int:
        return self.UPLOAD_MAX_BATCH_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


_settings_instance: Settings | None = None
_settings_lock = threading.Lock()


def get_settings() -> Settings:
    """Return the singleton Settings instance (thread-safe)."""
    global _settings_instance
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                _settings_instance = Settings()
    return _settings_instance

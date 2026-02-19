"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "NILE Security"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://nile:nile@localhost:5432/nile"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI APIs
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_model: str = "claude-opus-4-6"

    # Security
    api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_prefix": "NILE_"}


settings = Settings()

"""Settings for support-bot, read from environment variables and .env.

Every value here has a matching line in .env.example.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "support-bot"

    # Model provider. "fake" runs an offline demo model so you can click through the
    # whole app (and run the tests) without an API key.
    llm_provider: str = "anthropic"
    llm_model: str = "claude-opus-5-5"
    llm_temperature: float = 0.2
    llm_effort: str | None = None
    llm_max_tokens: int = 4096
    # Server-side refusal fallback for Claude models that support it: "default" or "off".
    anthropic_refusal_fallback: str = "default"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Conversation state: memory | sqlite | postgres
    checkpointer: str = "postgres"
    database_url: str = "postgresql://app:app@localhost:5432/app"
    sqlite_path: str = "data/checkpoints.sqlite"

    cors_origins: list[str] = ["http://localhost:3000"]
    data_dir: str = "data"
    recursion_limit: int = 50

    # Knowledge bases. The overrides swap in in-process stand-ins for tests.
    vector_store_override: str | None = None
    embeddings_override: str | None = None
    reranker_override: str | None = None
    chroma_path: str = "data/chroma"
    cohere_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

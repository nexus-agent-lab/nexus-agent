from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    LLM_API_KEY: str = "ollama"
    LLM_BASE_URL: str = "http://host.docker.internal:11434/v1"
    LLM_MODEL: str = "qwen2.5:14b"

    # Skill Generation
    SKILL_GEN_PROVIDER: str = "local"
    SKILL_GEN_MODEL: Optional[str] = None
    SKILL_GEN_API_KEY: Optional[str] = None

    # Embeddings
    EMBEDDING_API_KEY: str = "local"
    EMBEDDING_BASE_URL: str = "http://host.docker.internal:9292/v1"
    EMBEDDING_MODEL: str = "bge-small-zh-v1.5"
    EMBEDDING_DIMENSION: int = 512

    # Semantic Routing
    ENABLE_SEMANTIC_ROUTING: bool = True
    ROUTING_TOP_K: int = 5
    ROUTING_THRESHOLD: float = 0.35

    # Voice
    STT_BASE_URL: str = "http://host.docker.internal:9191/v1"
    STT_API_KEY: str = "sk-local-test"

    # Home Assistant
    HOMEASSISTANT_URL: Optional[str] = None
    HOMEASSISTANT_TOKEN: Optional[str] = None

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ALLOWED_USERS: Optional[str] = None
    TELEGRAM_PROXY_URL: Optional[str] = None

    # Feishu (Lark)
    FEISHU_APP_ID: Optional[str] = None
    FEISHU_APP_SECRET: Optional[str] = None
    FEISHU_VERIFICATION_TOKEN: Optional[str] = None

    # Database & Redis
    DATABASE_URL: str = "postgresql+asyncpg://nexus:nexus_password@postgres:5432/nexus_db"
    REDIS_URL: str = "redis://redis:6379/0"

    # Tailscale
    TAILSCALE_AUTH_KEY: Optional[str] = None

    # Environment Reference (for relative paths)
    BASE_DIR: str = "."

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()

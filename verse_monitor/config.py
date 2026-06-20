"""Configuration pydantic-settings pour verse-monitor.

Lit les variables d'environnement depuis le .env partagé avec verse-monitor.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Variables d'environnement du service."""

    # Redis
    REDIS_URL: str = "redis://redis-verse:6379"
    REDIS_PASSWORD: str = ""

    # Qdrant
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "sc_events"

    # Ingestion: API source + embeddings (OpenRouter-compatible)
    WIKI_API_BASE: str = "https://api.star-citizen.wiki/api"
    EMBEDDING_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY: str = ""

    # Discord webhooks (optionnels — si vide, les alertes sont skippées)
    DISCORD_WEBHOOK_CRITICAL: str = ""
    DISCORD_WEBHOOK_HIGH: str = ""
    DISCORD_WEBHOOK_MEDIUM: str = ""

    # Ingestion interval (secondes)
    INGESTION_INTERVAL: int = 86400  # 24h

    # Intervals de polling (secondes)
    POLL_ROADMAP_INTERVAL: int = 300
    POLL_DEVTRACKER_INTERVAL: int = 120
    POLL_COMMLINKS_INTERVAL: int = 300
    POLL_SPECTRUM_INTERVAL: int = 180
    POLL_REDDIT_INTERVAL: int = 180

    # Redis Stream
    STREAM_NAME: str = "sc:events"
    STREAM_MAXLEN: int = 2000
    DEDUP_TTL: int = 86400  # 24h

    # Consumer group
    CONSUMER_GROUP: str = "alert-workers"
    CONSUMER_NAME: str = "worker-1"

    # HTTP
    HTTP_TIMEOUT: int = 30
    HTTP_RETRIES: int = 2
    HTTP_RETRY_BACKOFF: int = 5


settings = Settings()

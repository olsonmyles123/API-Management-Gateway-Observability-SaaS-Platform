import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server Configuration
    PROJECT_NAME: str = "API Management & Observability SaaS"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "info"
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Operational Metadata Database (PostgreSQL / SQLite async)
    DATABASE_URL: str = "sqlite+aiosqlite:///./apigateway.db"

    # Redis Cache, Sliding-Window Rate Limiter & Streams
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_KEY: str = "telemetry:requests"
    REDIS_STREAM_GROUP: str = "telemetry_consumers"
    REDIS_KEY_CACHE_PREFIX: str = "apikey:meta:"
    REDIS_CACHE_TTL_SECONDS: int = 3600  # 1 hour

    # ClickHouse OLAP Configuration
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_DB: str = "default"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_SECURE: bool = False
    CLICKHOUSE_TABLE: str = "api_telemetry"

    # Reverse Proxy Client Pooling
    PROXY_TIMEOUT_SECONDS: float = 30.0
    MAX_KEEPALIVE_CONNECTIONS: int = 100
    MAX_CONNECTIONS: int = 500

    # Background Workers
    TELEMETRY_BATCH_SIZE: int = 100
    TELEMETRY_FLUSH_INTERVAL_MS: int = 500
    ALERT_EVAL_INTERVAL_SECONDS: int = 30

    # JWT Authentication & Cookie Security
    JWT_SECRET_KEY: str = "antigravity-super-secure-jwt-secret-key-prod-9831412"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            if v == "*":
                return ["http://localhost:3000", "http://127.0.0.1:3000"]
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()

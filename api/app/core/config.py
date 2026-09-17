from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tinkertaps API"
    app_version: str = "0.1.0"
    environment: Literal["development",
                         "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "tinkertaps_api"
    db_password: str
    db_name: str = "tinkertaps"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    migration_db_user: str
    migration_db_password: str

    cors_origins: list[str] = Field(default_factory=lambda: [
                                    "http://localhost:4321"])
    cors_allow_credentials: bool = True

    # Clerk (JWT verification via JWKS)
    clerk_issuer: str = ""
    clerk_jwks_url: str = ""
    clerk_audience: str | None = None

    # AWS / Floci
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_internal_endpoint_url: str
    aws_public_endpoint_url: str

    # S3 / object storage
    s3_bucket_name: str = ""
    s3_presign_expiry_seconds: int = 3600

    # SQS Queue
    sqs_queue_url: str
    sqs_queue_name: str

    # Redis job queue
    redis_url: str = "redis://localhost:6379/0"

    # Credits + anonymous tracking
    anonymous_default_credits: int = 3
    registered_default_credits: int = 10
    anon_cookie_name: str = "tt_anon_id"
    anon_cookie_max_age_seconds: int = 60 * 60 * 24 * 365

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
                path=self.db_name,
            )
        )

    @property
    def migration_database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.migration_db_user,
                password=self.migration_db_password,
                host=self.db_host,
                port=self.db_port,
                path=self.db_name,
            )
        )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


# Cache the Settings instance to avoid reloading from environment variables
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

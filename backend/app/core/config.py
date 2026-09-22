
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://rotapay:rotapay@localhost:5434/rotapay"
    redis_url: str = "redis://localhost:6381/0"

    jwt_secret: str = "troque-por-um-segredo-longo-e-aleatorio"
    jwt_expire_minutes: int = 480
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_name: str = "rotapay_token"

    frontend_origin: str = "http://localhost:5173"
    platform_fee_bps: int = 500

    sla_avg_kmh: float = 45.0
    sla_buffer: float = 1.5
    sla_min_hours: int = 72
    sla_max_hours: int = 336

    mp_access_token: str = ""
    mp_webhook_secret: str = ""
    api_public_url: str = "http://localhost:8000"

    environment: str = "development"
    timezone: str = "America/Sao_Paulo"

@lru_cache
def get_settings() -> Settings:
    return Settings()

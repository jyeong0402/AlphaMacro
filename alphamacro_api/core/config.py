"""Application settings and environment configuration."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AlphaMacro API"
    database_url: str = "sqlite:///./alphamacro.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    finbert_model: str = "ProsusAI/finbert"
    finbert_enabled: bool = False
    fred_api_key: str | None = None
    news_api_key: str | None = None
    news_api_url: str = "https://newsapi.org/v2/everything"
    sec_user_agent: str | None = None
    refresh_enabled: bool = False
    refresh_interval_hours: int = 24
    refresh_tickers: str = ""
    refresh_fred_series: str = ""
    refresh_lookback_days: int = 7
    alert_check_interval_seconds: int = 60
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

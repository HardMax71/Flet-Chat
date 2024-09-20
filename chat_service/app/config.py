# /app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    PROJECT_NAME: str = "Chat API"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "A FastAPI-based Chat Application"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_HOST: str
    REDIS_PORT: int
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


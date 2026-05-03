from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import json
import os

class Settings(BaseSettings):
    # Database - set from docker-compose environment or directly
    DB_USER: str = "ocr_user_prod"
    DB_PASS: str = "password"
    DB_HOST: str = "db"
    DB_PORT: str = "5432"
    DB_NAME: str = "ocr_exames"
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_PASS: str = "password"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # External services
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    MAX_PDF_PAGES_FALLBACK: int = 5

    # API Key (opcional - para uso administrativo via CLI)
    MASTER_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "https://app.storge.care"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [i.strip() for i in v.split(",")]
        return v

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def celery_broker(self) -> str:
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        return f"redis://:{self.REDIS_PASS}@redis:6379/0"

    @property
    def celery_backend(self) -> str:
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        return f"redis://:{self.REDIS_PASS}@redis:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()

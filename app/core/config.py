from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional
import json
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env" if os.access(".env", os.R_OK) else None
    )

    # Database - set from docker-compose environment or directly
    DB_USER: str = "ocr_user_prod"
    DB_PASS: str = ""
    DB_HOST: str = "db"
    DB_PORT: str = "5432"
    DB_NAME: str = "ocr_exames"
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_PASS: str = ""
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CACHE_REDIS_URL: Optional[str] = None

    # External services
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    MAX_PDF_PAGES_FALLBACK: int = 5
    AI_PROVIDER_TIMEOUT_SECONDS: int = 60

    # API Key (opcional - para uso administrativo via CLI)
    MASTER_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "https://app.storge.care"]

    # Storage
    OCR_STORAGE_BACKEND: str = "local"
    OCR_STORAGE_BUCKET: str = "ocr-exams"
    OCR_STORAGE_REGION: str = "us-east-1"
    OCR_STORAGE_ENDPOINT: Optional[str] = None
    OCR_STORAGE_ACCESS_KEY: Optional[str] = None
    OCR_STORAGE_SECRET_KEY: Optional[str] = None
    OCR_STORAGE_FORCE_PATH_STYLE: bool = True
    OCR_LOCAL_STORAGE_DIR: str = "storage"
    OCR_RETENTION_DAYS: int = 30

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

    @property
    def cache_redis_url(self) -> str:
        if self.CACHE_REDIS_URL:
            return self.CACHE_REDIS_URL
        return f"redis://:{self.REDIS_PASS}@redis:6379/1"

settings = Settings()

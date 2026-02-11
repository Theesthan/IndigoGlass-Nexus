# =============================================================================
# IndigoGlass Nexus - Application Configuration
# =============================================================================
"""
Centralized configuration using Pydantic Settings.
All configuration is loaded from environment variables.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # -------------------------------------------------------------------------
    # General
    # -------------------------------------------------------------------------
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    SECRET_KEY: str = Field(default="change-me-in-production")
    
    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_WORKERS: int = Field(default=4)
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"])
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # -------------------------------------------------------------------------
    # JWT Authentication
    # -------------------------------------------------------------------------
    JWT_SECRET_KEY: str = Field(default="jwt-secret-change-me")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # -------------------------------------------------------------------------
    # MySQL
    # -------------------------------------------------------------------------
    MYSQL_HOST: str = Field(default="localhost")
    MYSQL_PORT: int = Field(default=3306)
    MYSQL_DATABASE: str = Field(default="indigoglass")
    MYSQL_USER: str = Field(default="indigoglass")
    MYSQL_PASSWORD: str = Field(default="password")
    
    @property
    def MYSQL_URL(self) -> str:
        return (
            f"mysql+asyncmy://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )
    
    @property
    def MYSQL_URL_SYNC(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )
    
    # -------------------------------------------------------------------------
    # MongoDB
    # -------------------------------------------------------------------------
    MONGODB_URL: str = Field(default="mongodb://localhost:27017/indigoglass_raw")
    MONGODB_DATABASE: str = Field(default="indigoglass_raw")
    
    # -------------------------------------------------------------------------
    # Neo4j
    # -------------------------------------------------------------------------
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="password")
    
    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    
    # -------------------------------------------------------------------------
    # S3/MinIO
    # -------------------------------------------------------------------------
    S3_ENDPOINT_URL: str = Field(default="http://localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_REGION: str = Field(default="us-east-1")
    S3_BUCKET_MODELS: str = Field(default="models")
    S3_BUCKET_EXPORTS: str = Field(default="exports")
    
    # -------------------------------------------------------------------------
    # Optimizer
    # -------------------------------------------------------------------------
    OPTIMIZER_URL: str = Field(default="http://localhost:8080")
    OPTIMIZER_TIMEOUT_SECONDS: int = Field(default=30)
    
    # -------------------------------------------------------------------------
    # ML
    # -------------------------------------------------------------------------
    ML_MODEL_CACHE_TTL: int = Field(default=3600)
    ML_FORECAST_HORIZON_DAYS: int = Field(default=14)
    ML_RANDOM_SEED: int = Field(default=42)
    
    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = Field(default=100)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

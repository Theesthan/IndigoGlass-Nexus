# =============================================================================
# IndigoGlass Nexus - Ingestion Worker Configuration
# =============================================================================
"""
Configuration settings for the ingestion worker.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Ingestion worker settings loaded from environment."""
    
    # MySQL Configuration
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "nexus"
    MYSQL_PASSWORD: str = "nexus_dev_password"
    MYSQL_DATABASE: str = "nexus_warehouse"
    
    # MongoDB Configuration
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_USER: str = "nexus"
    MONGO_PASSWORD: str = "nexus_dev_password"
    MONGO_DB: str = "nexus_raw"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # MinIO / S3 Configuration
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "nexus-artifacts"
    MINIO_SECURE: bool = False
    
    # Worker Configuration
    WORKER_CONCURRENCY: int = 4
    BATCH_SIZE: int = 1000
    
    # Observability
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_ENDPOINT: str = ""
    
    @property
    def MYSQL_DSN(self) -> str:
        """Build MySQL DSN."""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )
    
    @property
    def MONGO_URI(self) -> str:
        """Build MongoDB URI."""
        if self.MONGO_USER and self.MONGO_PASSWORD:
            return (
                f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}"
                f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}?authSource=admin"
            )
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}"
    
    @property
    def REDIS_URL(self) -> str:
        """Build Redis URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

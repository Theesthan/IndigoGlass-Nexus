# =============================================================================
# IndigoGlass Nexus - ML Training Configuration
# =============================================================================
"""
Configuration settings for ML training jobs.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ML training job settings."""
    
    # MySQL Configuration
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "nexus"
    MYSQL_PASSWORD: str = "nexus_dev_password"
    MYSQL_DATABASE: str = "nexus_warehouse"
    
    # MinIO / S3 Configuration
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "nexus-models"
    MINIO_SECURE: bool = False
    
    # MLflow Configuration
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "demand-forecasting"
    
    # Training Configuration
    TRAIN_START_DATE: str = ""
    TRAIN_END_DATE: str = ""
    FORECAST_HORIZON_DAYS: int = 14
    MIN_TRAINING_SAMPLES: int = 30
    
    # Model Configuration
    MODEL_NAME: str = "demand_forecast"
    MODEL_ALGORITHM: str = "xgboost"
    
    # Hyperparameters
    XGBOOST_MAX_DEPTH: int = 6
    XGBOOST_LEARNING_RATE: float = 0.1
    XGBOOST_N_ESTIMATORS: int = 100
    XGBOOST_MIN_CHILD_WEIGHT: int = 1
    XGBOOST_SUBSAMPLE: float = 0.8
    XGBOOST_COLSAMPLE_BYTREE: float = 0.8
    
    # Validation
    CV_FOLDS: int = 5
    TEST_SIZE_DAYS: int = 14
    
    @property
    def MYSQL_DSN(self) -> str:
        """Build MySQL DSN."""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

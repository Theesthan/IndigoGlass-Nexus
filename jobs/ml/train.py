# =============================================================================
# IndigoGlass Nexus - ML Training Pipeline
# =============================================================================
"""
XGBoost demand forecasting training pipeline.
"""

import hashlib
import io
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import click
import numpy as np
import pandas as pd
import structlog
import xgboost as xgb
from minio import Minio
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy import create_engine, text

from config import get_settings
from features import engineer_features, get_feature_columns, prepare_train_test_split

logger = structlog.get_logger()
settings = get_settings()


def get_engine():
    """Get SQLAlchemy engine."""
    return create_engine(settings.MYSQL_DSN, pool_pre_ping=True)


def get_minio_client() -> Minio:
    """Get MinIO client."""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def load_training_data(
    start_date: str = None,
    end_date: str = None,
) -> pd.DataFrame:
    """
    Load sales data for training.
    
    Args:
        start_date: Training start date (YYYY-MM-DD)
        end_date: Training end date (YYYY-MM-DD)
    
    Returns:
        DataFrame with sales data
    """
    logger.info("loading_training_data", start_date=start_date, end_date=end_date)
    
    engine = get_engine()
    
    query = """
        SELECT
            d.full_date as date,
            p.product_id,
            l.location_id,
            SUM(fs.quantity) as quantity,
            SUM(fs.total_amount) as revenue
        FROM fact_sales fs
        JOIN dim_date d ON fs.date_key = d.date_key
        JOIN dim_product p ON fs.product_sk = p.product_sk
        JOIN dim_location l ON fs.location_sk = l.location_sk
        WHERE 1=1
    """
    
    params = {}
    
    if start_date:
        query += " AND d.full_date >= :start_date"
        params["start_date"] = start_date
    
    if end_date:
        query += " AND d.full_date <= :end_date"
        params["end_date"] = end_date
    
    query += """
        GROUP BY d.full_date, p.product_id, l.location_id
        ORDER BY d.full_date, p.product_id, l.location_id
    """
    
    df = pd.read_sql(query, engine, params=params)
    engine.dispose()
    
    logger.info("training_data_loaded", rows=len(df), columns=list(df.columns))
    
    return df


def train_xgboost_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Tuple[xgb.XGBRegressor, Dict[str, float]]:
    """
    Train XGBoost regressor.
    
    Args:
        X_train: Training features
        y_train: Training target
        X_test: Test features
        y_test: Test target
    
    Returns:
        Trained model and metrics dictionary
    """
    logger.info("training_xgboost_model")
    
    params = {
        "objective": "reg:squarederror",
        "max_depth": settings.XGBOOST_MAX_DEPTH,
        "learning_rate": settings.XGBOOST_LEARNING_RATE,
        "n_estimators": settings.XGBOOST_N_ESTIMATORS,
        "min_child_weight": settings.XGBOOST_MIN_CHILD_WEIGHT,
        "subsample": settings.XGBOOST_SUBSAMPLE,
        "colsample_bytree": settings.XGBOOST_COLSAMPLE_BYTREE,
        "random_state": 42,
        "n_jobs": -1,
    }
    
    model = xgb.XGBRegressor(**params)
    
    # Train with early stopping
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    
    # Predict
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Calculate metrics
    metrics = {
        "train_mae": float(mean_absolute_error(y_train, y_pred_train)),
        "train_rmse": float(np.sqrt(mean_squared_error(y_train, y_pred_train))),
        "test_mae": float(mean_absolute_error(y_test, y_pred_test)),
        "test_rmse": float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
        "test_mape": float(mean_absolute_percentage_error(y_test, y_pred_test)),
    }
    
    # Feature importance
    feature_importance = dict(zip(
        get_feature_columns(),
        model.feature_importances_.tolist(),
    ))
    
    logger.info("model_trained", **metrics)
    
    return model, metrics, feature_importance


def cross_validate_model(
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
) -> Dict[str, float]:
    """
    Perform time series cross-validation.
    
    Args:
        X: Features
        y: Target
        n_splits: Number of CV splits
    
    Returns:
        Cross-validation metrics
    """
    logger.info("cross_validating_model", n_splits=n_splits)
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    mae_scores = []
    rmse_scores = []
    
    params = {
        "objective": "reg:squarederror",
        "max_depth": settings.XGBOOST_MAX_DEPTH,
        "learning_rate": settings.XGBOOST_LEARNING_RATE,
        "n_estimators": settings.XGBOOST_N_ESTIMATORS,
        "random_state": 42,
        "n_jobs": -1,
    }
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train_cv = X.iloc[train_idx]
        y_train_cv = y.iloc[train_idx]
        X_val_cv = X.iloc[val_idx]
        y_val_cv = y.iloc[val_idx]
        
        model = xgb.XGBRegressor(**params)
        model.fit(X_train_cv, y_train_cv, verbose=False)
        
        y_pred = model.predict(X_val_cv)
        
        mae_scores.append(mean_absolute_error(y_val_cv, y_pred))
        rmse_scores.append(np.sqrt(mean_squared_error(y_val_cv, y_pred)))
        
        logger.debug(f"fold_{fold}", mae=mae_scores[-1], rmse=rmse_scores[-1])
    
    cv_metrics = {
        "cv_mae_mean": float(np.mean(mae_scores)),
        "cv_mae_std": float(np.std(mae_scores)),
        "cv_rmse_mean": float(np.mean(rmse_scores)),
        "cv_rmse_std": float(np.std(rmse_scores)),
    }
    
    logger.info("cross_validation_complete", **cv_metrics)
    
    return cv_metrics


def save_model_to_s3(
    model: xgb.XGBRegressor,
    model_name: str,
    version: str,
    metrics: Dict[str, Any],
) -> str:
    """
    Save model artifact to S3/MinIO.
    
    Args:
        model: Trained model
        model_name: Model name
        version: Model version
        metrics: Model metrics
    
    Returns:
        S3 URI of saved model
    """
    client = get_minio_client()
    bucket = settings.MINIO_BUCKET
    
    # Ensure bucket exists
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    
    # Serialize model
    model_buffer = io.BytesIO()
    pickle.dump(model, model_buffer)
    model_buffer.seek(0)
    model_size = model_buffer.getbuffer().nbytes
    
    # Upload model
    model_path = f"models/{model_name}/{version}/model.pkl"
    client.put_object(
        bucket,
        model_path,
        model_buffer,
        model_size,
        content_type="application/octet-stream",
    )
    
    # Upload metrics
    metrics_buffer = io.BytesIO(json.dumps(metrics).encode())
    metrics_path = f"models/{model_name}/{version}/metrics.json"
    client.put_object(
        bucket,
        metrics_path,
        metrics_buffer,
        len(metrics_buffer.getvalue()),
        content_type="application/json",
    )
    
    s3_uri = f"s3://{bucket}/{model_path}"
    
    logger.info("model_saved_to_s3", uri=s3_uri)
    
    return s3_uri


def register_model(
    model_name: str,
    version: str,
    algorithm: str,
    metrics: Dict[str, Any],
    hyperparams: Dict[str, Any],
    feature_names: list[str],
    s3_uri: str,
    train_start: str,
    train_end: str,
) -> int:
    """
    Register model in MySQL model registry.
    
    Args:
        model_name: Model name
        version: Model version
        algorithm: Algorithm name
        metrics: Model metrics
        hyperparams: Hyperparameters used
        feature_names: List of feature names
        s3_uri: S3 URI of model artifact
        train_start: Training data start date
        train_end: Training data end date
    
    Returns:
        Model ID
    """
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                INSERT INTO ml_model (
                    model_name, version, algorithm, status,
                    metrics_json, hyperparams_json, feature_names_json,
                    artifact_s3_uri, training_data_start, training_data_end,
                    trained_at, trained_by
                ) VALUES (
                    :model_name, :version, :algorithm, 'staged',
                    :metrics, :hyperparams, :features,
                    :s3_uri, :train_start, :train_end,
                    NOW(), 'ml-training-job'
                )
            """),
            {
                "model_name": model_name,
                "version": version,
                "algorithm": algorithm,
                "metrics": json.dumps(metrics),
                "hyperparams": json.dumps(hyperparams),
                "features": json.dumps(feature_names),
                "s3_uri": s3_uri,
                "train_start": train_start,
                "train_end": train_end,
            },
        )
        
        model_id = result.lastrowid
        conn.commit()
    
    engine.dispose()
    
    logger.info("model_registered", model_id=model_id, version=version)
    
    return model_id


def generate_version() -> str:
    """Generate version string based on timestamp."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d_%H%M%S")


@click.command()
@click.option("--start-date", "-s", help="Training start date (YYYY-MM-DD)")
@click.option("--end-date", "-e", help="Training end date (YYYY-MM-DD)")
@click.option("--model-name", "-m", default="demand_forecast", help="Model name")
@click.option("--test-days", "-t", default=14, help="Number of days for test set")
@click.option("--cv-folds", "-c", default=5, help="Number of CV folds")
def train(
    start_date: str,
    end_date: str,
    model_name: str,
    test_days: int,
    cv_folds: int,
):
    """
    Train demand forecasting model.
    """
    logger.info(
        "training_pipeline_started",
        model_name=model_name,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Load data
    raw_df = load_training_data(start_date, end_date)
    
    if len(raw_df) < settings.MIN_TRAINING_SAMPLES:
        logger.error("insufficient_data", samples=len(raw_df))
        raise click.ClickException(
            f"Insufficient training data: {len(raw_df)} samples"
        )
    
    # Engineer features
    df = engineer_features(raw_df)
    
    # Train/test split
    X_train, X_test, y_train, y_test = prepare_train_test_split(df, test_days)
    
    # Cross-validation
    feature_cols = get_feature_columns()
    cv_metrics = cross_validate_model(
        df[feature_cols],
        df["quantity"],
        n_splits=cv_folds,
    )
    
    # Train final model
    model, test_metrics, feature_importance = train_xgboost_model(
        X_train, y_train, X_test, y_test
    )
    
    # Combine metrics
    all_metrics = {**test_metrics, **cv_metrics, "feature_importance": feature_importance}
    
    # Generate version
    version = generate_version()
    
    # Hyperparameters used
    hyperparams = {
        "max_depth": settings.XGBOOST_MAX_DEPTH,
        "learning_rate": settings.XGBOOST_LEARNING_RATE,
        "n_estimators": settings.XGBOOST_N_ESTIMATORS,
        "min_child_weight": settings.XGBOOST_MIN_CHILD_WEIGHT,
        "subsample": settings.XGBOOST_SUBSAMPLE,
        "colsample_bytree": settings.XGBOOST_COLSAMPLE_BYTREE,
    }
    
    # Save to S3
    s3_uri = save_model_to_s3(model, model_name, version, all_metrics)
    
    # Register in DB
    model_id = register_model(
        model_name=model_name,
        version=version,
        algorithm="xgboost",
        metrics=all_metrics,
        hyperparams=hyperparams,
        feature_names=feature_cols,
        s3_uri=s3_uri,
        train_start=start_date or str(raw_df["date"].min()),
        train_end=end_date or str(raw_df["date"].max()),
    )
    
    logger.info(
        "training_pipeline_completed",
        model_id=model_id,
        version=version,
        test_mae=test_metrics["test_mae"],
        test_mape=test_metrics["test_mape"],
        s3_uri=s3_uri,
    )
    
    click.echo(f"Model trained successfully!")
    click.echo(f"  Model ID: {model_id}")
    click.echo(f"  Version: {version}")
    click.echo(f"  Test MAE: {test_metrics['test_mae']:.2f}")
    click.echo(f"  Test MAPE: {test_metrics['test_mape']:.2%}")
    click.echo(f"  S3 URI: {s3_uri}")


if __name__ == "__main__":
    train()

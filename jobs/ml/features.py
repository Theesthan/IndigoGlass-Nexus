# =============================================================================
# IndigoGlass Nexus - Feature Engineering
# =============================================================================
"""
Feature engineering for demand forecasting model.
"""

from datetime import datetime, timedelta
from typing import Tuple

import holidays
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger()


def engineer_features(df: pd.DataFrame, country: str = "US") -> pd.DataFrame:
    """
    Engineer features for demand forecasting.
    
    Args:
        df: Raw sales data with columns [date, product_id, location_id, quantity]
        country: Country code for holiday detection
    
    Returns:
        DataFrame with engineered features
    """
    logger.info("engineering_features", rows=len(df))
    
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    
    # Date features
    df = add_date_features(df)
    
    # Holiday features
    df = add_holiday_features(df, country)
    
    # Lag features
    df = add_lag_features(df)
    
    # Rolling statistics
    df = add_rolling_features(df)
    
    # Trend features
    df = add_trend_features(df)
    
    # Drop rows with NaN from lag/rolling
    initial_len = len(df)
    df = df.dropna()
    logger.info("features_engineered", initial=initial_len, final=len(df))
    
    return df


def add_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar-based features."""
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["day_of_year"] = df["date"].dt.dayofyear
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["year"] = df["date"].dt.year
    
    # Cyclical encoding for day of week
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    
    # Cyclical encoding for month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    
    # Weekend flag
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    
    # Month start/end flags
    df["is_month_start"] = df["date"].dt.is_month_start.astype(int)
    df["is_month_end"] = df["date"].dt.is_month_end.astype(int)
    
    return df


def add_holiday_features(df: pd.DataFrame, country: str = "US") -> pd.DataFrame:
    """Add holiday-related features."""
    years = df["date"].dt.year.unique()
    country_holidays = holidays.country_holidays(country, years=years)
    
    df["is_holiday"] = df["date"].dt.date.apply(lambda x: x in country_holidays).astype(int)
    
    # Days until next holiday / since last holiday
    holiday_dates = sorted(country_holidays.keys())
    
    def days_to_holiday(date):
        date = date.date() if hasattr(date, "date") else date
        future = [h for h in holiday_dates if h > date]
        return (future[0] - date).days if future else 999
    
    def days_since_holiday(date):
        date = date.date() if hasattr(date, "date") else date
        past = [h for h in holiday_dates if h < date]
        return (date - past[-1]).days if past else 999
    
    df["days_to_holiday"] = df["date"].apply(days_to_holiday)
    df["days_since_holiday"] = df["date"].apply(days_since_holiday)
    
    # Cap extreme values
    df["days_to_holiday"] = df["days_to_holiday"].clip(upper=30)
    df["days_since_holiday"] = df["days_since_holiday"].clip(upper=30)
    
    return df


def add_lag_features(df: pd.DataFrame, group_cols: list = None) -> pd.DataFrame:
    """Add lagged quantity features."""
    if group_cols is None:
        group_cols = ["product_id", "location_id"]
    
    lags = [1, 7, 14, 28]
    
    for lag in lags:
        df[f"qty_lag_{lag}d"] = df.groupby(group_cols)["quantity"].shift(lag)
    
    # Same day last week
    df["qty_same_dow_1w"] = df.groupby(group_cols)["quantity"].shift(7)
    df["qty_same_dow_2w"] = df.groupby(group_cols)["quantity"].shift(14)
    df["qty_same_dow_4w"] = df.groupby(group_cols)["quantity"].shift(28)
    
    return df


def add_rolling_features(df: pd.DataFrame, group_cols: list = None) -> pd.DataFrame:
    """Add rolling statistics features."""
    if group_cols is None:
        group_cols = ["product_id", "location_id"]
    
    windows = [7, 14, 28]
    
    for window in windows:
        # Rolling mean
        df[f"qty_rolling_mean_{window}d"] = (
            df.groupby(group_cols)["quantity"]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
        )
        
        # Rolling std
        df[f"qty_rolling_std_{window}d"] = (
            df.groupby(group_cols)["quantity"]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).std())
        )
        
        # Rolling min/max
        df[f"qty_rolling_min_{window}d"] = (
            df.groupby(group_cols)["quantity"]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).min())
        )
        df[f"qty_rolling_max_{window}d"] = (
            df.groupby(group_cols)["quantity"]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).max())
        )
    
    # Fill NaN std with 0
    std_cols = [c for c in df.columns if "rolling_std" in c]
    df[std_cols] = df[std_cols].fillna(0)
    
    return df


def add_trend_features(df: pd.DataFrame, group_cols: list = None) -> pd.DataFrame:
    """Add trend-based features."""
    if group_cols is None:
        group_cols = ["product_id", "location_id"]
    
    # Week over week change
    df["qty_wow_change"] = (
        df.groupby(group_cols)["quantity"]
        .transform(lambda x: x.shift(1) - x.shift(8))
    )
    
    # Week over week percentage change
    df["qty_wow_pct_change"] = (
        df.groupby(group_cols)["quantity"]
        .transform(lambda x: (x.shift(1) - x.shift(8)) / (x.shift(8) + 1))
    )
    
    # 7-day vs 28-day average ratio (trend indicator)
    df["short_long_ratio"] = (
        df["qty_rolling_mean_7d"] / (df["qty_rolling_mean_28d"] + 1)
    )
    
    return df


def get_feature_columns() -> list[str]:
    """Get list of feature column names."""
    return [
        # Date features
        "day_of_week", "day_of_month", "day_of_year", "week_of_year",
        "month", "quarter", "year",
        "dow_sin", "dow_cos", "month_sin", "month_cos",
        "is_weekend", "is_month_start", "is_month_end",
        
        # Holiday features
        "is_holiday", "days_to_holiday", "days_since_holiday",
        
        # Lag features
        "qty_lag_1d", "qty_lag_7d", "qty_lag_14d", "qty_lag_28d",
        "qty_same_dow_1w", "qty_same_dow_2w", "qty_same_dow_4w",
        
        # Rolling features
        "qty_rolling_mean_7d", "qty_rolling_std_7d",
        "qty_rolling_min_7d", "qty_rolling_max_7d",
        "qty_rolling_mean_14d", "qty_rolling_std_14d",
        "qty_rolling_min_14d", "qty_rolling_max_14d",
        "qty_rolling_mean_28d", "qty_rolling_std_28d",
        "qty_rolling_min_28d", "qty_rolling_max_28d",
        
        # Trend features
        "qty_wow_change", "qty_wow_pct_change", "short_long_ratio",
    ]


def prepare_train_test_split(
    df: pd.DataFrame,
    test_days: int = 14,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split data into train and test sets chronologically.
    
    Args:
        df: Engineered features DataFrame
        test_days: Number of days to use for testing
    
    Returns:
        X_train, X_test, y_train, y_test
    """
    df = df.sort_values("date")
    
    cutoff_date = df["date"].max() - timedelta(days=test_days)
    
    train_df = df[df["date"] <= cutoff_date]
    test_df = df[df["date"] > cutoff_date]
    
    feature_cols = get_feature_columns()
    
    X_train = train_df[feature_cols]
    X_test = test_df[feature_cols]
    y_train = train_df["quantity"]
    y_test = test_df["quantity"]
    
    logger.info(
        "train_test_split",
        train_samples=len(X_train),
        test_samples=len(X_test),
        cutoff_date=str(cutoff_date),
    )
    
    return X_train, X_test, y_train, y_test

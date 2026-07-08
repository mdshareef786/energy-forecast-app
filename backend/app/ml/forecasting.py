"""
Forecasting module.

Supports three interchangeable model backends:
- Prophet: handles daily/weekly seasonality well, gives confidence intervals natively.
- ARIMA: classic statistical time-series model (statsmodels), good at capturing
  autocorrelation/trend without assuming a fixed seasonal shape.
- Regression: a lightweight linear baseline (time index + hour/day-of-week dummies)
  used for model comparison and as a fallback when Prophet/ARIMA aren't suitable.

All three return a common shape so the API/frontend don't need to care which model ran.
"""
from datetime import timedelta
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

HORIZON_TO_PERIODS = {
    "24h": 24,     # hourly steps
    "7d": 7 * 24,
    "30d": 30 * 24,
}

# ARIMA forecasts get slow/unstable over very long horizons on an hourly grid;
# cap how far out we ask it to project directly and note the approximation.
ARIMA_MAX_PERIODS = 7 * 24


def _prepare_series(readings: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(readings)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    # Resample to hourly to ensure a regular frequency, filling small gaps by interpolation
    df = df.set_index("timestamp").resample("1h").mean(numeric_only=True)
    df["energy_kwh"] = df["energy_kwh"].interpolate(limit=6).fillna(method="bfill").fillna(method="ffill")
    df = df.reset_index()
    return df


def _train_test_split(df: pd.DataFrame, test_frac: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame]:
    n_test = max(1, int(len(df) * test_frac))
    return df.iloc[:-n_test], df.iloc[-n_test:]


def forecast_with_prophet(readings: List[Dict[str, Any]], horizon: str) -> Dict[str, Any]:
    from prophet import Prophet  # imported lazily; heavy import

    df = _prepare_series(readings)
    if len(df) < 48:
        raise ValueError("Not enough data for Prophet (need at least 48 hourly points)")

    train, test = _train_test_split(df)

    m = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False)
    prophet_train = train.rename(columns={"timestamp": "ds", "energy_kwh": "y"})[["ds", "y"]]
    m.fit(prophet_train)

    periods = HORIZON_TO_PERIODS[horizon]
    future = m.make_future_dataframe(periods=periods, freq="h")
    forecast = m.predict(future)

    # Evaluate on held-out test window using in-sample predictions
    metrics = {"mae": None, "rmse": None, "mape": None}
    if len(test) > 0:
        merged = forecast.set_index("ds").loc[test["timestamp"], "yhat"]
        y_true = test["energy_kwh"].values
        y_pred = merged.values
        metrics["mae"] = float(mean_absolute_error(y_true, y_pred))
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        nonzero = y_true != 0
        metrics["mape"] = float(np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100) if nonzero.any() else None

    future_only = forecast[forecast["ds"] > df["timestamp"].max()]
    predictions = [
        {
            "timestamp": row.ds.isoformat(),
            "predicted": round(float(max(row.yhat, 0)), 3),
            "lower": round(float(max(row.yhat_lower, 0)), 3),
            "upper": round(float(max(row.yhat_upper, 0)), 3),
        }
        for row in future_only.itertuples()
    ]
    return {"predictions": predictions, **metrics}


def forecast_with_regression(readings: List[Dict[str, Any]], horizon: str) -> Dict[str, Any]:
    df = _prepare_series(readings)
    if len(df) < 24:
        raise ValueError("Not enough data for regression forecasting (need at least 24 hourly points)")

    df["t"] = np.arange(len(df))
    df["hour"] = df["timestamp"].dt.hour
    df["dow"] = df["timestamp"].dt.dayofweek

    feature_cols = ["t"]
    X = pd.get_dummies(df[["t", "hour", "dow"]], columns=["hour", "dow"], drop_first=True)
    y = df["energy_kwh"]

    train, test = _train_test_split(df)
    X_train, X_test = X.iloc[:len(train)], X.iloc[len(train):]
    y_train, y_test = y.iloc[:len(train)], y.iloc[len(train):]

    model = LinearRegression()
    model.fit(X_train, y_train)

    metrics = {"mae": None, "rmse": None, "mape": None}
    if len(X_test) > 0:
        y_pred_test = model.predict(X_test)
        metrics["mae"] = float(mean_absolute_error(y_test, y_pred_test))
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_test, y_pred_test)))
        nonzero = y_test.values != 0
        metrics["mape"] = float(np.mean(np.abs((y_test.values[nonzero] - y_pred_test[nonzero]) / y_test.values[nonzero])) * 100) if nonzero.any() else None

    periods = HORIZON_TO_PERIODS[horizon]
    last_ts = df["timestamp"].max()
    future_ts = [last_ts + timedelta(hours=i + 1) for i in range(periods)]
    future_df = pd.DataFrame({
        "t": np.arange(len(df), len(df) + periods),
        "hour": [ts.hour for ts in future_ts],
        "dow": [ts.dayofweek for ts in future_ts],
    })
    X_future = pd.get_dummies(future_df, columns=["hour", "dow"], drop_first=True)
    X_future = X_future.reindex(columns=X.columns, fill_value=0)

    preds = model.predict(X_future)
    predictions = [
        {"timestamp": ts.isoformat(), "predicted": round(float(max(p, 0)), 3), "lower": None, "upper": None}
        for ts, p in zip(future_ts, preds)
    ]
    return {"predictions": predictions, **metrics}


def forecast_with_arima(readings: List[Dict[str, Any]], horizon: str) -> Dict[str, Any]:
    from statsmodels.tsa.arima.model import ARIMA
    import warnings

    df = _prepare_series(readings)
    if len(df) < 48:
        raise ValueError("Not enough data for ARIMA (need at least 48 hourly points)")

    train, test = _train_test_split(df)
    y_train = train.set_index("timestamp")["energy_kwh"]
    y_train.index.freq = "h"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ARIMA(y_train, order=(2, 1, 2))
        fit = model.fit()

    metrics = {"mae": None, "rmse": None, "mape": None}
    if len(test) > 0:
        test_pred = fit.forecast(steps=len(test))
        y_true = test["energy_kwh"].values
        y_pred = test_pred.values
        metrics["mae"] = float(mean_absolute_error(y_true, y_pred))
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        nonzero = y_true != 0
        metrics["mape"] = float(np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100) if nonzero.any() else None

    # Refit on the full series (train+test) before projecting forward
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        y_full = df.set_index("timestamp")["energy_kwh"]
        y_full.index.freq = "h"
        full_model = ARIMA(y_full, order=(2, 1, 2))
        full_fit = full_model.fit()

    periods = min(HORIZON_TO_PERIODS[horizon], ARIMA_MAX_PERIODS)
    forecast_res = full_fit.get_forecast(steps=periods)
    mean = forecast_res.predicted_mean
    conf_int = forecast_res.conf_int(alpha=0.2)  # ~80% interval

    last_ts = df["timestamp"].max()
    predictions = []
    for i in range(periods):
        ts = last_ts + timedelta(hours=i + 1)
        predictions.append({
            "timestamp": ts.isoformat(),
            "predicted": round(float(max(mean.iloc[i], 0)), 3),
            "lower": round(float(max(conf_int.iloc[i, 0], 0)), 3),
            "upper": round(float(max(conf_int.iloc[i, 1], 0)), 3),
        })

    if HORIZON_TO_PERIODS[horizon] > ARIMA_MAX_PERIODS:
        metrics["note"] = (
            f"ARIMA projection capped at {ARIMA_MAX_PERIODS}h; longer horizons compound "
            f"autoregressive error too much to be meaningful with this order."
        )

    return {"predictions": predictions, **metrics}


def run_forecast(readings: List[Dict[str, Any]], horizon: str, model_type: str) -> Dict[str, Any]:
    if model_type == "prophet":
        try:
            return forecast_with_prophet(readings, horizon)
        except Exception:
            # Fallback to regression if Prophet fails (e.g. sparse data)
            return forecast_with_regression(readings, horizon)
    if model_type == "arima":
        try:
            return forecast_with_arima(readings, horizon)
        except Exception:
            return forecast_with_regression(readings, horizon)
    return forecast_with_regression(readings, horizon)

from typing import List, Dict, Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def _severity_from_z(z: float) -> str:
    az = abs(z)
    if az >= 5:
        return "high"
    if az >= 4:
        return "medium"
    return "low"


def detect_anomalies_zscore(readings: List[Dict[str, Any]], threshold: float = 3.0) -> List[Dict[str, Any]]:
    df = pd.DataFrame(readings)
    if df.empty:
        return []
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    mean = df["energy_kwh"].mean()
    std = df["energy_kwh"].std(ddof=0) or 1e-9
    df["z_score"] = (df["energy_kwh"] - mean) / std

    results = []
    for row in df[df["z_score"].abs() >= threshold].itertuples():
        hour = row.timestamp.hour
        reason = "Unusual spike" if row.z_score > 0 else "Unusual drop"
        if hour >= 23 or hour <= 5:
            reason += " during night-time hours (possible faulty device)"
        results.append({
            "timestamp": row.timestamp.isoformat(),
            "energy_kwh": float(row.energy_kwh),
            "z_score": round(float(row.z_score), 3),
            "method": "z_score",
            "severity": _severity_from_z(row.z_score),
            "reason": reason,
        })
    return results


def detect_anomalies_isolation_forest(readings: List[Dict[str, Any]], contamination: float = 0.03) -> List[Dict[str, Any]]:
    df = pd.DataFrame(readings)
    if len(df) < 10:
        return []
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    df["hour"] = df["timestamp"].dt.hour
    df["dow"] = df["timestamp"].dt.dayofweek

    X = df[["energy_kwh", "hour", "dow"]].fillna(0)
    model = IsolationForest(contamination=contamination, random_state=42)
    df["anomaly_flag"] = model.fit_predict(X)  # -1 = anomaly
    df["score"] = model.decision_function(X)

    results = []
    for row in df[df["anomaly_flag"] == -1].itertuples():
        reason = "Sensor/consumption pattern anomaly detected by Isolation Forest"
        if row.hour >= 23 or row.hour <= 5:
            reason += " (occurs during night-time)"
        severity = "high" if row.score < -0.15 else ("medium" if row.score < -0.05 else "low")
        results.append({
            "timestamp": row.timestamp.isoformat(),
            "energy_kwh": float(row.energy_kwh),
            "z_score": round(float(row.score), 3),
            "method": "isolation_forest",
            "severity": severity,
            "reason": reason,
        })
    return results


def detect_peak_periods(readings: List[Dict[str, Any]], percentile: float = 0.90) -> Dict[str, Any]:
    """Identify hours of day that historically represent peak load, and flag if
    upcoming forecasted data (if provided) crosses the threshold."""
    df = pd.DataFrame(readings)
    if df.empty:
        return {"threshold_kwh": None, "peak_hours": [], "alerts": []}
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour

    threshold = float(df["energy_kwh"].quantile(percentile))
    hourly_avg = df.groupby("hour")["energy_kwh"].mean()
    peak_hours = hourly_avg[hourly_avg >= hourly_avg.quantile(percentile)].index.tolist()

    alerts = []
    if peak_hours:
        start, end = min(peak_hours), max(peak_hours)
        alerts.append(f"Expected peak consumption between {start}:00 and {end}:00 based on historical patterns")

    return {
        "threshold_kwh": round(threshold, 3),
        "peak_hours": sorted(peak_hours),
        "alerts": alerts,
    }

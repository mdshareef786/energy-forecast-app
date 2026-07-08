from typing import List, Dict, Any

import pandas as pd


def generate_recommendations(
    readings: List[Dict[str, Any]],
    device_name: str,
    peak_hours: List[int],
    anomalies: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Rule-based recommendation engine driven by consumption patterns,
    peak-hour analysis, and detected anomalies. Kept rule-based (rather than a
    black-box model) so recommendations stay explainable and auditable."""
    df = pd.DataFrame(readings)
    recs: List[Dict[str, Any]] = []

    if df.empty:
        return recs

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    avg_kwh = df["energy_kwh"].mean()

    # 1. Peak-hour load balancing
    if peak_hours:
        peak_avg = df[df["hour"].isin(peak_hours)]["energy_kwh"].mean()
        off_peak_avg = df[~df["hour"].isin(peak_hours)]["energy_kwh"].mean()
        if peak_avg and off_peak_avg and peak_avg > off_peak_avg * 1.2:
            estimated_savings = round((peak_avg - off_peak_avg) * 0.3 * len(peak_hours), 2)
            recs.append({
                "category": "load_balancing",
                "message": f"Shift non-critical processing on '{device_name}' from peak hours "
                           f"({min(peak_hours)}:00-{max(peak_hours)}:00) to off-peak hours to flatten demand",
                "estimated_savings_kwh": estimated_savings,
                "priority": "high",
            })

    # 2. Off-peak scheduling suggestion
    night_avg = df[(df["hour"] >= 0) & (df["hour"] <= 5)]["energy_kwh"].mean()
    if night_avg and night_avg > avg_kwh * 0.4:
        recs.append({
            "category": "off_peak",
            "message": f"'{device_name}' shows significant night-time (12AM-5AM) baseline usage; "
                       f"consider scheduling batch/background tasks here to use cheaper off-peak tariffs",
            "estimated_savings_kwh": round(night_avg * 0.15, 2),
            "priority": "medium",
        })

    # 3. Device shutdown / anomaly-driven recommendations
    high_severity_anomalies = [a for a in anomalies if a.get("severity") == "high"]
    if high_severity_anomalies:
        recs.append({
            "category": "shutdown",
            "message": f"'{device_name}' had {len(high_severity_anomalies)} high-severity anomalies recently; "
                       f"inspect for faulty behavior and consider automatic shutdown outside operating hours",
            "estimated_savings_kwh": round(avg_kwh * 0.1 * len(high_severity_anomalies), 2),
            "priority": "high",
        })

    # 4. General efficiency scheduling
    if not recs:
        recs.append({
            "category": "scheduling",
            "message": f"'{device_name}' consumption looks stable; maintain current schedule and "
                       f"re-evaluate after the next forecast cycle",
            "estimated_savings_kwh": 0.0,
            "priority": "low",
        })

    return recs

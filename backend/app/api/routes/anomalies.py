import datetime as dt
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.reading import EnergyReading
from app.models.ml_results import Anomaly
from app.models.asset import Device
from app.models.alert import AlertSource, AlertSeverity
from app.models.user import User, UserRole
from app.schemas.ml import AnomalyOut
from app.core.security import get_current_user, require_role
from app.core.config import settings
from app.ml.anomaly import detect_anomalies_zscore, detect_anomalies_isolation_forest, detect_peak_periods
from app.services.alerts import create_alert

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


@router.post("/detect/{device_id}", response_model=List[AnomalyOut])
def detect_anomalies(
    device_id: int,
    method: str = Query("z_score", pattern="^(z_score|isolation_forest)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    readings = (
        db.query(EnergyReading)
        .filter(EnergyReading.device_id == device_id)
        .order_by(EnergyReading.timestamp)
        .all()
    )
    if not readings:
        raise HTTPException(status_code=400, detail="No energy readings available for this device")

    reading_dicts = [{"timestamp": r.timestamp, "energy_kwh": r.energy_kwh} for r in readings]

    if method == "z_score":
        found = detect_anomalies_zscore(reading_dicts, threshold=settings.ANOMALY_Z_THRESHOLD)
    else:
        found = detect_anomalies_isolation_forest(reading_dicts)

    saved = []
    for a in found:
        a = {**a, "timestamp": dt.datetime.fromisoformat(a["timestamp"])}
        anomaly = Anomaly(device_id=device_id, **a)
        db.add(anomaly)
        saved.append(anomaly)
    db.commit()
    for a in saved:
        db.refresh(a)

    high_severity = [a for a in saved if a.severity == "high" or getattr(a.severity, "value", None) == "high"]
    if high_severity:
        create_alert(
            db,
            source=AlertSource.ANOMALY,
            severity=AlertSeverity.CRITICAL,
            message=f"{device.name}: {len(high_severity)} high-severity anomal{'y' if len(high_severity) == 1 else 'ies'} "
                    f"detected via {method.replace('_', ' ')}",
            device_id=device_id,
        )

    return saved


@router.get("/device/{device_id}", response_model=List[AnomalyOut])
def get_anomalies_for_device(device_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    return (
        db.query(Anomaly)
        .filter(Anomaly.device_id == device_id)
        .order_by(Anomaly.timestamp.desc())
        .all()
    )


@router.get("/peaks/{device_id}")
def get_peak_analysis(device_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    readings = (
        db.query(EnergyReading)
        .filter(EnergyReading.device_id == device_id)
        .order_by(EnergyReading.timestamp)
        .all()
    )
    if not readings:
        raise HTTPException(status_code=400, detail="No energy readings available for this device")
    reading_dicts = [{"timestamp": r.timestamp, "energy_kwh": r.energy_kwh} for r in readings]
    return detect_peak_periods(reading_dicts, percentile=settings.PEAK_PERCENTILE)

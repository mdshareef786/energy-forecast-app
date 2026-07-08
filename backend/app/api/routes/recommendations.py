from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.reading import EnergyReading
from app.models.ml_results import Anomaly, Recommendation
from app.models.asset import Device
from app.models.user import User, UserRole
from app.schemas.ml import RecommendationOut
from app.core.security import get_current_user, require_role
from app.core.config import settings
from app.ml.anomaly import detect_peak_periods
from app.ml.optimization import generate_recommendations

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("/generate/{device_id}", response_model=List[RecommendationOut])
def generate_device_recommendations(
    device_id: int,
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
    peak_info = detect_peak_periods(reading_dicts, percentile=settings.PEAK_PERCENTILE)

    recent_anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.device_id == device_id)
        .order_by(Anomaly.timestamp.desc())
        .limit(50)
        .all()
    )
    anomaly_dicts = [{"severity": a.severity.value if hasattr(a.severity, "value") else a.severity} for a in recent_anomalies]

    recs = generate_recommendations(reading_dicts, device.name, peak_info["peak_hours"], anomaly_dicts)

    saved = []
    for r in recs:
        rec = Recommendation(device_id=device_id, building_id=device.building_id, **r)
        db.add(rec)
        saved.append(rec)
    db.commit()
    for r in saved:
        db.refresh(r)
    return saved


@router.get("/device/{device_id}", response_model=List[RecommendationOut])
def get_recommendations_for_device(device_id: int, db: Session = Depends(get_db),
                                    current_user: User = Depends(get_current_user)):
    return (
        db.query(Recommendation)
        .filter(Recommendation.device_id == device_id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )


@router.get("/building/{building_id}", response_model=List[RecommendationOut])
def get_recommendations_for_building(building_id: int, db: Session = Depends(get_db),
                                      current_user: User = Depends(get_current_user)):
    return (
        db.query(Recommendation)
        .filter(Recommendation.building_id == building_id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.reading import EnergyReading
from app.models.asset import Device, Building
from app.models.ml_results import Anomaly, Recommendation, Forecast
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/device/{device_id}/history")
def device_history(
    device_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    since = datetime.utcnow() - timedelta(days=days)
    readings = (
        db.query(EnergyReading)
        .filter(EnergyReading.device_id == device_id, EnergyReading.timestamp >= since)
        .order_by(EnergyReading.timestamp)
        .all()
    )
    return {
        "device_id": device_id,
        "device_name": device.name,
        "readings": [
            {"timestamp": r.timestamp.isoformat(), "energy_kwh": r.energy_kwh, "temperature_c": r.temperature_c}
            for r in readings
        ],
    }


@router.get("/building/{building_id}/summary")
def building_summary(building_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    devices = db.query(Device).filter(Device.building_id == building_id).all()
    device_ids = [d.id for d in devices]

    total_kwh = (
        db.query(func.coalesce(func.sum(EnergyReading.energy_kwh), 0.0))
        .filter(EnergyReading.device_id.in_(device_ids))
        .scalar()
        if device_ids else 0.0
    )
    anomaly_count = db.query(func.count(Anomaly.id)).filter(Anomaly.device_id.in_(device_ids)).scalar() if device_ids else 0
    recommendation_count = (
        db.query(func.count(Recommendation.id)).filter(Recommendation.building_id == building_id).scalar()
    )

    return {
        "building_id": building_id,
        "building_name": building.name,
        "device_count": len(devices),
        "total_energy_kwh": round(float(total_kwh), 3),
        "anomaly_count": int(anomaly_count),
        "recommendation_count": int(recommendation_count),
        "devices": [{"id": d.id, "name": d.name, "device_type": d.device_type} for d in devices],
    }


@router.get("/device/{device_id}/forecast-accuracy")
def forecast_accuracy(device_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    forecasts = (
        db.query(Forecast)
        .filter(Forecast.device_id == device_id)
        .order_by(Forecast.generated_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": f.id,
            "model_type": f.model_type,
            "horizon": f.horizon,
            "generated_at": f.generated_at.isoformat(),
            "mae": f.mae,
            "rmse": f.rmse,
            "mape": f.mape,
        }
        for f in forecasts
    ]

from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.database import get_db, SessionLocal
from app.models.reading import EnergyReading
from app.models.ml_results import Forecast
from app.models.asset import Device
from app.models.alert import AlertSource, AlertSeverity
from app.models.user import User, UserRole
from app.schemas.ml import ForecastRequest, ForecastOut
from app.core.security import get_current_user, require_role
from app.core.config import settings
from app.ml.forecasting import run_forecast
from app.ml.anomaly import detect_peak_periods
from app.services.alerts import create_alert

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


def run_forecast_job(device_id: int, horizon: str, model_type: str):
    """Runs in a background task so the API responds immediately (non-blocking ML execution).
    Also used directly by the automated retraining scheduler (see app/services/retraining.py)."""
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        readings = (
            db.query(EnergyReading)
            .filter(EnergyReading.device_id == device_id)
            .order_by(EnergyReading.timestamp)
            .all()
        )
        if not readings or not device:
            return
        reading_dicts = [{"timestamp": r.timestamp, "energy_kwh": r.energy_kwh} for r in readings]
        result = run_forecast(reading_dicts, horizon, model_type)

        forecast = Forecast(
            device_id=device_id,
            model_type=model_type,
            horizon=horizon,
            mae=result.get("mae"),
            rmse=result.get("rmse"),
            mape=result.get("mape"),
            predictions=result["predictions"],
        )
        db.add(forecast)
        db.commit()

        # Peak-usage prediction alert: does the forecast expect the device to exceed
        # its historical peak threshold in the near term?
        peak_info = detect_peak_periods(reading_dicts, percentile=settings.PEAK_PERCENTILE)
        threshold = peak_info.get("threshold_kwh")
        if threshold is not None:
            near_term = result["predictions"][:24]  # next 24h of the forecast
            breaching = [p for p in near_term if p["predicted"] > threshold]
            if breaching:
                first_breach = breaching[0]
                create_alert(
                    db,
                    source=AlertSource.FORECAST_THRESHOLD,
                    severity=AlertSeverity.WARNING,
                    message=f"{device.name} is forecast to exceed its normal energy threshold "
                            f"({threshold} kWh) around {first_breach['timestamp'][:16].replace('T', ' ')}",
                    device_id=device_id,
                )
    finally:
        db.close()


# Backwards-compatible alias (background task registration below)
_run_forecast_job = run_forecast_job


@router.post("/generate", status_code=202)
def generate_forecast(
    payload: ForecastRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    device = db.query(Device).filter(Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    reading_count = db.query(EnergyReading).filter(EnergyReading.device_id == payload.device_id).count()
    if reading_count == 0:
        raise HTTPException(status_code=400, detail="No energy readings available for this device")

    background_tasks.add_task(_run_forecast_job, payload.device_id, payload.horizon.value, payload.model_type.value)
    return {"message": "Forecast generation started", "device_id": payload.device_id, "horizon": payload.horizon}


@router.get("/device/{device_id}", response_model=List[ForecastOut])
def get_forecasts_for_device(device_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    return (
        db.query(Forecast)
        .filter(Forecast.device_id == device_id)
        .order_by(Forecast.generated_at.desc())
        .all()
    )


@router.get("/latest/{device_id}", response_model=ForecastOut)
def get_latest_forecast(device_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    forecast = (
        db.query(Forecast)
        .filter(Forecast.device_id == device_id)
        .order_by(Forecast.generated_at.desc())
        .first()
    )
    if not forecast:
        raise HTTPException(status_code=404, detail="No forecast found for this device yet")
    return forecast


@router.post("/retrain-all", status_code=202)
def trigger_retraining(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Manually trigger the automated retraining pipeline immediately, rather than
    waiting for its scheduled interval. Regenerates forecasts for every device with
    readings, reusing each device's last model/horizon (or Prophet/7d as default)."""
    from app.services.retraining import retrain_all_devices

    background_tasks.add_task(retrain_all_devices)
    return {"message": "Retraining triggered for all devices with readings"}


"""
Automated retraining pipeline (bonus feature).

Periodically re-runs forecast generation for every device that has energy readings,
using each device's most recently used model/horizon (or sensible defaults for
devices that have never been forecast). This keeps forecasts fresh without the user
having to manually click "Generate forecast" after every new batch of readings.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.database import SessionLocal
from app.models.asset import Device
from app.models.reading import EnergyReading
from app.models.ml_results import Forecast
from app.models.alert import AlertSource, AlertSeverity
from app.services.alerts import create_alert

logger = logging.getLogger("retraining")

DEFAULT_MODEL = "prophet"
DEFAULT_HORIZON = "7d"

_scheduler = None


def retrain_all_devices():
    """Regenerate a forecast for every device that has at least one reading.
    Uses the model/horizon of that device's most recent forecast if one exists,
    otherwise falls back to Prophet/7d."""
    from app.api.routes.forecasts import run_forecast_job  # local import avoids circular import

    db = SessionLocal()
    try:
        device_ids = [
            row[0]
            for row in db.query(EnergyReading.device_id).distinct().all()
        ]
    finally:
        db.close()

    retrained = 0
    for device_id in device_ids:
        db = SessionLocal()
        try:
            last_forecast = (
                db.query(Forecast)
                .filter(Forecast.device_id == device_id)
                .order_by(Forecast.generated_at.desc())
                .first()
            )
            model_type = last_forecast.model_type.value if last_forecast else DEFAULT_MODEL
            horizon = last_forecast.horizon.value if last_forecast else DEFAULT_HORIZON
        finally:
            db.close()

        try:
            run_forecast_job(device_id, horizon, model_type)
            retrained += 1
        except Exception:
            logger.exception("Automated retraining failed for device %s", device_id)

    if retrained:
        db = SessionLocal()
        try:
            create_alert(
                db,
                source=AlertSource.RETRAINING,
                severity=AlertSeverity.INFO,
                message=f"Automated retraining completed for {retrained} device(s)",
            )
        finally:
            db.close()
    logger.info("Automated retraining cycle complete: %d device(s) retrained", retrained)


def start_scheduler(interval_hours: int = 24):
    """Called once at app startup. Safe to call multiple times (e.g. under
    --reload) since APScheduler jobs are replaced, not duplicated, by job id."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        retrain_all_devices,
        "interval",
        hours=interval_hours,
        id="retrain_all_devices",
        replace_existing=True,
        next_run_time=None,  # don't fire immediately on startup; wait one full interval
    )
    _scheduler.start()
    logger.info("Automated retraining scheduler started (every %sh)", interval_hours)
    return _scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

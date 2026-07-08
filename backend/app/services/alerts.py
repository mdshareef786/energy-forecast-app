from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity, AlertSource


def create_alert(
    db: Session,
    source: AlertSource,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    device_id: int = None,
    building_id: int = None,
) -> Alert:
    alert = Alert(
        device_id=device_id,
        building_id=building_id,
        source=source,
        severity=severity,
        message=message,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alerts import AlertOut
from app.core.security import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=List[AlertOut])
def list_alerts(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Alert)
    if unread_only:
        query = query.filter(Alert.is_read == False)  # noqa: E712
    return query.order_by(Alert.created_at.desc()).limit(limit).all()


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(Alert).filter(Alert.is_read == False).count()  # noqa: E712
    return {"count": count}


@router.post("/{alert_id}/read", response_model=AlertOut)
def mark_read(alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    updated = db.query(Alert).filter(Alert.is_read == False).update({"is_read": True})  # noqa: E712
    db.commit()
    return {"updated": updated}

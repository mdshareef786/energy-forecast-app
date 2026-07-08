from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertSeverity, AlertSource


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: Optional[int] = None
    building_id: Optional[int] = None
    source: AlertSource
    severity: AlertSeverity
    message: str
    is_read: bool
    created_at: datetime

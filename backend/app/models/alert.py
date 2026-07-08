import enum

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean, func

from app.db.database import Base


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertSource(str, enum.Enum):
    PEAK_PREDICTION = "peak_prediction"
    ANOMALY = "anomaly"
    FORECAST_THRESHOLD = "forecast_threshold"
    RETRAINING = "retraining"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    source = Column(Enum(AlertSource), nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.INFO)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

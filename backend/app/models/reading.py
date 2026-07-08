from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship

from app.db.database import Base


class EnergyReading(Base):
    __tablename__ = "energy_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    energy_kwh = Column(Float, nullable=False)
    temperature_c = Column(Float, nullable=True)

    device = relationship("Device", back_populates="readings")

    __table_args__ = (
        Index("ix_device_timestamp", "device_id", "timestamp"),
    )

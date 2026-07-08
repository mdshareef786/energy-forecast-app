from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.database import Base


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    devices = relationship("Device", back_populates="building", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    device_type = Column(String, nullable=True)  # HVAC, lighting, server, etc.
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    rated_capacity_kw = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    building = relationship("Building", back_populates="devices")
    readings = relationship("EnergyReading", back_populates="device", cascade="all, delete-orphan")

import enum

from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, Enum, JSON, func
from sqlalchemy.orm import relationship

from app.db.database import Base


class ForecastHorizon(str, enum.Enum):
    HOUR_24 = "24h"
    DAY_7 = "7d"
    DAY_30 = "30d"


class ForecastModelType(str, enum.Enum):
    PROPHET = "prophet"
    ARIMA = "arima"
    REGRESSION = "regression"


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    model_type = Column(Enum(ForecastModelType), nullable=False)
    horizon = Column(Enum(ForecastHorizon), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    predictions = Column(JSON, nullable=False)  # list of {timestamp, predicted, lower, upper}

    device = relationship("Device")


class AnomalySeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    energy_kwh = Column(Float, nullable=False)
    z_score = Column(Float, nullable=True)
    method = Column(String, default="z_score")  # z_score | isolation_forest
    severity = Column(Enum(AnomalySeverity), default=AnomalySeverity.LOW)
    reason = Column(String, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    category = Column(String, nullable=False)  # load_balancing | scheduling | shutdown | off_peak
    message = Column(String, nullable=False)
    estimated_savings_kwh = Column(Float, nullable=True)
    priority = Column(String, default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device")
    building = relationship("Building")


class SimulationScenario(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    name = Column(String, nullable=False)
    scenario_type = Column(String, nullable=False)  # occupancy | temperature | shutdown | peak_reduction
    parameters = Column(JSON, nullable=False)
    baseline_kwh = Column(Float, nullable=False)
    projected_kwh = Column(Float, nullable=False)
    savings_kwh = Column(Float, nullable=False)
    savings_percent = Column(Float, nullable=False)
    estimated_cost_impact = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    building = relationship("Building")

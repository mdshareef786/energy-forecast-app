from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict

from app.models.ml_results import ForecastHorizon, ForecastModelType, AnomalySeverity


class ForecastRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    device_id: int
    horizon: ForecastHorizon = ForecastHorizon.DAY_7
    model_type: ForecastModelType = ForecastModelType.PROPHET


class ForecastPoint(BaseModel):
    timestamp: datetime
    predicted: float
    lower: Optional[float] = None
    upper: Optional[float] = None


class ForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    device_id: int
    model_type: ForecastModelType
    horizon: ForecastHorizon
    generated_at: datetime
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    predictions: List[Dict[str, Any]]


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_id: int
    timestamp: datetime
    energy_kwh: float
    z_score: Optional[float] = None
    method: str
    severity: AnomalySeverity
    reason: Optional[str] = None


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_id: Optional[int] = None
    building_id: Optional[int] = None
    category: str
    message: str
    estimated_savings_kwh: Optional[float] = None
    priority: str


class SimulationRequest(BaseModel):
    building_id: int
    name: str
    scenario_type: str  # occupancy | temperature | shutdown | peak_reduction
    parameters: Dict[str, Any]


class SimulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    building_id: int
    name: str
    scenario_type: str
    parameters: Dict[str, Any]
    baseline_kwh: float
    projected_kwh: float
    savings_kwh: float
    savings_percent: float
    estimated_cost_impact: Optional[float] = None

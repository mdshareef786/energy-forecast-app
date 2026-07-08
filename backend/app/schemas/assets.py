from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BuildingCreate(BaseModel):
    name: str
    location: Optional[str] = None


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    location: Optional[str] = None


class DeviceCreate(BaseModel):
    name: str
    device_type: Optional[str] = None
    building_id: int
    rated_capacity_kw: Optional[float] = None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    device_type: Optional[str] = None
    building_id: int
    rated_capacity_kw: Optional[float] = None


class EnergyReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_id: int
    timestamp: datetime
    energy_kwh: float
    temperature_c: Optional[float] = None

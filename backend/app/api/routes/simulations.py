from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.reading import EnergyReading
from app.models.asset import Device, Building
from app.models.ml_results import SimulationScenario
from app.models.user import User, UserRole
from app.schemas.ml import SimulationRequest, SimulationOut
from app.core.security import get_current_user, require_role
from app.ml.simulation import simulate_scenario

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("/run", response_model=SimulationOut)
def run_simulation(
    payload: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
):
    building = db.query(Building).filter(Building.id == payload.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    device_ids = [d.id for d in db.query(Device).filter(Device.building_id == payload.building_id).all()]
    if not device_ids:
        raise HTTPException(status_code=400, detail="Building has no devices")

    readings = (
        db.query(EnergyReading)
        .filter(EnergyReading.device_id.in_(device_ids))
        .all()
    )
    if not readings:
        raise HTTPException(status_code=400, detail="No energy readings available for this building")

    # Use average daily consumption across the building as the baseline
    total_kwh = sum(r.energy_kwh for r in readings)
    days = max(1, (max(r.timestamp for r in readings) - min(r.timestamp for r in readings)).days or 1)
    baseline_daily_kwh = total_kwh / days

    try:
        result = simulate_scenario(baseline_daily_kwh, payload.scenario_type, payload.parameters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    sim = SimulationScenario(
        building_id=payload.building_id,
        name=payload.name,
        scenario_type=payload.scenario_type,
        parameters=payload.parameters,
        **result,
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return sim


@router.get("/building/{building_id}", response_model=List[SimulationOut])
def get_simulations_for_building(building_id: int, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    return (
        db.query(SimulationScenario)
        .filter(SimulationScenario.building_id == building_id)
        .order_by(SimulationScenario.created_at.desc())
        .all()
    )

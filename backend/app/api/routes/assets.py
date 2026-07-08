from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.asset import Building, Device
from app.models.user import User, UserRole
from app.schemas.assets import BuildingCreate, BuildingOut, DeviceCreate, DeviceOut
from app.core.security import get_current_user, require_role

router = APIRouter(prefix="/api", tags=["assets"])


@router.post("/buildings", response_model=BuildingOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
def create_building(payload: BuildingCreate, db: Session = Depends(get_db)):
    building = Building(**payload.model_dump())
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


@router.get("/buildings", response_model=List[BuildingOut])
def list_buildings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Building).all()


@router.post("/devices", response_model=DeviceOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    building = db.query(Building).filter(Building.id == payload.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/devices", response_model=List[DeviceOut])
def list_devices(building_id: int | None = None, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    query = db.query(Device)
    if building_id:
        query = query.filter(Device.building_id == building_id)
    return query.all()

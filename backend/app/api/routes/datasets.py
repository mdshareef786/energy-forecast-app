import os
import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.dataset import Dataset, DatasetStatus
from app.models.asset import Building, Device
from app.models.reading import EnergyReading
from app.models.user import User, UserRole
from app.core.security import get_current_user, require_role

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "uploads")
os.makedirs(STORAGE_DIR, exist_ok=True)

REQUIRED_COLUMNS = {"timestamp", "device_id", "energy_kwh"}


@router.post("/upload", dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.ANALYST))])
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    stored_path = os.path.join(STORAGE_DIR, stored_name)

    contents = await file.read()
    with open(stored_path, "wb") as f:
        f.write(contents)

    dataset = Dataset(filename=file.filename, stored_path=stored_path, status=DatasetStatus.UPLOADED)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    try:
        df = pd.read_csv(stored_path)
    except Exception as exc:
        dataset.status = DatasetStatus.INVALID
        dataset.validation_notes = f"Could not parse CSV: {exc}"
        db.commit()
        raise HTTPException(status_code=400, detail=dataset.validation_notes)

    df.columns = [c.strip().lower() for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        dataset.status = DatasetStatus.INVALID
        dataset.validation_notes = f"Missing required columns: {sorted(missing)}"
        db.commit()
        raise HTTPException(status_code=400, detail=dataset.validation_notes)

    # Edge case: parse timestamps, drop unparsable rows
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["timestamp", "energy_kwh"])
    dropped_missing = before - len(df)

    # Edge case: invalid/negative energy values
    invalid_energy = df[df["energy_kwh"] < 0]
    df = df[df["energy_kwh"] >= 0]

    # Edge case: sparse data warning
    notes = []
    if dropped_missing:
        notes.append(f"Dropped {dropped_missing} rows with missing/invalid timestamp or energy value")
    if len(invalid_energy):
        notes.append(f"Dropped {len(invalid_energy)} rows with negative energy readings")
    if len(df) < 24:
        notes.append("Warning: dataset has very sparse data (<24 readings)")

    # Build lookup tables once: by numeric ID and by device name (case-insensitive),
    # since real-world exports commonly use a device's name rather than its DB id.
    all_devices = db.query(Device).all()
    devices_by_id = {d.id: d for d in all_devices}
    devices_by_name = {d.name.strip().lower(): d for d in all_devices}

    def resolve_device(raw_value):
        if pd.isna(raw_value):
            return None
        # Try numeric ID first
        try:
            return devices_by_id.get(int(raw_value))
        except (ValueError, TypeError):
            pass
        # Fall back to matching by device name
        return devices_by_name.get(str(raw_value).strip().lower())

    inserted = 0
    unknown_devices = set()
    for _, row in df.iterrows():
        device = resolve_device(row["device_id"])
        if not device:
            unknown_devices.add(str(row["device_id"]))
            continue
        reading = EnergyReading(
            device_id=device.id,
            timestamp=row["timestamp"].to_pydatetime(),
            energy_kwh=float(row["energy_kwh"]),
            temperature_c=float(row["temperature_c"]) if "temperature_c" in df.columns and pd.notna(row.get("temperature_c")) else None,
        )
        db.add(reading)
        inserted += 1

    if unknown_devices:
        notes.append(f"Skipped rows referencing unknown device_id(s): {sorted(unknown_devices)}")

    dataset.row_count = inserted
    dataset.status = DatasetStatus.PROCESSED if inserted > 0 else DatasetStatus.INVALID
    dataset.validation_notes = "; ".join(notes) if notes else "OK"
    db.commit()
    db.refresh(dataset)

    return {
        "dataset_id": dataset.id,
        "status": dataset.status,
        "rows_inserted": inserted,
        "notes": dataset.validation_notes,
    }


@router.get("")
def list_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Dataset).order_by(Dataset.created_at.desc()).all()

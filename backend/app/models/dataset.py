import enum

from sqlalchemy import Column, Integer, String, DateTime, Enum, func

from app.db.database import Base


class DatasetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    INVALID = "invalid"
    PROCESSED = "processed"


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    uploaded_by = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)
    status = Column(Enum(DatasetStatus), default=DatasetStatus.UPLOADED)
    validation_notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base


def generate_uuid():
    return str(uuid.uuid4())


class Sheet(Base):
    __tablename__ = "sheets"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    name = Column(String, nullable=False)
    spreadsheet_id = Column(String, nullable=False)
    credentials_id = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_backup = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    # Отношения
    backups = relationship("Backup", back_populates="sheet", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="sheet", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Sheet(id={self.id}, name={self.name}, spreadsheet_id={self.spreadsheet_id})>" 
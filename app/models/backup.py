import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.base_class import Base


def generate_uuid():
    return str(uuid.uuid4())


class Backup(Base):
    __tablename__ = "backups"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    sheet_id = Column(String, ForeignKey("sheets.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    storage_type = Column(String, nullable=False, default="local")
    storage_params = Column(JSON, nullable=True)
    storage_results = Column(JSON, nullable=True)
    backup_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)

    # Отношения
    sheet = relationship("Sheet", back_populates="backups")

    def __repr__(self):
        return f"<Backup(id={self.id}, sheet_id={self.sheet_id}, status={self.status})>" 
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import Base


def generate_uuid():
    return str(uuid.uuid4())


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    sheet_id = Column(String, ForeignKey("sheets.id"), nullable=False)
    schedule_type = Column(String, nullable=False)  # "interval" или "cron"
    schedule_config = Column(JSON, nullable=False)
    storage_type = Column(String, nullable=False, default="local")
    storage_params = Column(JSON, nullable=True)  # Параметры для хранилища (webhook_url, folder_id и т.д.)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    # Отношения
    sheet = relationship("Sheet", back_populates="schedules") 
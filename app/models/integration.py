from sqlalchemy import Column, Integer, String, JSON, Text
from app.db.base_class import Base

class Integration(Base):
    """
    Модель для хранения настроек интеграций
    """
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), index=True, nullable=False, comment="Тип интеграции (например, 'bitrix')")
    name = Column(String(100), nullable=False, comment="Название интеграции")
    settings = Column(JSON, nullable=False, comment="Настройки интеграции в формате JSON")
    description = Column(Text, nullable=True, comment="Описание интеграции")

    def __repr__(self):
        return f"<Integration {self.type}:{self.name}>" 
from typing import Any
from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """
    Базовый класс для всех моделей SQLAlchemy
    """
    id: Any
    __name__: str
    
    # Генерирует __tablename__ автоматически
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower() 
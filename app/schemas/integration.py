from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class IntegrationBase(BaseModel):
    """Базовая схема для интеграций"""
    type: str
    name: str
    description: Optional[str] = None


class Integration(IntegrationBase):
    """Схема для интеграции с дополнительными полями"""
    id: int
    settings: Dict[str, Any]
    
    class Config:
        from_attributes = True 
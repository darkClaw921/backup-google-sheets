from typing import Dict, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ScheduleBase(BaseModel):
    """Базовая схема для расписания"""
    sheet_id: str
    schedule_type: Literal["interval", "cron"]
    schedule_config: Dict[str, Any]
    storage_type: str = "local"
    storage_params: Optional[Dict[str, Any]] = None
    is_active: bool = True


class ScheduleCreate(ScheduleBase):
    """Схема для создания расписания"""
    pass


class ScheduleUpdate(BaseModel):
    """Схема для обновления расписания"""
    sheet_id: Optional[str] = None
    schedule_type: Optional[Literal["interval", "cron"]] = None
    schedule_config: Optional[Dict[str, Any]] = None
    storage_type: Optional[str] = None
    storage_params: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ScheduleResponse(ScheduleBase):
    """Схема для ответа с данными расписания"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "sheet_id": "456e7890-e89b-12d3-a456-426614174001",
                "schedule_type": "interval",
                "schedule_config": {
                    "interval": {
                        "hours": 12
                    }
                },
                "storage_type": "local",
                "storage_params": {
                    "webhook_url": "https://domain.bitrix24.ru/rest/1/your-webhook-code/",
                    "folder_id": "12345"
                },
                "is_active": True,
                "created_at": "2023-01-01T12:00:00",
                "updated_at": "2023-01-02T14:30:00"
            }
        } 
from typing import Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

class BackupSchedule(BaseModel):
    """
    Модель для хранения расписания резервного копирования
    """
    id: str
    sheet_id: str
    storage_type: str = "local"  # local, s3, gdrive, bitrix, etc.
    storage_params: Optional[Dict[str, Any]] = None  # Параметры для хранилища (webhook_url, folder_id, etc.)
    schedule_type: str = "interval"  # interval, cron
    schedule_config: Dict[str, Any]
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "schedule_12345",
                "sheet_id": "sheet_12345",
                "storage_type": "local",
                "storage_params": None,
                "schedule_type": "interval",
                "schedule_config": {
                    "interval": {
                        "hours": 6
                    }
                },
                "is_active": True,
                "created_at": "2023-10-10T12:30:00",
                "updated_at": "2023-10-10T12:30:00"
            }
        } 
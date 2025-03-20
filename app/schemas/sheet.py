from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class SheetBase(BaseModel):
    """Базовая схема для таблицы"""
    name: str
    spreadsheet_id: str

class SheetCreate(SheetBase):
    """Схема для создания таблицы"""
    credentials_id: Optional[str] = None

class SheetUpdate(BaseModel):
    """Схема для обновления таблицы"""
    name: Optional[str] = None
    spreadsheet_id: Optional[str] = None
    credentials_id: Optional[str] = None

class SheetResponse(SheetBase):
    """Схема для ответа с данными таблицы"""
    id: str
    credentials_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    last_backup: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Финансовый отчет",
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "credentials_id": "google_creds_1",
                "last_synced_at": "2023-01-01T10:00:00",
                "last_backup": "2023-01-01T12:30:00",
                "created_at": "2023-01-01T09:00:00",
                "updated_at": "2023-01-01T15:45:00"
            }
        } 
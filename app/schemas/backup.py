from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class BackupBase(BaseModel):
    """Базовая схема для бэкапа"""
    sheet_id: str
    storage_type: str = "local"
    status: str = "processing"
    
class BackupCreate(BackupBase):
    """Схема для создания бэкапа"""
    storage_path: str
    size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class BackupUpdate(BaseModel):
    """Схема для обновления бэкапа"""
    status: Optional[str] = None
    size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class BackupInDB(BackupBase):
    """Схема бэкапа в БД"""
    id: str
    storage_path: str
    size: Optional[int] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class BackupOut(BackupInDB):
    """Схема бэкапа для вывода"""
    pass

class BackupStats(BaseModel):
    """Статистика резервных копий для таблицы"""
    total_backups: int
    total_size: int
    successful_backups: int
    failed_backups: int
    average_size: float
    first_backup_date: Optional[datetime] = None
    last_backup_date: Optional[datetime] = None

class BackupResponse(BackupBase):
    """Схема для ответа с данными бэкапа"""
    id: str
    filename: str
    file_path: str
    size: int
    backup_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "sheet_id": "456e7890-e89b-12d3-a456-426614174001",
                "filename": "MyTable_20230101_120000.json",
                "file_path": "backups/MyTable_20230101_120000.json",
                "size": 1024,
                "storage_type": "local",
                "status": "completed",
                "backup_metadata": {
                    "sheets": 2,
                    "rows": 100,
                    "columns": 15
                },
                "created_at": "2023-01-01T12:00:00"
            }
        } 
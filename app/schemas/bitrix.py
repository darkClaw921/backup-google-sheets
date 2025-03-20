from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class BitrixSettings(BaseModel):
    """
    Схема для настроек интеграции с Bitrix24
    """
    webhook_url: str = Field(..., description="URL вебхука Bitrix24")
    folder_id: Optional[str] = Field(None, description="ID папки в Битрикс24 (опционально)")
    base_path: str = Field("backup_google_sheets", description="Базовый путь для хранения файлов")


class BitrixTestConnection(BaseModel):
    """
    Схема для проверки соединения с Bitrix24
    """
    webhook_url: str = Field(..., description="URL вебхука Bitrix24 для проверки")


class BitrixConnectionResponse(BaseModel):
    """
    Схема ответа на проверку соединения с Bitrix24
    """
    success: bool = Field(..., description="Успешность соединения")
    error: Optional[str] = Field(None, description="Сообщение об ошибке, если есть")


class BitrixFolder(BaseModel):
    """
    Схема папки в Bitrix24
    """
    ID: str = Field(..., description="ID папки")
    NAME: str = Field(..., description="Название папки")
    PATH: Optional[str] = Field(None, description="Путь к папке")
    PARENT_ID: Optional[str] = Field(None, description="ID родительской папки")
    CREATED_TIME: Optional[str] = Field(None, description="Дата создания")
    UPDATED_TIME: Optional[str] = Field(None, description="Дата изменения")
    
    class Config:
        """Конфигурация схемы"""
        from_attributes = True
        json_schema_extra = {"example": {"ID": "123", "NAME": "backup_folder", "PATH": "/Drive/", "PARENT_ID": "1"}} 
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения и файла .env
    """
    APP_NAME: str = "Backup Google Sheets"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    
    # Пути к файлам
    CREDENTIALS_PATH: Path = Path("credentials/service-account.json")
    
    # Настройки Google API
    GOOGLE_API_SCOPES: str = "https://www.googleapis.com/auth/spreadsheets.readonly"
    
    # База данных
    DATABASE_URL: str = "sqlite:///./data/app.db"
    
    # Настройки приложения
    PROJECT_NAME: str = "Backup Google Sheets"
    PROJECT_DESCRIPTION: str = "Сервис для резервного копирования Google Sheets"
    VERSION: str = "0.1.0"
    
    # Настройки Битрикс24
    BITRIX24_WEBHOOK_URL: Optional[str] = None
    BITRIX24_DEFAULT_FOLDER_ID: Optional[str] = None
    
    # Настройки кодировки
    ENCODING: str = "utf-8"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True


# Создаем глобальный экземпляр настроек
settings = Settings() 
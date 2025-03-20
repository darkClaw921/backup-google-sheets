from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db
from app.schemas.bitrix import BitrixSettings, BitrixTestConnection, BitrixConnectionResponse, BitrixFolder
from app.schemas.integration import Integration
from app.services.integration_service import IntegrationService
from app.models.integration import Integration as IntegrationModel

router = APIRouter()

@router.get("/all", response_model=List[Integration])
def get_all_integrations(db: Session = Depends(get_db)):
    """
    Получить список всех интеграций
    """
    integrations = db.query(IntegrationModel).all()
    return integrations

@router.get("/bitrix", response_model=BitrixSettings)
def get_bitrix_settings(db: Session = Depends(get_db)):
    """
    Получить настройки интеграции с Bitrix24
    """
    settings = IntegrationService.get_bitrix_settings(db)
    
    if not settings:
        return {
            "webhook_url": "",
            "folder_id": None,
            "base_path": "backup_google_sheets"
        }
        
    return settings

@router.post("/bitrix", response_model=BitrixSettings)
def save_bitrix_settings(settings: BitrixSettings, db: Session = Depends(get_db)):
    """
    Сохранить настройки интеграции с Bitrix24
    """
    integration = IntegrationService.save_bitrix_settings(db, settings.dict())
    return integration.settings

@router.post("/bitrix/test", response_model=BitrixConnectionResponse)
def test_bitrix_connection(test_data: BitrixTestConnection):
    """
    Проверить соединение с Bitrix24
    """
    result = IntegrationService.test_bitrix_connection(test_data.webhook_url)
    return result

@router.get("/bitrix/folders", response_model=List[BitrixFolder])
def get_bitrix_folders(db: Session = Depends(get_db)):
    """
    Получить список папок из Bitrix24
    """
    folders = IntegrationService.get_bitrix_folders(db)
    return folders

@router.post("/bitrix/folders", response_model=List[BitrixFolder])
def get_bitrix_folders_by_webhook(data: BitrixTestConnection, db: Session = Depends(get_db)):
    """
    Получить список папок из Bitrix24 по указанному webhook_url
    
    Используется при создании расписания, когда нужно получить папки
    без сохранения настроек в БД
    """
    from app.services.storage.bitrix_disk_storage import BitrixDiskStorage
    
    try:
        # Создаем экземпляр хранилища
        storage = BitrixDiskStorage(
            webhook_url=data.webhook_url,
            base_path="backup_google_sheets"
        )
        
        # Получаем список папок
        folders = storage.get_folder_list()
        return folders
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 
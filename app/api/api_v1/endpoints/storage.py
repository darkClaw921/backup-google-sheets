from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.storage.bitrix_disk_storage import BitrixDiskStorage

router = APIRouter()

class BitrixWebhookRequest(BaseModel):
    webhook_url: str
    folder_id: Optional[str] = None

class BitrixFolder(BaseModel):
    id: str
    name: str
    storage_name: str
    storage_id: str
    created_at: Optional[str] = None

@router.post("/bitrix/folders", response_model=List[BitrixFolder])
async def get_bitrix_folders(request: BitrixWebhookRequest):
    """
    Получение списка папок в Битрикс24 Диск
    """
    try:
        # Создаем временный экземпляр хранилища для получения списка папок
        storage = BitrixDiskStorage(
            webhook_url=request.webhook_url,
            folder_id=request.folder_id
        )
        
        # Получаем список папок
        folders = storage.get_folder_list()
        
        return folders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении списка папок: {str(e)}"
        ) 
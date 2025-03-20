from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Response, Depends
from fastapi.responses import FileResponse
import io
import os
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.schemas.backup import BackupOut, BackupCreate, BackupUpdate, BackupStats, BackupResponse
from app.services.backup_service import backup_sheet, delete_backup
from app.models.backup import Backup
from app.models.sheet import Sheet
from app.api.deps import get_db

router = APIRouter()

@router.post("/", response_model=BackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    sheet_id: str, 
    storage_type: str = "local",
    storage_params: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """
    Создание резервной копии таблицы
    
    - **sheet_id**: ID таблицы
    - **storage_type**: Тип хранилища (local или bitrix)
    - **storage_params**: Параметры хранилища (опционально, для bitrix можно указать folder_id)
    """
    # Проверяем существование таблицы
    sheet = db.query(Sheet).filter(Sheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Таблица не найдена"
        )
    
    # Создаем резервную копию
    try:
        backup_result = backup_sheet(
            sheet.spreadsheet_id,
            sheet.name,
            storage_type,
            storage_params=storage_params,
            db=db
        )
        
        if not backup_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось создать резервную копию"
            )
        
        # Отладочный вывод
        logger = logging.getLogger(__name__)
        logger.info(f"Результат создания бэкапа: {backup_result.__dict__}")
        
        # Сохраняем в БД
        backup = Backup(
            sheet_id=sheet_id,
            filename=backup_result.filename,
            file_path=backup_result.file_path,
            size=backup_result.size,
            status=backup_result.status,
            storage_type=backup_result.storage_type,
            backup_metadata=backup_result.backup_metadata,
            created_at=datetime.utcnow()
        )
        
        db.add(backup)
        db.commit()
        db.refresh(backup)
        
        # Обновляем время последнего бэкапа для таблицы
        sheet.last_backup = backup.created_at
        db.commit()
        
        return backup
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании бэкапа: {str(e)}"
        )

@router.get("/", response_model=List[BackupResponse])
async def get_backups(
    sheet_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получение списка всех резервных копий
    """
    query = db.query(Backup)
    
    if sheet_id:
        # Фильтруем бэкапы по ID таблицы
        query = query.filter(Backup.sheet_id == sheet_id)
    
    return query.all()

@router.get("/{backup_id}", response_model=BackupResponse)
async def get_backup_info(
    backup_id: str,
    db: Session = Depends(get_db)
):
    """
    Получение информации о резервной копии
    """
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резервная копия не найдена"
        )
    
    return backup

@router.delete("/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup_endpoint(
    backup_id: str,
    db: Session = Depends(get_db)
):
    """
    Удаление резервной копии
    """
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резервная копия не найдена"
        )
    
    # Удаляем файл с диска
    try:
        if os.path.exists(backup.file_path):
            os.remove(backup.file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось удалить файл резервной копии: {str(e)}"
        )
    
    # Удаляем из БД
    db.delete(backup)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: str,
    db: Session = Depends(get_db)
):
    """
    Скачивание файла резервной копии
    """
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резервная копия не найдена"
        )
    
    # Проверяем тип хранилища и обрабатываем соответственно
    if backup.storage_type == "bitrix":
        from app.services.storage.bitrix_disk_storage import BitrixDiskStorage
        from app.services.integration_service import IntegrationService
        
        # Получаем настройки Битрикс24
        bitrix_settings = IntegrationService.get_bitrix_settings(db)
        if not bitrix_settings or not bitrix_settings.get("webhook_url"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не настроена интеграция с Битрикс24"
            )
        
        # Создаем экземпляр хранилища Битрикс24
        storage = BitrixDiskStorage(
            webhook_url=bitrix_settings["webhook_url"],
            folder_id=bitrix_settings.get("folder_id"),
            base_path=bitrix_settings.get("base_path", "backup_google_sheets")
        )
        
        # Получаем ID файла из пути (в этом случае file_path содержит ID файла)
        file_id = backup.file_path
        
        # Получаем файл из Битрикс24
        file_data = storage.get(file_id)
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Файл бэкапа не найден на диске"
            )
        
        # Создаем временный файл для отправки пользователю
        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), backup.filename)
        
        with open(temp_path, 'wb') as f:
            f.write(file_data.read())
        
        # Возвращаем файл клиенту
        return FileResponse(
            path=temp_path,
            filename=backup.filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            background=None  # Явно отключаем фоновую обработку, чтобы файл не был удален до завершения ответа
        )
    else:
        # Для локального хранилища - стандартный путь
        # Проверяем существование файла
        if not os.path.exists(backup.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Файл бэкапа не найден на диске"
            )
        
        # Возвращаем файл клиенту
        return FileResponse(
            path=backup.file_path,
            filename=backup.filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

@router.get("/stats/{sheet_id}", response_model=BackupStats)
async def get_backup_stats(
    sheet_id: str,
    db: Session = Depends(get_db)
):
    """
    Получение статистики резервных копий для таблицы
    """
    sheet = db.query(Sheet).filter(Sheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Таблица не найдена"
        )
    
    # Получаем все бэкапы для таблицы
    backups = db.query(Backup).filter(Backup.sheet_id == sheet_id).all()
    
    if not backups:
        # Если бэкапов нет, возвращаем пустую статистику
        return {
            "total_backups": 0,
            "total_size": 0,
            "successful_backups": 0,
            "failed_backups": 0,
            "average_size": 0,
            "first_backup_date": None,
            "last_backup_date": None
        }
    
    # Вычисляем статистику
    total_backups = len(backups)
    successful_backups = sum(1 for backup in backups if backup.status == "completed")
    failed_backups = total_backups - successful_backups
    
    total_size = sum(backup.size for backup in backups if backup.size is not None)
    average_size = total_size / total_backups if total_backups > 0 else 0
    
    # Сортируем по дате создания
    sorted_backups = sorted(backups, key=lambda x: x.created_at)
    first_backup_date = sorted_backups[0].created_at if sorted_backups else None
    last_backup_date = sorted_backups[-1].created_at if sorted_backups else None
    
    return {
        "total_backups": total_backups,
        "total_size": total_size,
        "successful_backups": successful_backups,
        "failed_backups": failed_backups,
        "average_size": average_size,
        "first_backup_date": first_backup_date,
        "last_backup_date": last_backup_date
    } 
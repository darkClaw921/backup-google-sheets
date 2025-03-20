import os
import json
import logging
import requests
import io
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.backup import Backup
from app.services.google_service import google_service
from app.services.storage import get_storage
from app.services.backup_service import backup_sheet

logger = logging.getLogger(__name__)

def get_spreadsheet_data(spreadsheet_id: str):
    """
    Получает данные из Google Sheets, используя сервис
    """
    return google_service.get_sheet_values_by_sheets(spreadsheet_id)

def create_backup(
    sheet_id: str, 
    spreadsheet_id: str, 
    sheet_name: str, 
    storage_configs: List[Dict[str, Any]],
    db: Session
):
    """
    Создает бэкап таблицы Google Sheets
    
    Args:
        sheet_id: ID таблицы в базе данных
        spreadsheet_id: ID таблицы в Google Sheets
        sheet_name: Название таблицы
        storage_configs: Список конфигураций хранилищ
        db: Сессия базы данных
    
    Returns:
        Созданный объект бэкапа
    """
    try:
        logger.info(f"Создание резервной копии для таблицы {sheet_name} (ID: {spreadsheet_id})")
        
        # Создаем бэкап через сервис
        backup_result = backup_sheet(
            sheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            storage_configs=storage_configs,
            db=db
        )
        
        if not backup_result:
            raise Exception("Не удалось создать резервную копию")
        
        # Создание записи о бэкапе в БД
        backup = Backup(
            sheet_id=sheet_id,
            filename=backup_result.filename,
            file_path=backup_result.file_path,
            size=backup_result.size,
            status=backup_result.status,
            storage_type=backup_result.storage_type,
            storage_params=backup_result.storage_params,
            storage_results=backup_result.storage_results,
            backup_metadata=backup_result.backup_metadata,
            created_at=datetime.utcnow()
        )
        
        db.add(backup)
        db.commit()
        db.refresh(backup)
        
        logger.info(f"Бэкап успешно создан: {backup.id} в {len(backup_result.storage_results)} хранилищах")
        return backup
    
    except Exception as e:
        logger.error(f"Ошибка при создании бэкапа для таблицы {sheet_name}: {str(e)}")
        raise 
import os
import json
import logging
import requests
import io
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.backup import Backup
from app.services.google_service import google_service
from app.services.storage import get_storage

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
    storage_type: str, 
    db: Session,
    storage_params: Optional[Dict[str, Any]] = None
):
    """
    Создает бэкап таблицы Google Sheets
    
    Args:
        sheet_id: ID таблицы в базе данных
        spreadsheet_id: ID таблицы в Google Sheets
        sheet_name: Название таблицы
        storage_type: Тип хранилища для сохранения
        db: Сессия базы данных
        storage_params: Параметры хранилища (например, webhook_url и folder_id для Битрикс24)
    
    Returns:
        Созданный объект бэкапа
    """
    try:
        logger.info(f"Создание резервной копии для таблицы {sheet_name} (ID: {spreadsheet_id})")
        
        # Прямой URL для экспорта таблицы в формате XLSX
        export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
        
        # Делаем запрос с использованием аутентификации Google Service
        response = requests.get(
            export_url, 
            headers={"Authorization": f"Bearer {google_service.credentials.token}"}
        )
        
        # Проверяем успешность запроса
        if response.status_code != 200:
            logger.error(f"Не удалось экспортировать таблицу {spreadsheet_id}. Код ответа: {response.status_code}")
            raise Exception(f"Ошибка экспорта: код {response.status_code}")
        
        # Получаем бинарные данные файла
        file_data = io.BytesIO(response.content)
        
        # Формирование имени файла бэкапа
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{sheet_name.replace(' ', '_')}_{timestamp}.xlsx"
        
        # Инициализируем хранилище в зависимости от типа
        storage_instance = None
        
        if storage_type == "local":
            # Для локального хранилища используем стандартные параметры
            storage_instance = get_storage(storage_type)
        elif storage_type == "bitrix":
            # Для Битрикс24 требуются специальные параметры
            logger.info(f"Обработка хранилища Битрикс24, параметры: {storage_params}")
            
            # Проверяем наличие ID интеграции в параметрах
            if db and storage_params and storage_params.get("integration_id") is not None:
                from app.services.integration_service import IntegrationService
                
                integration_id = storage_params.get("integration_id")
                logger.info(f"Получение интеграции по ID: {integration_id}")
                
                # Получаем настройки из базы данных по ID интеграции
                integration = IntegrationService.get_integration_by_id(db, integration_id)
                if not integration:
                    logger.error(f"Не найдена интеграция Битрикс24 с ID {integration_id}")
                    raise Exception(f"Не найдена интеграция Битрикс24 с ID {integration_id}")
                
                logger.info(f"Найдена интеграция: {integration}, тип: {integration.type}")
                
                if integration.type != "bitrix":
                    logger.error(f"Найденная интеграция с ID {integration_id} имеет неверный тип: {integration.type}")
                    raise Exception(f"Найденная интеграция с ID {integration_id} имеет неверный тип: {integration.type}")
                
                logger.info(f"Использую настройки из интеграции: {integration.settings}")
                storage_params = integration.settings
            # Если есть webhook_url в storage_params, используем его напрямую
            elif storage_params and storage_params.get("webhook_url"):
                logger.info(f"Использую прямые параметры для Битрикс24: {storage_params}")
            # Пытаемся получить настройки из базы данных по типу
            elif db:
                from app.services.integration_service import IntegrationService
                
                logger.info("Получение настроек Битрикс24 из базы данных")
                bitrix_settings = IntegrationService.get_bitrix_settings(db)
                if not bitrix_settings:
                    logger.error("Не настроена интеграция с Битрикс24")
                    raise Exception("Не настроена интеграция с Битрикс24")
                
                logger.info(f"Использую настройки Битрикс24 из базы данных: {bitrix_settings}")
                storage_params = bitrix_settings
            else:
                logger.error("Не указаны параметры для хранилища Битрикс24 и нет доступа к базе данных")
                raise Exception("Не указаны параметры для хранилища Битрикс24 и нет доступа к базе данных")
            
            # Проверяем наличие обязательного webhook_url
            if not storage_params or "webhook_url" not in storage_params:
                logger.error("Не указаны параметры webhook_url для хранилища Битрикс24")
                raise Exception("Не указаны параметры webhook_url для хранилища Битрикс24")
            
            # Создаем экземпляр хранилища Битрикс24 с параметрами
            storage_instance = get_storage(
                storage_type, 
                webhook_url=storage_params["webhook_url"],
                folder_id=storage_params.get("folder_id"),
                base_path=storage_params.get("base_path", "backup_google_sheets")
            )
        else:
            # Для других типов хранилищ
            storage_instance = get_storage(storage_type, **(storage_params or {}))
        
        # Сохраняем файл в выбранное хранилище
        file_path = storage_instance.save(file_data, filename)
        
        if not file_path:
            logger.error(f"Не удалось сохранить файл в хранилище типа {storage_type}")
            raise Exception(f"Не удалось сохранить файл в хранилище типа {storage_type}")
        
        # Получаем информацию о файле из хранилища
        file_info = None
        try:
            file_info = storage_instance.get_file_info(file_path)
        except Exception as e:
            logger.warning(f"Не удалось получить информацию о файле: {str(e)}")
            
        # Размер файла
        file_size = file_info.get("size", 0) if file_info else 0
        
        # Пытаемся извлечь метаданные из Excel-файла (кол-во листов и др.)
        metadata = None
        try:
            import pandas as pd
            # Сбрасываем указатель в начало файла
            file_data.seek(0)
            
            with pd.ExcelFile(file_data) as xls:
                metadata = {
                    "sheets": xls.sheet_names,
                    "sheet_count": len(xls.sheet_names)
                }
        except Exception as e:
            logger.warning(f"Не удалось прочитать метаданные из файла: {str(e)}")
        
        # Создание записи о бэкапе в БД
        backup = Backup(
            sheet_id=sheet_id,
            filename=filename,
            file_path=file_path,
            size=file_size,
            status="completed",
            storage_type=storage_type,
            storage_params=storage_params,
            backup_metadata=metadata,
            created_at=datetime.utcnow()
        )
        
        db.add(backup)
        db.commit()
        db.refresh(backup)
        
        logger.info(f"Бэкап успешно создан: {backup.id} в хранилище типа {storage_type}")
        return backup
    
    except Exception as e:
        logger.error(f"Ошибка при создании бэкапа для таблицы {sheet_name}: {str(e)}")
        raise 
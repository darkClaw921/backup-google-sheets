import io
import json
import logging
import uuid
import requests
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

from app.services.google_service import google_service
from app.services.storage import get_storage
from app.models.backup import Backup
from app.services.integration_service import IntegrationService

logger = logging.getLogger(__name__)

def backup_sheet_by_id(
    sheet_id: str, 
    sheet_name: str,
    storage_configs: List[Dict[str, Any]],
    db: Optional[Any] = None
) -> Optional[Backup]:
    """
    Создание резервной копии одной таблицы Google Sheets
    
    Args:
        sheet_id: ID таблицы Google Sheets
        sheet_name: Название таблицы
        storage_configs: Список конфигураций хранилищ в формате [{"storage_type": str, "storage_params": dict}]
        db: Сессия базы данных (для получения настроек интеграции)
        
    Returns:
        Backup или None: Информация о созданной резервной копии или None в случае ошибки
    """
    try:
        logger.info(f"Создание резервной копии для таблицы {sheet_name} (ID: {sheet_id})")
        logger.info(f"Полученные конфигурации хранилищ: {storage_configs}")
        
        # Прямой URL для экспорта таблицы в формате XLSX
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        
        # Делаем запрос с использованием аутентификации Google Service
        response = requests.get(
            export_url, 
            headers={"Authorization": f"Bearer {google_service.credentials.token}"}
        )
        
        # Проверяем успешность запроса
        if response.status_code != 200:
            logger.error(f"Не удалось экспортировать таблицу {sheet_id}. Код ответа: {response.status_code}")
            return None
        
        # Получаем бинарные данные файла
        file_data = io.BytesIO(response.content)
        
        # Генерируем имя файла с названием таблицы вместо ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Заменяем недопустимые символы в имени файла
        safe_sheet_name = sheet_name.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")
        filename = f"{safe_sheet_name}_{timestamp}.xlsx"
        
        # Результаты сохранения в разные хранилища
        storage_results = []
        
        # Сохраняем файл в каждое выбранное хранилище
        for config in storage_configs:
            storage_type = config["storage_type"]
            storage_params = config.get("storage_params", {})
            
            logger.info(f"Обработка хранилища {storage_type} с параметрами: {storage_params}")
            
            try:
                # Инициализируем хранилище в зависимости от типа
                storage_instance = None
                
                if storage_type == "local":
                    # Для локального хранилища используем стандартные параметры
                    storage_instance = get_storage(storage_type)
                    logger.info("Создан экземпляр локального хранилища")
                elif storage_type == "bitrix":
                    # Для Битрикс24 получаем настройки из интеграции, если не переданы напрямую
                    logger.info(f"Обработка хранилища Битрикс24, начальные параметры: {storage_params}")
                    
                    bitrix_params = None
                    
                    # Проверяем наличие ID интеграции в параметрах
                    if db and storage_params and storage_params.get("integration_id") is not None:
                        integration_id = storage_params.get("integration_id")
                        logger.info(f"Получение интеграции по ID: {integration_id}")
                        
                        # Получаем настройки из базы данных по ID интеграции
                        integration = IntegrationService.get_integration_by_id(db, integration_id)
                        if not integration:
                            logger.error(f"Не найдена интеграция Битрикс24 с ID {integration_id}")
                            continue
                        
                        logger.info(f"Найдена интеграция: {integration}, тип: {integration.type}")
                        
                        if integration.type != "bitrix":
                            logger.error(f"Найденная интеграция с ID {integration_id} имеет неверный тип: {integration.type}")
                            continue
                        
                        logger.info(f"Использую настройки из интеграции: {integration.settings}")
                        bitrix_params = integration.settings
                    
                    # Если есть webhook_url в storage_params, используем его напрямую
                    elif storage_params and storage_params.get("webhook_url"):
                        logger.info(f"Использую прямые параметры для Битрикс24: {storage_params}")
                        bitrix_params = storage_params
                    
                    # Пытаемся получить настройки из базы данных
                    elif db:
                        logger.info("Получение настроек Битрикс24 из базы данных")
                        bitrix_settings = IntegrationService.get_bitrix_settings(db)
                        if not bitrix_settings:
                            logger.error("Не настроена интеграция с Битрикс24")
                            continue
                        
                        logger.info(f"Использую настройки Битрикс24 из базы данных: {bitrix_settings}")
                        bitrix_params = bitrix_settings
                    else:
                        logger.error("Не указаны параметры для хранилища Битрикс24 и нет доступа к базе данных")
                        continue
                    
                    # Проверяем наличие обязательного webhook_url
                    if not bitrix_params or "webhook_url" not in bitrix_params:
                        logger.error("Не указаны параметры webhook_url для хранилища Битрикс24")
                        logger.error(f"Полученные параметры: {bitrix_params}")
                        continue
                    
                    # Создаем экземпляр хранилища Битрикс24 с параметрами
                    storage_instance = get_storage(
                        storage_type, 
                        webhook_url=bitrix_params["webhook_url"],
                        folder_id=bitrix_params.get("folder_id"),
                        base_path=bitrix_params.get("base_path", "backup_google_sheets")
                    )
                    logger.info("Создан экземпляр хранилища Битрикс24")
                else:
                    # Для других типов хранилищ
                    storage_instance = get_storage(storage_type, **(storage_params or {}))
                    logger.info(f"Создан экземпляр хранилища типа {storage_type}")
                
                # Сбрасываем указатель в начало файла перед каждым сохранением
                file_data.seek(0)
                
                # Сохраняем файл в текущее хранилище
                file_path = storage_instance.save(file_data, filename)
                
                if not file_path:
                    logger.error(f"Не удалось сохранить файл в хранилище типа {storage_type}")
                    continue
                
                # Получаем информацию о файле из хранилища
                file_info = None
                try:
                    file_info = storage_instance.get_file_info(file_path)
                except Exception as e:
                    logger.warning(f"Не удалось получить информацию о файле: {str(e)}")
                
                # Добавляем результат сохранения
                storage_results.append({
                    "storage_type": storage_type,
                    "file_path": file_path,
                    "size": file_info.get("size", 0) if file_info else 0,
                    "storage_params": storage_params
                })
                
                logger.info(f"Файл успешно сохранен в хранилище {storage_type}: {file_path}")
                
            except Exception as e:
                logger.error(f"Ошибка при сохранении в хранилище {storage_type}: {str(e)}")
                continue
        
        # Если ни одно сохранение не удалось
        if not storage_results:
            logger.error("Не удалось сохранить файл ни в одно хранилище")
            return None
        
        # Используем информацию о первом успешном сохранении для основных полей
        primary_storage = storage_results[0]
        
        # Пытаемся извлечь метаданные из Excel-файла
        metadata = {"sheet_name": sheet_name}
        try:
            # Сбрасываем указатель в начало файла
            file_data.seek(0)
            
            # Открываем Excel-файл для чтения метаданных
            with pd.ExcelFile(file_data) as xls:
                metadata["sheets"] = xls.sheet_names
                # Подсчитываем общее количество строк во всех листах
                total_rows = 0
                for sheet in metadata["sheets"]:
                    df = pd.read_excel(xls, sheet_name=sheet)
                    total_rows += len(df)
                metadata["rows_count"] = total_rows
        except Exception as e:
            logger.warning(f"Не удалось прочитать метаданные из файла: {str(e)}")
        
        # Создаем объект для возврата
        class BackupResult:
            def __init__(self, filename, file_path, size, status, storage_type, backup_metadata, storage_params=None, storage_results=None):
                self.filename = filename
                self.file_path = file_path
                self.size = size
                self.status = status
                self.storage_type = storage_type
                self.storage_params = storage_params
                self.backup_metadata = backup_metadata
                self.storage_results = storage_results
        
        backup_result = BackupResult(
            filename=filename,
            file_path=primary_storage["file_path"],
            size=primary_storage["size"],
            status="completed",
            storage_type=primary_storage["storage_type"],
            storage_params=primary_storage["storage_params"],
            backup_metadata=metadata,
            storage_results=storage_results
        )
        
        logger.info(f"Бэкап успешно создан: {filename} в {len(storage_results)} хранилищах")
        return backup_result
    
    except Exception as e:
        logger.error(f"Ошибка при создании бэкапа таблицы {sheet_id}: {str(e)}")
        return None

def get_backup(backup_id: str, storage_type: str) -> Optional[io.BytesIO]:
    """
    Получение бэкапа из хранилища по ID
    
    Args:
        backup_id: ID бэкапа
        storage_type: Тип хранилища
        
    Returns:
        BytesIO или None: Данные бэкапа или None в случае ошибки
    """
    try:
        # В реальном приложении здесь был бы запрос в БД для получения пути к файлу
        # по идентификатору бэкапа. Сейчас мы предполагаем, что backup_id - это путь к файлу
        
        # Получаем экземпляр хранилища
        storage = get_storage(storage_type)
        
        # Получаем файл из хранилища
        file_data = storage.get(backup_id)
        if not file_data:
            logger.error(f"Не удалось получить бэкап {backup_id}")
            return None
        
        # Читаем все данные в память
        buffer = io.BytesIO(file_data.read())
        
        # Закрываем файл
        file_data.close()
        
        # Перемещаем указатель в начало
        buffer.seek(0)
        
        return buffer
    
    except Exception as e:
        logger.error(f"Ошибка при получении бэкапа {backup_id}: {str(e)}")
        return None

def delete_backup(backup_id: str, storage_type: str, storage_path: str) -> bool:
    """
    Удаление бэкапа
    
    Args:
        backup_id: ID бэкапа
        storage_type: Тип хранилища
        storage_path: Путь к файлу в хранилище
        
    Returns:
        bool: True если бэкап успешно удален, иначе False
    """
    try:
        # Получаем экземпляр хранилища
        storage = get_storage(storage_type)
        
        # Удаляем файл из хранилища
        if not storage.delete(storage_path):
            logger.error(f"Не удалось удалить файл бэкапа {storage_path}")
            return False
        
        # В реальном приложении здесь был бы запрос в БД для удаления записи о бэкапе
        
        logger.info(f"Бэкап {backup_id} успешно удален")
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при удалении бэкапа {backup_id}: {str(e)}")
        return False

def backup_sheets(
    sheets: List[Dict[str, str]],
    storage_configs: List[Dict[str, Any]],
    db: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Создание резервных копий для нескольких таблиц Google Sheets
    
    Args:
        sheets: Список таблиц в формате [{"id": str, "name": str, "spreadsheet_id": str}]
        storage_configs: Список конфигураций хранилищ
        db: Сессия базы данных
        
    Returns:
        Список результатов создания бэкапов для каждой таблицы
    """
    results = []
    
    for sheet in sheets:
        try:
            sheet_id = sheet["id"]
            sheet_name = sheet.get("name", "Неизвестная таблица")
            spreadsheet_id = sheet.get("spreadsheet_id")
            
            if not spreadsheet_id:
                logger.error(f"Не указан spreadsheet_id для таблицы {sheet_id} ({sheet_name})")
                results.append({
                    "sheet_id": sheet_id,
                    "sheet_name": sheet_name,
                    "success": False,
                    "error": "Отсутствует spreadsheet_id"
                })
                continue
            
            # Создаем бэкап для текущей таблицы
            backup_result = backup_sheet_by_id(
                sheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                storage_configs=storage_configs,
                db=db
            )
            
            if backup_result:
                # Создаем запись о бэкапе в базе данных, если передана сессия
                if db is not None:
                    try:
                        from app.models.backup import Backup
                        from app.models.sheet import Sheet
                        
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
                        
                        # Обновляем время последнего бэкапа для таблицы
                        sheet_obj = db.query(Sheet).filter(Sheet.id == sheet_id).first()
                        if sheet_obj:
                            sheet_obj.last_backup = backup.created_at
                            db.commit()
                        
                        logger.info(f"Бэкап для таблицы {sheet_name} сохранен в БД: {backup.id}")
                    except Exception as e:
                        logger.error(f"Ошибка при сохранении бэкапа в БД: {str(e)}")
                
                results.append({
                    "sheet_id": sheet_id,
                    "sheet_name": sheet_name,
                    "success": True,
                    "backup_id": backup_result.filename,
                    "storage_results": backup_result.storage_results
                })
            else:
                results.append({
                    "sheet_id": sheet_id,
                    "sheet_name": sheet_name,
                    "success": False,
                    "error": "Не удалось создать бэкап"
                })
        
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа для таблицы {sheet.get('id')}: {str(e)}")
            results.append({
                "sheet_id": sheet.get("id"),
                "sheet_name": sheet.get("name", "Неизвестная таблица"),
                "success": False,
                "error": str(e)
            })
    
    return results

# Переименовываем исходную функцию в backup_sheet_by_id и алиас для обратной совместимости
backup_sheet = backup_sheet_by_id 
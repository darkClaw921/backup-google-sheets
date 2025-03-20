import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import json
import requests

from app.models.integration import Integration
from app.services.storage.bitrix_disk_storage import BitrixDiskStorage

logger = logging.getLogger(__name__)

class IntegrationService:
    """
    Сервис для работы с интеграциями
    """
    
    @staticmethod
    def get_bitrix_settings(db: Session) -> Optional[Dict[str, Any]]:
        """
        Получить настройки интеграции с Bitrix24
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Словарь с настройками или None, если интеграция не настроена
        """
        integration = db.query(Integration).filter(Integration.type == "bitrix").first()
        
        if not integration:
            return None
            
        return integration.settings
    
    @staticmethod
    def get_integration_by_id(db: Session, integration_id: str) -> Optional[Integration]:
        """
        Получить интеграцию по ID
        
        Args:
            db: Сессия базы данных
            integration_id: ID интеграции
            
        Returns:
            Объект интеграции или None, если не найдена
        """
        try:
            # Преобразуем ID в целое число для поиска в базе данных
            int_id = int(integration_id)
            logger.info(f"Поиск интеграции с ID={int_id}")
            
            # Ищем интеграцию по ID
            integration = db.query(Integration).filter(Integration.id == int_id).first()
            
            if integration:
                logger.info(f"Найдена интеграция: {integration.type}:{integration.name}")
            else:
                logger.warning(f"Интеграция с ID={int_id} не найдена")
                
            return integration
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при получении интеграции по ID {integration_id}: {str(e)}")
            return None
    
    @staticmethod
    def save_bitrix_settings(db: Session, settings: Dict[str, Any]) -> Integration:
        """
        Сохранить настройки интеграции с Bitrix24
        
        Args:
            db: Сессия базы данных
            settings: Словарь с настройками
            
        Returns:
            Объект интеграции
        """
        integration = db.query(Integration).filter(Integration.type == "bitrix").first()
        
        if integration:
            integration.settings = settings
        else:
            integration = Integration(
                type="bitrix",
                name="Bitrix24",
                settings=settings,
                description="Интеграция с Bitrix24 для хранения бэкапов"
            )
            db.add(integration)
            
        db.commit()
        db.refresh(integration)
        
        return integration
    
    @staticmethod
    def test_bitrix_connection(webhook_url: str) -> Dict[str, Any]:
        """
        Проверить соединение с Bitrix24
        
        Args:
            webhook_url: URL вебхука Bitrix24
            
        Returns:
            Словарь с результатом проверки
        """
        try:
            # Проверяем соединение путем простого запроса к API
            response = requests.get(
                f"{webhook_url.rstrip('/')}/disk.storage.getList"
            )
            
            if response.status_code != 200:
                error_message = response.json().get("error_description", "Неизвестная ошибка")
                return {
                    "success": False, 
                    "error": f"Ошибка API Bitrix24 (HTTP {response.status_code}): {error_message}"
                }
                
            # Проверяем, что в ответе есть результат
            result = response.json().get("result")
            if not result:
                return {
                    "success": False, 
                    "error": "Получен пустой ответ от API Bitrix24"
                }
                
            return {"success": True}
                
        except requests.RequestException as e:
            logger.error(f"Ошибка сетевого соединения с Bitrix24: {str(e)}")
            return {"success": False, "error": f"Ошибка сетевого соединения: {str(e)}"}
        except ValueError as e:
            logger.error(f"Ошибка при разборе ответа от Bitrix24: {str(e)}")
            return {"success": False, "error": f"Ошибка при разборе ответа: {str(e)}"}
        except Exception as e:
            logger.error(f"Ошибка при проверке соединения с Bitrix24: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_bitrix_folders(db: Session) -> List[Dict[str, Any]]:
        """
        Получить список папок из Bitrix24
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Список папок
        """
        settings = IntegrationService.get_bitrix_settings(db)
        
        if not settings or not settings.get("webhook_url"):
            return []
            
        try:
            # Создаем экземпляр хранилища
            storage = BitrixDiskStorage(
                webhook_url=settings["webhook_url"],
                folder_id=settings.get("folder_id"),
                base_path=settings.get("base_path", "backup_google_sheets")
            )
            
            # Получаем список папок
            folders = storage.get_folder_list()
            
            # Преобразуем в нужный формат (без изменений, так как мы обновили формат в классе BitrixDiskStorage)
            return folders
                
        except Exception as e:
            logger.error(f"Ошибка при получении списка папок из Bitrix24: {str(e)}")
            return [] 
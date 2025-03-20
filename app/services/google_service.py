import os
import logging
from typing import Dict, List, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.core.config import settings

logger = logging.getLogger(__name__)

class GoogleService:
    """
    Сервис для работы с Google API
    """
    def __init__(self):
        self.credentials = None
        self.sheets_service = None
        self._init_service()
    
    def _init_service(self):
        """
        Инициализация сервиса Google Sheets API
        """
        try:
            # Проверка наличия файла с учетными данными
            if not os.path.exists(settings.CREDENTIALS_PATH):
                logger.error(f"Файл с учетными данными не найден: {settings.CREDENTIALS_PATH}")
                return
            
            # Создание учетных данных из файла сервисного аккаунта
            self.credentials = service_account.Credentials.from_service_account_file(
                str(settings.CREDENTIALS_PATH),
                scopes=[settings.GOOGLE_API_SCOPES]
            )
            
            # Создание сервиса для работы с Google Sheets API
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            logger.info("Сервис Google Sheets успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Google Sheets API: {str(e)}")
    
    def get_sheet_info(self, spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о таблице Google Sheets
        
        Args:
            spreadsheet_id: ID таблицы Google Sheets
            
        Returns:
            Dict или None: Метаданные таблицы или None в случае ошибки
        """
        if not self.sheets_service:
            logger.error("Сервис Google Sheets не инициализирован")
            return None
        
        try:
            result = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            return {
                "spreadsheet_id": result["spreadsheetId"],
                "title": result["properties"]["title"],
                "sheets": [sheet["properties"]["title"] for sheet in result["sheets"]],
                "url": result["spreadsheetUrl"],
                "owner": self._get_owner_email(spreadsheet_id)
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о таблице {spreadsheet_id}: {str(e)}")
            return None
    
    def _get_owner_email(self, spreadsheet_id: str) -> Optional[str]:
        """
        Получение email владельца таблицы (упрощенная версия)
        
        Args:
            spreadsheet_id: ID таблицы Google Sheets
            
        Returns:
            str или None: Email владельца или None
        """
        # В реальном приложении здесь был бы запрос к Drive API
        # для получения информации о владельце
        # Упрощенно возвращаем None, т.к. это требует доп. разрешений
        return None
    
    def get_sheet_data(self, spreadsheet_id: str, range_name: str = 'A1:Z1000') -> Optional[List[List[Any]]]:
        """
        Получение данных из таблицы Google Sheets
        
        Args:
            spreadsheet_id: ID таблицы Google Sheets
            range_name: Диапазон ячеек для получения данных
            
        Returns:
            List[List[Any]] или None: Данные из таблицы или None в случае ошибки
        """
        if not self.sheets_service:
            logger.error("Сервис Google Sheets не инициализирован")
            return None
        
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            return result.get('values', [])
        except Exception as e:
            logger.error(f"Ошибка при получении данных из таблицы {spreadsheet_id}: {str(e)}")
            return None
    
    def get_sheet_values_by_sheets(self, spreadsheet_id: str) -> Optional[Dict[str, List[List[Any]]]]:
        """
        Получение данных из всех листов таблицы
        
        Args:
            spreadsheet_id: ID таблицы Google Sheets
            
        Returns:
            Dict[str, List[List[Any]]] или None: Данные из всех листов или None в случае ошибки
        """
        if not self.sheets_service:
            logger.error("Сервис Google Sheets не инициализирован")
            return None
        
        try:
            # Получаем список всех листов в таблице
            metadata = self.get_sheet_info(spreadsheet_id)
            if not metadata or "sheets" not in metadata:
                logger.error(f"Не удалось получить список листов таблицы {spreadsheet_id}")
                return None
            
            result = {}
            for sheet_name in metadata["sheets"]:
                # Получаем данные для каждого листа
                data = self.get_sheet_data(spreadsheet_id, f"'{sheet_name}'!A1:Z1000")
                if data is not None:
                    result[sheet_name] = data
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении данных из листов таблицы {spreadsheet_id}: {str(e)}")
            return None

# Создаем глобальный экземпляр сервиса
google_service = GoogleService() 
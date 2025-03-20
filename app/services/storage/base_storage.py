import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO

logger = logging.getLogger(__name__)

class BaseStorage(ABC):
    """
    Абстрактный базовый класс для различных типов хранилищ бэкапов
    """
    
    @abstractmethod
    def save(self, file_data: BinaryIO, file_name: str, content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") -> Optional[str]:
        """
        Сохранение файла в хранилище
        
        Args:
            file_data: Бинарные данные файла
            file_name: Имя файла
            content_type: MIME-тип содержимого
            
        Returns:
            str или None: Путь к сохраненному файлу или None в случае ошибки
        """
        pass
    
    @abstractmethod
    def get(self, file_path: str) -> Optional[BinaryIO]:
        """
        Получение файла из хранилища
        
        Args:
            file_path: Путь к файлу в хранилище
            
        Returns:
            BinaryIO или None: Объект для чтения файла или None в случае ошибки
        """
        pass
    
    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """
        Удаление файла из хранилища
        
        Args:
            file_path: Путь к файлу в хранилище
            
        Returns:
            bool: True если файл успешно удален, иначе False
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "") -> list:
        """
        Получение списка файлов в хранилище
        
        Args:
            prefix: Префикс для фильтрации файлов
            
        Returns:
            list: Список файлов
        """
        pass
    
    @abstractmethod
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о файле
        
        Args:
            file_path: Путь к файлу в хранилище
            
        Returns:
            Dict или None: Информация о файле или None в случае ошибки
        """
        pass 
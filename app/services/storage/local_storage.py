import os
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO, List

from app.services.storage.base_storage import BaseStorage

logger = logging.getLogger(__name__)

class LocalStorage(BaseStorage):
    """
    Класс для хранения бэкапов в локальной файловой системе
    """
    
    def __init__(self, base_path: str = "backups"):
        """
        Инициализация хранилища
        
        Args:
            base_path: Базовый путь для хранения файлов
        """
        self.base_path = Path(base_path)
        os.makedirs(self.base_path, exist_ok=True)
    
    def save(self, file_data: BinaryIO, file_name: str, content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") -> Optional[str]:
        """
        Сохранение файла в локальное хранилище
        
        Args:
            file_data: Бинарные данные файла
            file_name: Имя файла
            content_type: MIME-тип содержимого (не используется в локальном хранилище)
            
        Returns:
            str или None: Путь к сохраненному файлу или None в случае ошибки
        """
        try:
            # Создаем путь к файлу
            file_path = self.base_path / file_name
            
            # Создаем подкаталоги, если они не существуют
            os.makedirs(file_path.parent, exist_ok=True)
            
            # Записываем файл
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
            
            logger.info(f"Файл успешно сохранен: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла {file_name}: {str(e)}")
            return None
    
    def get(self, file_path: str) -> Optional[BinaryIO]:
        """
        Получение файла из локального хранилища
        
        Args:
            file_path: Путь к файлу в хранилище
            
        Returns:
            BinaryIO или None: Объект для чтения файла или None в случае ошибки
        """
        try:
            # Проверяем, существует ли файл
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Файл не найден: {file_path}")
                return None
            
            # Открываем файл для чтения
            return open(path, 'rb')
        except Exception as e:
            logger.error(f"Ошибка при получении файла {file_path}: {str(e)}")
            return None
    
    def delete(self, file_path: str) -> bool:
        """
        Удаление файла из локального хранилища
        
        Args:
            file_path: Путь к файлу в хранилище
            
        Returns:
            bool: True если файл успешно удален, иначе False
        """
        try:
            # Проверяем, существует ли файл
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Файл не найден: {file_path}")
                return False
            
            # Удаляем файл
            os.remove(path)
            logger.info(f"Файл успешно удален: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {file_path}: {str(e)}")
            return False
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        Получение списка файлов в локальном хранилище
        
        Args:
            prefix: Префикс для фильтрации файлов
            
        Returns:
            List[str]: Список путей к файлам
        """
        try:
            result = []
            # Ищем все файлы в директории с учетом префикса
            for root, _, files in os.walk(self.base_path):
                for file in files:
                    if file.startswith(prefix):
                        result.append(os.path.join(root, file))
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении списка файлов с префиксом {prefix}: {str(e)}")
            return []
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о файле в локальном хранилище
        
        Args:
            file_path: Путь к файлу в хранилище
            
        Returns:
            Dict или None: Информация о файле или None в случае ошибки
        """
        try:
            # Проверяем, существует ли файл
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Файл не найден: {file_path}")
                return None
            
            # Получаем информацию о файле
            stat = path.stat()
            return {
                "path": str(path),
                "filename": path.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "modified_at": datetime.fromtimestamp(stat.st_mtime)
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о файле {file_path}: {str(e)}")
            return None 
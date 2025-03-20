import os
import logging
import requests
from typing import Optional, Dict, Any, BinaryIO, List
from urllib.parse import urljoin

from app.services.storage.base_storage import BaseStorage

logger = logging.getLogger(__name__)

class BitrixDiskStorage(BaseStorage):
    """
    Класс для хранения бэкапов в Битрикс24 Диск
    """
    
    def __init__(self, 
                webhook_url: str, 
                folder_id: Optional[str] = None, 
                base_path: str = "backup_google_sheets"):
        """
        Инициализация хранилища Битрикс24
        
        Args:
            webhook_url: URL вебхука для доступа к API Битрикс24
            folder_id: ID папки на диске Битрикс24 (если None, то будет использоваться корневой каталог)
            base_path: Базовый путь для хранения файлов в Битрикс24
        """
        self.webhook_url = webhook_url
        self.folder_id = folder_id
        self.base_path = base_path
        
        # Проверяем соединение с Битрикс24
        self._check_connection()
        
        # Создаем базовую папку, если её нет
        if not self.folder_id:
            self._create_base_folder()
    
    def _check_connection(self) -> bool:
        """
        Проверка соединения с Битрикс24
        
        Returns:
            bool: True если соединение установлено успешно, иначе False
        """
        try:
            # Проверяем соединение с Битрикс24 через вызов метода disk.storage.getList
            response = requests.get(
                urljoin(self.webhook_url, "disk.storage.getList")
            )
            response.raise_for_status()
            
            logger.info("Соединение с Битрикс24 установлено успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка соединения с Битрикс24: {str(e)}")
            return False
    
    def _create_base_folder(self) -> Optional[str]:
        """
        Создание базовой папки в Битрикс24 Диск
        
        Returns:
            str или None: ID созданной папки или None в случае ошибки
        """
        try:
            # Получаем список хранилищ
            response = requests.get(
                urljoin(self.webhook_url, "disk.storage.getList")
            )
            response.raise_for_status()
            
            storages = response.json().get("result", [])
            if not storages:
                logger.error("Не найдены хранилища в Битрикс24")
                return None
                
            # Используем первое хранилище
            storage_id = storages[0].get("ID")
            
            # Получаем список папок в корневом каталоге
            response = requests.post(
                urljoin(self.webhook_url, "disk.storage.getChildren"),
                data={
                    "id": storage_id,
                }
            )
            response.raise_for_status()
            
            folders = response.json().get("result", [])
            
            # Ищем папку с нужным именем
            for folder in folders:
                if folder.get("NAME") == self.base_path:
                    self.folder_id = folder.get("ID")
                    logger.info(f"Найдена существующая папка в Битрикс24: {self.base_path}, ID: {self.folder_id}")
                    return self.folder_id
            
            # Если папка не найдена, создаем новую
            response = requests.post(
                urljoin(self.webhook_url, "disk.folder.addFolder"),
                data={
                    "id": storage_id,
                    "data[NAME]": self.base_path,
                }
            )
            response.raise_for_status()
            
            result = response.json().get("result", {})
            self.folder_id = result.get("ID")
            
            if self.folder_id:
                logger.info(f"Создана новая папка в Битрикс24: {self.base_path}, ID: {self.folder_id}")
            else:
                logger.error("Не удалось получить ID созданной папки")
            
            return self.folder_id
        except Exception as e:
            logger.error(f"Ошибка при создании базовой папки в Битрикс24: {str(e)}")
            return None
    
    def save(self, file_data: BinaryIO, file_name: str, content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") -> Optional[str]:
        """
        Сохранение файла в Битрикс24 Диск
        
        Args:
            file_data: Бинарные данные файла
            file_name: Имя файла
            content_type: MIME-тип содержимого
            
        Returns:
            str или None: ID сохраненного файла или None в случае ошибки
        """
        try:
            # Сохраняем текущую позицию в файле
            current_position = file_data.tell()
            
            # Сбрасываем позицию в начало файла
            file_data.seek(0)
            
            # API Битрикс24 может работать в двух режимах загрузки:
            # 1. Прямая загрузка через disk.folder.uploadfile
            # 2. Двухэтапная загрузка через uploadUrl
            
            # Сначала пробуем прямую загрузку
            logger.info(f"Начинаем загрузку файла {file_name} в Битрикс24, папка ID: {self.folder_id}")
            files = {'file': (file_name, file_data, content_type)}
            
            response = requests.post(
                urljoin(self.webhook_url, "disk.folder.uploadfile"),
                data={
                    "id": self.folder_id
                },
                files=files
            )
            response.raise_for_status()
            
            # Анализируем ответ
            result = response.json().get("result", {})
            
            # Если получили сразу ID файла - отлично
            file_id = result.get("ID")
            
            # Если получили uploadUrl - используем двухэтапную загрузку
            if not file_id and isinstance(result, dict) and result.get("uploadUrl"):
                logger.info(f"Получен uploadUrl для двухэтапной загрузки: {result.get('uploadUrl')}")
                
                # Сбрасываем позицию файла в начало для повторной загрузки
                file_data.seek(0)
                
                # Выполняем второй этап загрузки по полученному URL
                upload_url = result.get("uploadUrl")
                upload_files = {'file': (file_name, file_data, content_type)}
                
                # Загружаем файл по полученному URL
                upload_response = requests.post(
                    upload_url,
                    files=upload_files
                )
                upload_response.raise_for_status()
                
                # Получаем результат загрузки
                upload_result = upload_response.json().get("result", {})
                file_id = upload_result.get("ID") or upload_result.get("file_id")
                
                if not file_id:
                    logger.error(f"Не удалось получить ID загруженного файла после двухэтапной загрузки: {upload_response.text}")
                else:
                    logger.info(f"Файл успешно загружен в Битрикс24 через двухэтапную загрузку, получен ID: {file_id}")
            
            # Восстанавливаем позицию в файле
            file_data.seek(current_position)
            
            if file_id:
                logger.info(f"Файл успешно сохранен в Битрикс24: {file_name}, ID: {file_id}")
                return file_id
            else:
                logger.error(f"Не удалось получить ID загруженного файла: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла {file_name} в Битрикс24: {str(e)}")
            return None
    
    def get(self, file_id: str) -> Optional[BinaryIO]:
        """
        Получение файла из Битрикс24 Диск
        
        Args:
            file_id: ID файла в Битрикс24
            
        Returns:
            BinaryIO или None: Объект для чтения файла или None в случае ошибки
        """
        try:
            # Получаем информацию о файле
            response = requests.get(
                urljoin(self.webhook_url, "disk.file.get"),
                params={"id": file_id}
            )
            response.raise_for_status()
            
            file_info = response.json().get("result", {})
            download_url = file_info.get("DOWNLOAD_URL")
            
            if not download_url:
                logger.error(f"Не удалось получить URL для скачивания файла с ID: {file_id}")
                return None
            
            # Скачиваем файл
            file_response = requests.get(download_url, stream=True)
            file_response.raise_for_status()
            
            # Создаем временный файл
            import tempfile
            temp_file = tempfile.TemporaryFile()
            
            # Записываем содержимое файла
            for chunk in file_response.iter_content(chunk_size=1024):
                if chunk:
                    temp_file.write(chunk)
            
            # Сбрасываем позицию в начало файла
            temp_file.seek(0)
            
            return temp_file
            
        except Exception as e:
            logger.error(f"Ошибка при получении файла с ID {file_id} из Битрикс24: {str(e)}")
            return None
    
    def delete(self, file_id: str) -> bool:
        """
        Удаление файла из Битрикс24 Диск
        
        Args:
            file_id: ID файла в Битрикс24
            
        Returns:
            bool: True если файл успешно удален, иначе False
        """
        try:
            # Удаляем файл
            response = requests.post(
                urljoin(self.webhook_url, "disk.file.delete"),
                data={"id": file_id}
            )
            response.raise_for_status()
            
            result = response.json().get("result", False)
            
            if result:
                logger.info(f"Файл успешно удален из Битрикс24: ID {file_id}")
            else:
                logger.error(f"Не удалось удалить файл с ID {file_id} из Битрикс24")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при удалении файла с ID {file_id} из Битрикс24: {str(e)}")
            return False
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        Получение списка файлов в Битрикс24 Диск
        
        Args:
            prefix: Префикс для фильтрации файлов (не используется в текущей реализации)
            
        Returns:
            List[str]: Список ID файлов
        """
        try:
            # Получаем список файлов в папке
            response = requests.get(
                urljoin(self.webhook_url, "disk.folder.getChildren"),
                params={
                    "id": self.folder_id,
                    "filter[TYPE]": "file"
                }
            )
            response.raise_for_status()
            
            result = response.json().get("result", [])
            
            # Фильтруем по префиксу, если он задан
            files = []
            for file_info in result:
                file_name = file_info.get("NAME", "")
                if not prefix or file_name.startswith(prefix):
                    files.append(file_info.get("ID"))
            
            return files
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка файлов из Битрикс24: {str(e)}")
            return []
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о файле в Битрикс24
        
        Args:
            file_id: ID файла в Битрикс24
            
        Returns:
            Dict или None: Информация о файле или None в случае ошибки
        """
        try:
            # Получаем информацию о файле
            response = requests.get(
                urljoin(self.webhook_url, "disk.file.get"),
                params={"id": file_id}
            )
            response.raise_for_status()
            
            file_info = response.json().get("result", {})
            
            if file_info:
                return {
                    "id": file_info.get("ID"),
                    "filename": file_info.get("NAME"),
                    "size": file_info.get("SIZE"),
                    "created_at": file_info.get("CREATE_TIME"),
                    "modified_at": file_info.get("UPDATE_TIME"),
                    "download_url": file_info.get("DOWNLOAD_URL")
                }
            else:
                logger.error(f"Не удалось получить информацию о файле с ID {file_id}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении информации о файле с ID {file_id} из Битрикс24: {str(e)}")
            return None
    
    def get_folder_list(self) -> List[Dict[str, Any]]:
        """
        Получение списка папок в Битрикс24 Диск
        
        Returns:
            List[Dict]: Список папок с информацией о них
        """
        try:
            # Получаем список всех хранилищ
            response = requests.get(
                urljoin(self.webhook_url, "disk.storage.getList")
            )
            response.raise_for_status()
            
            storages = response.json().get("result", [])
            result = []
            
            # Обходим все хранилища и получаем список папок в них
            for storage in storages:
                storage_id = storage.get("ID")
                storage_name = storage.get("NAME", "")
                
                # Получаем корневые папки хранилища
                folder_response = requests.post(
                    urljoin(self.webhook_url, "disk.storage.getChildren"),
                    data={"id": storage_id}
                )
                folder_response.raise_for_status()
                
                folders = folder_response.json().get("result", [])
                
                for folder in folders:
                    folder_info = {
                        "ID": folder.get("ID"),
                        "NAME": folder.get("NAME"),
                        "PATH": f"{storage_name}/",
                        "PARENT_ID": storage_id,
                        "CREATED_TIME": folder.get("CREATE_TIME"),
                        "UPDATED_TIME": folder.get("UPDATE_TIME")
                    }
                    result.append(folder_info)
                    
                # Если у нас есть ID папки, получаем также папки внутри этой папки
                if self.folder_id:
                    subfolder_response = requests.post(
                        urljoin(self.webhook_url, "disk.folder.getChildren"),
                        data={
                            "id": self.folder_id,
                            "filter[TYPE]": "folder"
                        }
                    )
                    if subfolder_response.status_code == 200:
                        subfolders = subfolder_response.json().get("result", [])
                        for subfolder in subfolders:
                            subfolder_info = {
                                "ID": subfolder.get("ID"),
                                "NAME": subfolder.get("NAME"),
                                "PATH": f"{storage_name}/{self.base_path}/",
                                "PARENT_ID": self.folder_id,
                                "CREATED_TIME": subfolder.get("CREATE_TIME"),
                                "UPDATED_TIME": subfolder.get("UPDATE_TIME")
                            }
                            result.append(subfolder_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка папок из Битрикс24: {str(e)}")
            return [] 
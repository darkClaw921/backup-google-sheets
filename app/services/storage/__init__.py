from app.services.storage.base_storage import BaseStorage
from app.services.storage.local_storage import LocalStorage
from app.services.storage.bitrix_disk_storage import BitrixDiskStorage

# Фабрика для создания экземпляров хранилищ по типу
def get_storage(storage_type: str, **kwargs) -> BaseStorage:
    """
    Получение экземпляра хранилища по типу
    
    Args:
        storage_type: Тип хранилища (local, s3, gdrive, bitrix, etc.)
        **kwargs: Дополнительные параметры для инициализации хранилища
        
    Returns:
        BaseStorage: Экземпляр хранилища
        
    Raises:
        ValueError: Если указан неподдерживаемый тип хранилища
    """
    if storage_type == "local":
        return LocalStorage(**kwargs)
    elif storage_type == "bitrix":
        return BitrixDiskStorage(**kwargs)
    # Здесь можно добавить другие типы хранилищ
    # elif storage_type == "s3":
    #     return S3Storage(**kwargs)
    # elif storage_type == "gdrive":
    #     return GDriveStorage(**kwargs)
    else:
        raise ValueError(f"Неподдерживаемый тип хранилища: {storage_type}") 
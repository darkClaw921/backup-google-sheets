import logging
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


def init_db(db: Session) -> None:
    """
    Инициализация базы данных.
    Создает таблицы, если они не существуют.
    
    Args:
        db: Сессия базы данных
    """
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        raise 
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Создаем директорию для базы данных, если она не существует
os.makedirs(os.path.dirname(settings.DATABASE_URL), exist_ok=True)

# Создаем движок SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Для SQLite
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Функция-генератор, возвращающая сессию базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
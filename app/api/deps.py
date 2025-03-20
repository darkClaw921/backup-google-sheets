from typing import Generator

from fastapi import Depends, HTTPException, status
from app.db.session import SessionLocal


def get_db() -> Generator:
    """
    Зависимость для получения сессии базы данных
    """
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close() 
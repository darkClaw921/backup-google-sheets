from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from sqlalchemy.orm import Session

from app.schemas.sheet import SheetCreate, SheetUpdate, SheetResponse
from app.services.google_service import google_service
from app.api.deps import get_db
from app.models.sheet import Sheet

router = APIRouter()

@router.post("/", response_model=SheetResponse, status_code=status.HTTP_201_CREATED)
async def create_sheet(sheet: SheetCreate, db: Session = Depends(get_db)):
    """
    Создание новой таблицы для отслеживания
    """
    # Проверяем доступность таблицы через Google API
    sheet_info = google_service.get_sheet_info(sheet.spreadsheet_id)
    if not sheet_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось получить доступ к таблице. Проверьте ID таблицы и права доступа сервисного аккаунта."
        )
    
    # Создаем объект Sheet для базы данных
    db_sheet = Sheet(
        name=sheet.name,
        spreadsheet_id=sheet.spreadsheet_id,
        credentials_id=sheet.credentials_id,
        created_at=datetime.now()
    )
    
    # Сохраняем в базу данных
    db.add(db_sheet)
    db.commit()
    db.refresh(db_sheet)
    
    return db_sheet

@router.get("/", response_model=List[SheetResponse])
async def get_sheets(db: Session = Depends(get_db)):
    """
    Получение списка всех отслеживаемых таблиц
    """
    return db.query(Sheet).all()

@router.get("/{sheet_id}", response_model=SheetResponse)
async def get_sheet(sheet_id: str, db: Session = Depends(get_db)):
    """
    Получение информации об отслеживаемой таблице
    """
    sheet = db.query(Sheet).filter(Sheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Таблица не найдена"
        )
    
    return sheet

@router.put("/{sheet_id}", response_model=SheetResponse)
async def update_sheet(sheet_id: str, sheet_update: SheetUpdate, db: Session = Depends(get_db)):
    """
    Обновление информации об отслеживаемой таблице
    """
    sheet = db.query(Sheet).filter(Sheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Таблица не найдена"
        )
    
    # Обновляем поля таблицы
    update_data = sheet_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sheet, field, value)
    
    sheet.updated_at = datetime.now()
    
    # Сохраняем изменения
    db.commit()
    db.refresh(sheet)
    
    return sheet

@router.delete("/{sheet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sheet(sheet_id: str, db: Session = Depends(get_db)):
    """
    Удаление отслеживаемой таблицы
    """
    sheet = db.query(Sheet).filter(Sheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Таблица не найдена"
        )
    
    # Удаляем таблицу
    db.delete(sheet)
    db.commit()
    
    return None

@router.get("/{sheet_id}/verify", response_model=dict)
async def verify_sheet_access(sheet_id: str, db: Session = Depends(get_db)):
    """
    Проверка доступа к таблице
    """
    sheet = db.query(Sheet).filter(Sheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Таблица не найдена"
        )
    
    # Проверяем доступ к таблице
    sheet_info = google_service.get_sheet_info(sheet.spreadsheet_id)
    if not sheet_info:
        return {
            "access": False,
            "message": "Нет доступа к таблице. Убедитесь, что сервисный аккаунт имеет доступ к таблице."
        }
    
    # Обновляем информацию о таблице
    sheet.name = sheet_info["title"]
    sheet.updated_at = datetime.now()
    db.commit()
    
    return {
        "access": True,
        "sheets": sheet_info["sheets"],
        "title": sheet_info["title"],
        "url": sheet_info["url"]
    } 
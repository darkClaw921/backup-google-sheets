from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Response, Depends, Query, Path
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from app.core.scheduler import scheduler_service
from app.api.deps import get_db
from app.models.schedule import Schedule
from app.models.sheet import Sheet

router = APIRouter()

@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db)
):
    """
    Создать новое расписание.
    """
    # Проверяем, существует ли таблица
    sheet = db.query(Sheet).filter(Sheet.id == schedule_data.sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Таблица не найдена")
    
    # Создаем объект расписания
    schedule = Schedule(
        sheet_id=schedule_data.sheet_id,
        schedule_type=schedule_data.schedule_type,
        schedule_config=schedule_data.schedule_config,
        storage_type=schedule_data.storage_type,
        storage_params=schedule_data.storage_params,
        is_active=schedule_data.is_active,
        created_at=datetime.utcnow()
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    # Если расписание активно, добавляем его в планировщик
    if schedule.is_active:
        scheduler_service.add_schedule(schedule, db)
    
    return schedule

@router.get("/", response_model=List[ScheduleResponse])
def get_schedules(
    db: Session = Depends(get_db),
    sheet_id: Optional[str] = Query(None, description="Фильтр по ID таблицы")
):
    """
    Получить список всех расписаний.
    Может быть отфильтрован по ID таблицы.
    """
    query = db.query(Schedule)
    
    if sheet_id:
        query = query.filter(Schedule.sheet_id == sheet_id)
    
    return query.all()

@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: str = Path(..., description="ID расписания"),
    db: Session = Depends(get_db)
):
    """
    Получить расписание по ID.
    """
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    
    return schedule

@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_data: ScheduleUpdate,
    schedule_id: str = Path(..., description="ID расписания"),
    db: Session = Depends(get_db)
):
    """
    Обновить существующее расписание.
    """
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    
    # Если изменяется таблица, проверяем, существует ли она
    if schedule_data.sheet_id and schedule_data.sheet_id != schedule.sheet_id:
        sheet = db.query(Sheet).filter(Sheet.id == schedule_data.sheet_id).first()
        if not sheet:
            raise HTTPException(status_code=404, detail="Таблица не найдена")
        schedule.sheet_id = schedule_data.sheet_id
    
    # Обновляем поля
    if schedule_data.schedule_type is not None:
        schedule.schedule_type = schedule_data.schedule_type
    
    if schedule_data.schedule_config is not None:
        schedule.schedule_config = schedule_data.schedule_config
    
    if schedule_data.storage_type is not None:
        schedule.storage_type = schedule_data.storage_type
    
    if schedule_data.storage_params is not None:
        schedule.storage_params = schedule_data.storage_params
    
    if schedule_data.is_active is not None:
        schedule.is_active = schedule_data.is_active
    
    schedule.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(schedule)
    
    # Обновляем в планировщике
    scheduler_service.update_schedule(schedule, db)
    
    return schedule

@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str = Path(..., description="ID расписания"),
    db: Session = Depends(get_db)
):
    """
    Удалить расписание.
    """
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    
    # Удаляем из планировщика
    scheduler_service.remove_schedule(schedule_id)
    
    # Удаляем из БД
    db.delete(schedule)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT) 
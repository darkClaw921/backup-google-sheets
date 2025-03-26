from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Response, Depends, Query, Path
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from app.api.deps import get_db
from app.models.sheet import Sheet
from app.services.schedule_service import schedule_service

router = APIRouter()

@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db)
):
    """
    Создать новое расписание.
    """
    # Проверяем, что указан хотя бы один ID таблицы
    if not schedule_data.sheets_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать хотя бы одну таблицу"
        )
    
    # Проверяем наличие хотя бы одного хранилища
    if not schedule_data.storage_configs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать хотя бы одно хранилище"
        )
    
    # Создаем расписание с помощью сервиса
    schedule = schedule_service.create_schedule(
        db=db,
        sheets_ids=schedule_data.sheets_ids,
        schedule_type=schedule_data.schedule_type,
        schedule_config=schedule_data.schedule_config,
        storage_configs=schedule_data.storage_configs,
        is_active=schedule_data.is_active
    )
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать расписание. Проверьте, что все указанные таблицы существуют."
        )
    
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
    return schedule_service.get_all_schedules(db, sheet_id)

@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: str = Path(..., description="ID расписания"),
    db: Session = Depends(get_db)
):
    """
    Получить расписание по ID.
    """
    schedule = schedule_service.get_schedule(db, schedule_id)
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
    # Проверяем, что если передан список таблиц, то он не пустой
    if schedule_data.sheets_ids is not None and not schedule_data.sheets_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Список таблиц не может быть пустым"
        )
    
    # Проверяем, что если переданы конфигурации хранилищ, то список не пустой
    if schedule_data.storage_configs is not None and not schedule_data.storage_configs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать хотя бы одно хранилище"
        )
    
    # Обновляем расписание с помощью сервиса
    schedule = schedule_service.update_schedule(
        db=db,
        schedule_id=schedule_id,
        sheets_ids=schedule_data.sheets_ids,
        schedule_type=schedule_data.schedule_type,
        schedule_config=schedule_data.schedule_config,
        storage_configs=schedule_data.storage_configs,
        is_active=schedule_data.is_active
    )
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не удалось обновить расписание. Проверьте, что расписание существует и все указанные таблицы существуют."
        )
    
    return schedule

@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str = Path(..., description="ID расписания"),
    db: Session = Depends(get_db)
):
    """
    Удалить расписание.
    """
    success = schedule_service.delete_schedule(db, schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{schedule_id}/execute", status_code=status.HTTP_200_OK)
async def execute_schedule(
    schedule_id: str = Path(..., description="ID расписания"),
    db: Session = Depends(get_db)
):
    """
    Немедленно выполнить расписание, создав бэкапы всех указанных таблиц.
    """
    result = schedule_service.execute_schedule(db, schedule_id)
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Не удалось выполнить расписание")
        )
    
    return result 
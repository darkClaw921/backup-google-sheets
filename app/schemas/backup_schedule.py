from typing import Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

class ScheduleBase(BaseModel):
    """Базовая схема для расписания бэкапов"""
    sheet_id: str
    storage_type: str = "local"
    schedule_type: str
    schedule_config: Dict[str, Any]
    
    @validator('schedule_type')
    def validate_schedule_type(cls, v):
        if v not in ["interval", "cron"]:
            raise ValueError("Тип расписания должен быть 'interval' или 'cron'")
        return v
    
    @validator('schedule_config')
    def validate_schedule_config(cls, v, values):
        schedule_type = values.get('schedule_type')
        
        if schedule_type == "interval":
            interval = v.get("interval", {})
            if not interval or not any(k in interval for k in ["seconds", "minutes", "hours", "days", "weeks"]):
                raise ValueError("Для интервального расписания необходимо указать seconds, minutes, hours, days или weeks")
        
        elif schedule_type == "cron":
            cron = v.get("cron", {})
            required_fields = ["year", "month", "day", "week", "day_of_week", "hour", "minute", "second"]
            if not cron or not any(k in cron for k in required_fields):
                raise ValueError(f"Для cron-расписания необходимо указать хотя бы одно из: {', '.join(required_fields)}")
        
        return v

class ScheduleCreate(ScheduleBase):
    """Схема для создания расписания"""
    is_active: bool = True

class ScheduleUpdate(BaseModel):
    """Схема для обновления расписания"""
    storage_type: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    
    @validator('schedule_type')
    def validate_schedule_type(cls, v):
        if v is not None and v not in ["interval", "cron"]:
            raise ValueError("Тип расписания должен быть 'interval' или 'cron'")
        return v

class ScheduleInDB(ScheduleBase):
    """Схема расписания в БД"""
    id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ScheduleOut(ScheduleInDB):
    """Схема расписания для вывода"""
    pass 
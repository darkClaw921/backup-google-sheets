import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.schedule import Schedule
from app.models.sheet import Sheet
from app.core.scheduler import scheduler_service
from app.services.backup_service import backup_sheets

logger = logging.getLogger(__name__)

class ScheduleService:
    @staticmethod
    def create_schedule(
        db: Session,
        sheets_ids: List[str],
        schedule_type: str,
        schedule_config: Dict[str, Any],
        storage_configs: List[Dict[str, Any]],
        is_active: bool = True
    ) -> Optional[Schedule]:
        """
        Создает новое расписание для указанных таблиц
        
        Args:
            db: Сессия базы данных
            sheets_ids: Список ID таблиц
            schedule_type: Тип расписания ('interval' или 'cron')
            schedule_config: Конфигурация расписания
            storage_configs: Список конфигураций хранилищ
            is_active: Активно ли расписание
            
        Returns:
            Созданное расписание или None в случае ошибки
        """
        try:
            # Проверяем существование всех таблиц
            existing_sheets = db.query(Sheet).filter(Sheet.id.in_(sheets_ids)).all()
            existing_ids = [sheet.id for sheet in existing_sheets]
            
            if len(existing_ids) != len(sheets_ids):
                missing_ids = set(sheets_ids) - set(existing_ids)
                logger.error(f"Не найдены таблицы с ID: {missing_ids}")
                return None
            
            # Создаем объект расписания
            schedule = Schedule(
                sheets_ids=sheets_ids,
                schedule_type=schedule_type,
                schedule_config=schedule_config,
                storage_configs=[config if isinstance(config, dict) else config.dict() for config in storage_configs],
                is_active=is_active,
                created_at=datetime.utcnow()
            )
            
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            
            # Если расписание активно, добавляем его в планировщик
            if schedule.is_active:
                scheduler_service.add_multi_sheet_schedule(schedule, db)
            
            return schedule
            
        except Exception as e:
            logger.error(f"Ошибка при создании расписания: {str(e)}")
            db.rollback()
            return None
    
    @staticmethod
    def update_schedule(
        db: Session,
        schedule_id: str,
        sheets_ids: Optional[List[str]] = None,
        schedule_type: Optional[str] = None,
        schedule_config: Optional[Dict[str, Any]] = None,
        storage_configs: Optional[List[Dict[str, Any]]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Schedule]:
        """
        Обновляет существующее расписание
        
        Args:
            db: Сессия базы данных
            schedule_id: ID расписания
            sheets_ids: Список ID таблиц
            schedule_type: Тип расписания ('interval' или 'cron')
            schedule_config: Конфигурация расписания
            storage_configs: Список конфигураций хранилищ
            is_active: Активно ли расписание
            
        Returns:
            Обновленное расписание или None в случае ошибки
        """
        try:
            # Получаем расписание из БД
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule:
                logger.error(f"Расписание с ID {schedule_id} не найдено")
                return None
            
            # Обновляем список таблиц, если он передан
            if sheets_ids is not None:
                # Проверяем существование всех таблиц
                existing_sheets = db.query(Sheet).filter(Sheet.id.in_(sheets_ids)).all()
                existing_ids = [sheet.id for sheet in existing_sheets]
                
                if len(existing_ids) != len(sheets_ids):
                    missing_ids = set(sheets_ids) - set(existing_ids)
                    logger.error(f"Не найдены таблицы с ID: {missing_ids}")
                    return None
                
                schedule.sheets_ids = sheets_ids
            
            # Обновляем другие поля
            if schedule_type is not None:
                schedule.schedule_type = schedule_type
            
            if schedule_config is not None:
                schedule.schedule_config = schedule_config
            
            if storage_configs is not None:
                schedule.storage_configs = [config if isinstance(config, dict) else config.dict() for config in storage_configs]
            
            if is_active is not None:
                schedule.is_active = is_active
            
            schedule.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(schedule)
            
            # Обновляем в планировщике
            scheduler_service.update_schedule(schedule, db)
            
            return schedule
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении расписания: {str(e)}")
            db.rollback()
            return None
    
    @staticmethod
    def delete_schedule(db: Session, schedule_id: str) -> bool:
        """
        Удаляет расписание
        
        Args:
            db: Сессия базы данных
            schedule_id: ID расписания
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        try:
            # Получаем расписание из БД
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule:
                logger.error(f"Расписание с ID {schedule_id} не найдено")
                return False
            
            # Удаляем из планировщика
            scheduler_service.remove_schedule(schedule_id)
            
            # Удаляем из БД
            db.delete(schedule)
            db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при удалении расписания: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def get_schedule(db: Session, schedule_id: str) -> Optional[Schedule]:
        """
        Получает расписание по ID
        
        Args:
            db: Сессия базы данных
            schedule_id: ID расписания
            
        Returns:
            Объект расписания или None
        """
        try:
            return db.query(Schedule).filter(Schedule.id == schedule_id).first()
        except Exception as e:
            logger.error(f"Ошибка при получении расписания: {str(e)}")
            return None
    
    @staticmethod
    def get_all_schedules(db: Session, sheet_id: Optional[str] = None) -> List[Schedule]:
        """
        Получает список всех расписаний
        
        Args:
            db: Сессия базы данных
            sheet_id: Опциональный ID таблицы для фильтрации
            
        Returns:
            Список расписаний
        """
        try:
            query = db.query(Schedule)
            
            if sheet_id:
                # Фильтрация расписаний, содержащих указанный ID таблицы
                # Для этого придется проверять каждое расписание
                schedules = query.all()
                return [s for s in schedules if sheet_id in s.sheets_ids]
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка расписаний: {str(e)}")
            return []
    
    @staticmethod
    def execute_schedule(db: Session, schedule_id: str) -> Dict[str, Any]:
        """
        Выполняет расписание немедленно
        
        Args:
            db: Сессия базы данных
            schedule_id: ID расписания
            
        Returns:
            Результат выполнения расписания
        """
        try:
            # Получаем расписание из БД
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule:
                logger.error(f"Расписание с ID {schedule_id} не найдено")
                return {"success": False, "error": "Расписание не найдено"}
            
            # Получаем информацию о всех таблицах
            sheets_ids = schedule.sheets_ids
            sheets = db.query(Sheet).filter(Sheet.id.in_(sheets_ids)).all()
            
            if len(sheets) != len(sheets_ids):
                missing_ids = set(sheets_ids) - set(sheet.id for sheet in sheets)
                logger.error(f"Не найдены некоторые таблицы: {missing_ids}")
                return {"success": False, "error": f"Не найдены таблицы: {missing_ids}"}
            
            # Формируем список таблиц для бэкапа
            sheets_data = []
            for sheet in sheets:
                sheets_data.append({
                    "id": sheet.id,
                    "name": sheet.name,
                    "spreadsheet_id": sheet.spreadsheet_id
                })
            
            # Создаем бэкапы для всех таблиц
            results = backup_sheets(
                sheets=sheets_data,
                storage_configs=schedule.storage_configs,
                db=db
            )
            
            return {
                "success": True,
                "results": results,
                "sheets_count": len(sheets),
                "successful_backups": sum(1 for r in results if r.get("success", False))
            }
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении расписания: {str(e)}")
            return {"success": False, "error": str(e)}


# Создаем глобальный экземпляр сервиса
schedule_service = ScheduleService() 
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy.orm import Session

from app.core.sheets_service import create_backup
from app.models.schedule import Schedule
from app.models.sheet import Sheet
from app.api.deps import get_db

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self):
        """Инициализация планировщика задач"""
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore(MemoryJobStore(), 'default')
        self.scheduler.start()
        logger.info("Планировщик задач запущен")
    
    def add_schedule(self, schedule: Schedule, db: Session) -> str:
        """
        Добавляет расписание в планировщик
        
        Args:
            schedule: Объект расписания
            db: Сессия базы данных
            
        Returns:
            ID задачи в планировщике
        """
        # Получаем информацию о таблице
        sheet = db.query(Sheet).filter(Sheet.id == schedule.sheet_id).first()
        if not sheet:
            logger.error(f"Не удалось найти таблицу с ID {schedule.sheet_id}")
            return None
        
        # Формируем триггер в зависимости от типа расписания
        trigger = self._create_trigger(schedule.schedule_type, schedule.schedule_config)
        if not trigger:
            logger.error(f"Не удалось создать триггер для расписания {schedule.id}")
            return None
        
        # Функция для выполнения задачи
        def backup_job():
            try:
                # Создаем новую сессию для работы с БД в фоновой задаче
                session = next(get_db())
                try:
                    logger.info(f"Запуск бэкапа по расписанию {schedule.id} для таблицы {sheet.name} (ID: {sheet.id})")
                    logger.info(f"Параметры расписания: storage_type={schedule.storage_type}, storage_params={schedule.storage_params}")
                    
                    create_backup(
                        sheet_id=sheet.id,
                        spreadsheet_id=sheet.spreadsheet_id,
                        sheet_name=sheet.name,
                        storage_type=schedule.storage_type,
                        storage_params=schedule.storage_params,
                        db=session
                    )
                    logger.info(f"Бэкап по расписанию {schedule.id} для таблицы {sheet.name} выполнен успешно")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"Ошибка при выполнении бэкапа по расписанию {schedule.id}: {str(e)}", exc_info=True)
        
        # Добавляем задачу в планировщик
        job = self.scheduler.add_job(
            backup_job,
            trigger=trigger,
            id=f"backup_{schedule.id}",
            replace_existing=True,
            misfire_grace_time=3600  # 1 час
        )
        
        logger.info(f"Добавлено расписание {schedule.id} для таблицы {sheet.name}")
        return job.id
    
    def update_schedule(self, schedule: Schedule, db: Session) -> Optional[str]:
        """
        Обновляет расписание в планировщике
        
        Args:
            schedule: Объект расписания
            db: Сессия базы данных
            
        Returns:
            ID задачи в планировщике или None
        """
        # Сначала удаляем существующее расписание
        self.remove_schedule(schedule.id)
        
        # Если расписание активно, добавляем его снова
        if schedule.is_active:
            return self.add_schedule(schedule, db)
        
        return None
    
    def remove_schedule(self, schedule_id: str) -> None:
        """
        Удаляет расписание из планировщика
        
        Args:
            schedule_id: ID расписания
        """
        job_id = f"backup_{schedule_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Расписание {schedule_id} удалено из планировщика")
        except Exception as e:
            logger.warning(f"Не удалось удалить расписание {schedule_id}: {str(e)}")
    
    def _create_trigger(self, schedule_type: str, config: Dict[str, Any]) -> Optional[Any]:
        """
        Создает триггер на основе типа расписания и конфигурации
        
        Args:
            schedule_type: Тип расписания ('interval' или 'cron')
            config: Конфигурация расписания
            
        Returns:
            Триггер для планировщика или None в случае ошибки
        """
        try:
            if schedule_type == "interval":
                # Параметры для интервального триггера
                interval_params = {}
                
                if "interval" in config:
                    interval_dict = config["interval"]
                    for unit in ["seconds", "minutes", "hours", "days", "weeks"]:
                        if unit in interval_dict and interval_dict[unit]:
                            interval_params[unit] = int(interval_dict[unit])
                
                if not interval_params:
                    # Если не указаны параметры, используем значение по умолчанию (1 день)
                    interval_params["days"] = 1
                
                return IntervalTrigger(**interval_params)
            
            elif schedule_type == "cron":
                # Параметры для cron-триггера
                cron_params = {}
                
                if "cron" in config:
                    cron_dict = config["cron"]
                    for field in ["second", "minute", "hour", "day", "month", "day_of_week"]:
                        if field in cron_dict and cron_dict[field]:
                            cron_params[field] = cron_dict[field]
                
                return CronTrigger(**cron_params)
            
            else:
                logger.error(f"Неизвестный тип расписания: {schedule_type}")
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при создании триггера: {str(e)}")
            return None
    
    def shutdown(self):
        """Останавливает планировщик"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Планировщик задач остановлен")


# Создаем глобальный экземпляр сервиса планировщика
scheduler_service = SchedulerService()


def init_schedules(db: Session):
    """
    Инициализирует все активные расписания из базы данных
    
    Args:
        db: Сессия базы данных
    """
    logger.info("Инициализация расписаний из базы данных")
    
    try:
        # Получаем все активные расписания
        schedules = db.query(Schedule).filter(Schedule.is_active == True).all()
        
        for schedule in schedules:
            scheduler_service.add_schedule(schedule, db)
        
        logger.info(f"Инициализировано {len(schedules)} расписаний")
    
    except Exception as e:
        logger.error(f"Ошибка при инициализации расписаний: {str(e)}")


def cleanup():
    """Очищает ресурсы планировщика при остановке приложения"""
    scheduler_service.shutdown() 
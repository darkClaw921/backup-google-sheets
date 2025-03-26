import logging
from typing import Dict, Any, Optional, List
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
from app.services.backup_service import backup_sheets

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self):
        """Инициализация планировщика задач"""
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore(MemoryJobStore(), 'default')
        self.scheduler.start()
        logger.info("Планировщик задач запущен")
    
    def add_multi_sheet_schedule(self, schedule: Schedule, db: Session) -> str:
        """
        Добавляет расписание для нескольких таблиц в планировщик
        
        Args:
            schedule: Объект расписания
            db: Сессия базы данных
            
        Returns:
            ID задачи в планировщике
        """
        try:
            # Получаем информацию о таблицах
            sheet_ids = schedule.sheets_ids
            sheets = db.query(Sheet).filter(Sheet.id.in_(sheet_ids)).all()
            
            if len(sheets) != len(sheet_ids):
                logger.error(f"Не удалось найти все таблицы для расписания {schedule.id}")
                missing_ids = set(sheet_ids) - set(sheet.id for sheet in sheets)
                logger.error(f"Отсутствуют таблицы с ID: {missing_ids}")
                return None
            
            # Формируем триггер в зависимости от типа расписания
            trigger = self._create_trigger(schedule.schedule_type, schedule.schedule_config)
            if not trigger:
                logger.error(f"Не удалось создать триггер для расписания {schedule.id}")
                return None
            
            # Функция для выполнения задачи с несколькими таблицами
            def multi_backup_job(schedule_id: str, db: Session):
                """
                Задача для создания бэкапов по расписанию для нескольких таблиц
                """
                try:
                    logger.info(f"Запуск бэкапа по расписанию {schedule_id}")
                    
                    # Получаем расписание из БД
                    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
                    if not schedule:
                        logger.error(f"Расписание {schedule_id} не найдено")
                        return
                    
                    # Получаем информацию о таблицах
                    sheets_ids = schedule.sheets_ids
                    sheets = db.query(Sheet).filter(Sheet.id.in_(sheets_ids)).all()
                    
                    if len(sheets) != len(sheets_ids):
                        logger.error(f"Не найдены некоторые таблицы для расписания {schedule_id}")
                        return
                    
                    # Создаем бэкапы для всех таблиц
                    sheets_data = []
                    for sheet in sheets:
                        sheets_data.append({
                            "id": sheet.id,
                            "name": sheet.name,
                            "spreadsheet_id": sheet.spreadsheet_id
                        })
                    
                    results = backup_sheets(
                        sheets=sheets_data,
                        storage_configs=schedule.storage_configs,
                        db=db
                    )
                    
                    # Подсчитываем статистику выполнения
                    success_count = sum(1 for r in results if r.get("success", False))
                    logger.info(f"Бэкап по расписанию {schedule_id} завершен. Успешно: {success_count}/{len(sheets)}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при выполнении бэкапа по расписанию {schedule_id}: {str(e)}")
                    logger.exception(e)
            
            # Добавляем задачу в планировщик
            job = self.scheduler.add_job(
                multi_backup_job,
                trigger=trigger,
                id=f"backup_{schedule.id}",
                replace_existing=True,
                misfire_grace_time=3600,  # 1 час
                args=[schedule.id, db]
            )
            
            logger.info(f"Добавлено расписание {schedule.id} для {len(sheets)} таблиц")
            return job.id
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении расписания для нескольких таблиц: {str(e)}")
            return None
    
    def add_schedule(self, schedule: Schedule, db: Session) -> str:
        """
        Добавляет расписание в планировщик (для обратной совместимости)
        
        Args:
            schedule: Объект расписания
            db: Сессия базы данных
            
        Returns:
            ID задачи в планировщике
        """
        # Проверяем формат расписания
        if hasattr(schedule, 'sheets_ids') and isinstance(schedule.sheets_ids, list):
            # Новый формат с несколькими таблицами
            return self.add_multi_sheet_schedule(schedule, db)
        
        # Старый формат с одной таблицей
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
        def backup_job(schedule_id: str, db: Session):
            """
            Задача для создания бэкапа по расписанию
            """
            try:
                logger.info(f"Запуск бэкапа по расписанию {schedule_id}")
                
                # Получаем расписание из БД
                schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
                if not schedule:
                    logger.error(f"Расписание {schedule_id} не найдено")
                    return
                
                # Получаем информацию о таблице
                sheet = db.query(Sheet).filter(Sheet.id == schedule.sheet_id).first()
                if not sheet:
                    logger.error(f"Таблица {schedule.sheet_id} не найдена")
                    return
                
                # Создаем бэкап
                backup = create_backup(
                    sheet_id=sheet.id,
                    spreadsheet_id=sheet.spreadsheet_id,
                    sheet_name=sheet.name,
                    storage_configs=schedule.storage_configs,
                    db=db
                )
                
                if not backup:
                    logger.error(f"Не удалось создать бэкап для расписания {schedule_id}")
                    return
                
                logger.info(f"Бэкап по расписанию {schedule_id} успешно создан")
                
            except Exception as e:
                logger.error(f"Ошибка при выполнении бэкапа по расписанию {schedule_id}: {str(e)}")
                logger.exception(e)
        
        # Добавляем задачу в планировщик
        job = self.scheduler.add_job(
            backup_job,
            trigger=trigger,
            id=f"backup_{schedule.id}",
            replace_existing=True,
            misfire_grace_time=3600,  # 1 час
            args=[schedule.id, db]
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
            # Проверяем формат расписания
            if hasattr(schedule, 'sheets_ids') and isinstance(schedule.sheets_ids, list):
                return self.add_multi_sheet_schedule(schedule, db)
            else:
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
            # Проверяем формат расписания
            if hasattr(schedule, 'sheets_ids') and isinstance(schedule.sheets_ids, list):
                scheduler_service.add_multi_sheet_schedule(schedule, db)
            else:
                scheduler_service.add_schedule(schedule, db)
        
        logger.info(f"Инициализировано {len(schedules)} расписаний")
    
    except Exception as e:
        logger.error(f"Ошибка при инициализации расписаний: {str(e)}")


def cleanup():
    """Очищает ресурсы планировщика при остановке приложения"""
    scheduler_service.shutdown() 
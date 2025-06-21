# Архитектура проекта Backup Google Sheets

## Общее описание
Приложение для автоматического создания резервных копий таблиц Google Sheets с веб-интерфейсом управления и модульной системой хранения.

## Структура проекта

### Корневые файлы
- `Dockerfile` - конфигурация Docker контейнера для развертывания приложения
- `docker-compose.yml` - оркестрация Docker контейнера с настройками окружения
- `.dockerignore` - исключения файлов при сборке Docker образа
- `entrypoint.sh` - скрипт инициализации контейнера с проверкой директорий
- `pyproject.toml` - конфигурация проекта и зависимостей
- `requirements.txt` - список зависимостей Python
- `README.md` - документация проекта

### Директория app/
Основной код приложения FastAPI

#### app/main.py
Точка входа FastAPI приложения, настройка роутов и middleware:
- Веб-страницы (/, /sheets, /backups, /schedules, /integrations)
- Health check endpoint (/health) для мониторинга
- Настройка CORS и статических файлов
- Инициализация базы данных и планировщика при запуске

#### app/core/
Основные компоненты системы:
- `config.py` - конфигурация приложения и переменные окружения
- `scheduler.py` - планировщик задач для автоматических бэкапов
- `sheets_service.py` - сервис для работы с Google Sheets API

#### app/api/
REST API эндпоинты:
- `api_v1/api.py` - главный роутер API
- `endpoints/backups.py` - управление бэкапами
- `endpoints/sheets.py` - управление таблицами
- `endpoints/schedules.py` - управление расписаниями
- `endpoints/integrations.py` - управление интеграциями
- `endpoints/storage.py` - управление хранилищами
- `deps.py` - зависимости для DI

#### app/models/
SQLAlchemy модели базы данных:
- `sheet.py` - модель таблицы Google Sheets
- `backup.py` - модель бэкапа
- `schedule.py` - модель расписания
- `backup_schedule.py` - связь бэкапов и расписаний
- `integration.py` - модель интеграций

#### app/schemas/
Pydantic схемы для валидации данных:
- Соответствующие схемы для каждой модели
- `bitrix.py` - схемы для интеграции с Bitrix24

#### app/services/
Бизнес-логика приложения:
- `backup_service.py` - сервис создания бэкапов
- `google_service.py` - сервис работы с Google API
- `integration_service.py` - сервис интеграций
- `schedule_service.py` - сервис управления расписаниями
- `storage/` - модульная система хранения бэкапов

#### app/db/
Настройка базы данных:
- `base.py` - базовые настройки SQLAlchemy
- `session.py` - сессии базы данных
- `init_db.py` - инициализация базы данных

### Директории данных
- `backups/` - локальное хранение бэкапов
- `credentials/` - JSON ключи сервисных аккаунтов Google
- `data/` - временные данные
- `sqlite/` - файлы базы данных SQLite

### Веб-интерфейс
- `templates/` - HTML шаблоны Jinja2
- `static/` - CSS и JavaScript файлы

## Docker конфигурация

### Dockerfile
- Базовый образ: Python 3.12-slim
- Установка системных зависимостей (gcc, curl)
- Установка uv для управления зависимостями Python
- Создание непривилегированного пользователя app
- Создание необходимых директорий с правильными правами доступа
- Entrypoint скрипт для проверки готовности системы
- Открытие порта 8000
- Healthcheck для мониторинга

### docker-compose.yml
- Сборка из локального Dockerfile
- Монтирование томов для данных
- Настройка переменных окружения
- Автоматический перезапуск
- Healthcheck конфигурация

### Переменные окружения
- `DATABASE_URL` - путь к базе данных SQLite (sqlite:////app/sqlite/data/app.db)
- `GOOGLE_CREDENTIALS_PATH` - путь к JSON ключу сервисного аккаунта
- `SCHEDULER_TIMEZONE` - часовой пояс для планировщика
- `BITRIX24_*` - настройки интеграции с Bitrix24

### Решение проблем
#### Ошибка "unable to open database file"
- Создан entrypoint.sh скрипт для проверки существования директорий
- Исправлены права доступа к директории sqlite
- Использован абсолютный путь к базе данных в docker-compose.yml

#### Ошибка "GET /health HTTP/1.1" 404 Not Found
- Добавлен health check endpoint в app/main.py
- Endpoint проверяет состояние базы данных и возвращает статус приложения
- Используется Docker healthcheck для мониторинга контейнера

## Команды запуска

### Локальная разработка
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker
```bash
# Сборка и запуск
docker-compose up --build

# Запуск в фоне
docker-compose up -d

# Остановка
docker-compose down
``` 
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.core.config import settings
from app.api.api_v1.api import api_router
from app.core.scheduler import init_schedules, cleanup
from app.api.deps import get_db

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG,
    default_response_class=JSONResponse,
    json_encoder=None
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_encoding_headers(request, call_next):
    """
    Middleware для установки правильных заголовков кодировки
    """
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настраиваем шаблоны
templates = Jinja2Templates(directory="templates")

# Включаем маршруты API
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def index(request: Request):
    """
    Главная страница приложения
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/sheets")
async def sheets_page(request: Request):
    """
    Страница таблиц
    """
    return templates.TemplateResponse("sheets.html", {"request": request})

@app.get("/backups")
async def backups_page(request: Request):
    """
    Страница бэкапов
    """
    return templates.TemplateResponse("backups.html", {"request": request})

@app.get("/schedules")
async def schedules_page(request: Request):
    """
    Страница расписаний
    """
    return templates.TemplateResponse("schedules.html", {"request": request})

@app.get("/integrations")
async def integrations_page(request: Request):
    """
    Страница интеграций
    """
    return templates.TemplateResponse("integrations.html", {"request": request})

@app.get("/health")
async def health_check():
    """
    Health check endpoint для мониторинга состояния приложения
    """
    try:
        # Проверяем подключение к базе данных
        db = next(get_db())
        # Простой запрос для проверки БД
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "version": settings.VERSION,
        "app_name": settings.APP_NAME
    }

@app.on_event("startup")
def startup_db_and_scheduler():
    """
    Инициализация при запуске приложения
    """
    # Инициализация базы данных
    from app.db.init_db import init_db
    db = next(get_db())
    init_db(db)
    
    # Инициализация расписаний
    init_schedules(db)

@app.on_event("shutdown")
async def shutdown_event():
    """
    Очистка при остановке приложения
    """
    cleanup()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 
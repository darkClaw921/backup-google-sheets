from fastapi import APIRouter

from app.api.api_v1.endpoints import sheets, backups, schedules, storage, integrations

api_router = APIRouter()

api_router.include_router(sheets.router, prefix="/sheets", tags=["sheets"])
api_router.include_router(backups.router, prefix="/backups", tags=["backups"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(storage.router, prefix="/storage", tags=["storage"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
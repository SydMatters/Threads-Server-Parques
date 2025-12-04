from fastapi import APIRouter, Depends

from app.core.settings import Settings
from app.deps import get_settings_dep

router = APIRouter()


@router.get("/")
def health(settings: Settings = Depends(get_settings_dep)) -> dict:
    return {"status": "ok", "app": settings.app_name}

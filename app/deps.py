from typing import Generator

from sqlalchemy.orm import Session

from app.core.settings import Settings, get_settings
from app.db.session import SessionLocal
from app.services.game_manager import GameManager, get_game_manager


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_settings_dep() -> Settings:
    return get_settings()


def get_game_manager_dep() -> GameManager:
    return get_game_manager()

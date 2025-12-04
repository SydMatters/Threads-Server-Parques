from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings
from database.players import Base

settings = get_settings()

engine = create_engine(settings.database_url, echo=settings.debug, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create DB tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

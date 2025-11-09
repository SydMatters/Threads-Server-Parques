from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .players import Base

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
  Base.metadata.create_all(bind=engine)

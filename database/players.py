from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Player(Base):
  __tablename__ = 'players'

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String, unique=True, index=True)
  score = Column(Integer, default=0)
  age = Column(Integer)
  password = Column(String)
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    user = Column(String)
    params = Column(String)
    status = Column(String, default="pending")
    result = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

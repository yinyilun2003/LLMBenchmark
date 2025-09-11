# models/user.py
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base  # 你需要在 models/base.py 定义 Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)

    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系字段（可选，用于反向关联任务）
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(username={self.username}, email={self.email}, active={self.is_active})>"

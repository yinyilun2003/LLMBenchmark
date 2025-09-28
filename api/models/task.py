# api/models/task.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship

from api.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    # 使用通用 String(36) 存 UUID，保证在 SQLite/PG 都可用
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # 关联用户
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 任务元数据
    name = Column(String(200), nullable=False)
    model = Column(String(100), nullable=False)     # e.g. llama3-8b, qwen3-7b, gemini-2.0
    route = Column(String(200), nullable=False)     # HTTP endpoint or logical route
    dataset = Column(String(200), nullable=False)

    # 执行参数
    params = Column(JSON, nullable=False, default=dict)   # 任意适配器参数
    concurrency = Column(Integer, nullable=False, default=1)
    duration_sec = Column(Integer, nullable=False, default=60)

    # 状态与标签
    status = Column(String(32), nullable=False, default="queued")  # 与 TaskStatus 枚举对应
    tags = Column(JSON, nullable=False, default=list)              # 存字符串列表

    # 时间线
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # 错误信息（若失败）
    error = Column(Text, nullable=True)

    # 反向关系
    user = relationship("User", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task id={self.id} user_id={self.user_id} name={self.name} status={self.status}>"

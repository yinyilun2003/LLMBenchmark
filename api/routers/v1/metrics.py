# api/models/metric.py
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from api.models.base import Base
from fastapi import APIRouter
router = APIRouter(prefix="/metrics", tags=["Metrics"])


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    latency_ms = Column(Integer, nullable=True)
    http_status = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    quality = Column(Float, nullable=True)
    error = Column(Text, nullable=True)

    task = relationship("Task", back_populates="metrics", lazy="joined", viewonly=True)

    __table_args__ = (Index("ix_metrics_task_ts", "task_id", "ts"),)

    def __repr__(self) -> str:
        return f"<Metric task_id={self.task_id} ts={self.ts} latency={self.latency_ms} status={self.http_status}>"

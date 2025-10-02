# api/models/dataset.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON as JSON_GENERIC  # for SQLite/MySQL fallback

from api.models.base import Base

# choose JSON type compatible with current dialect
try:
    JSONType = JSONB  # works on PostgreSQL
except Exception:
    JSONType = JSON_GENERIC  # fallback


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(200), nullable=False, index=True)
    storage_uri = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSONType, nullable=False, default=list)  # list[str]

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relations
    user = relationship("User", back_populates="datasets", viewonly=True)
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_datasets_user_name", "user_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} name={self.name} owner={self.user_id}>"


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)

    version = Column(String(100), nullable=False, index=True)  # e.g., v1, 2024-09-01, sha123
    storage_uri = Column(String(512), nullable=True)           # default to parent if None at write time
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # relations
    dataset = relationship("Dataset", back_populates="versions")

    __table_args__ = (
        Index("ix_dataset_versions_ds_ver", "dataset_id", "version", unique=True),
    )

    def __repr__(self) -> str:
        return f"<DatasetVersion ds={self.dataset_id} ver={self.version}>"

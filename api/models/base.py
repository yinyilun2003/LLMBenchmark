# models/base.py
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# Alembic-friendly naming conventions for constraints and indexes
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Project-wide SQLAlchemy Declarative Base."""
    metadata = metadata


# Optional helper to create tables in dev/local
def create_all():
    """Create all tables using the engine from core.db (lazy import to avoid cycles)."""
    from core.db import engine  # lazy import prevents circular dependency
    Base.metadata.create_all(bind=engine)


__all__ = ["Base", "metadata", "create_all"]

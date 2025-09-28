import os
import psycopg2
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:devpass@localhost:5432/postgres",
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖，按需获取会话，确保请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping() -> bool:
    """轻量连通性检查。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# 可选：设置 DB_EAGER_PING=1 时在启动时输出一次连通性状态
if os.getenv("DB_EAGER_PING") == "1":
    print(f"[core.db] DATABASE_URL={DATABASE_URL}")
    print("[core.db] connect to db successfully!" if ping() else "[core.db] db not reachable")
    

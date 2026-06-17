"""
数据库配置和会话管理
使用 SQLite + SQLAlchemy
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 确保 data 目录存在
os.makedirs("data", exist_ok=True)

# SQLite 数据库文件位于 data/analyses.db
DATABASE_URL = "sqlite:///./data/analyses.db"

# SQLite 需要 check_same_thread=False 以支持多线程访问
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # 设为 True 可查看 SQL 日志
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话的依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
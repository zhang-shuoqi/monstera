"""SQLite + SQLAlchemy 连接与会话管理"""
import logging
import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

import config

log = logging.getLogger("monstera.database")

os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)

engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 15},
)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_conn, _):
    """并发保护：WAL 模式（读写不互斥）+ 忙等 15 秒（而非立即报 database is locked）"""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=15000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# 需要禁止 id 复用的表（存在"删除后新建"的用法，id 复用会导致数据错乱）
_AUTOINCREMENT_TABLES = ("user_apis", "conversations", "usage_logs")


def _add_missing_columns(insp):
    """为旧库补充缺失列（SQLite 的 ALTER TABLE ADD COLUMN）"""
    with engine.begin() as conn:
        cols = [c["name"] for c in insp.get_columns("user_apis")]
        if "latency_ms" not in cols:
            conn.execute(text("ALTER TABLE user_apis ADD COLUMN latency_ms INTEGER"))
        if "last_check_at" not in cols:
            conn.execute(text("ALTER TABLE user_apis ADD COLUMN last_check_at DATETIME"))
        if "conversations" in insp.get_table_names():
            ccols = [c["name"] for c in insp.get_columns("conversations")]
            if "pinned" not in ccols:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN pinned BOOLEAN DEFAULT 0"))
        if "providers" in insp.get_table_names():
            pcols = [c["name"] for c in insp.get_columns("providers")]
            if "balance_url" not in pcols:
                conn.execute(text("ALTER TABLE providers ADD COLUMN balance_url VARCHAR"))
            if "recharge_url" not in pcols:
                conn.execute(text("ALTER TABLE providers ADD COLUMN recharge_url VARCHAR"))
        if "models" in insp.get_table_names():
            mcols = [c["name"] for c in insp.get_columns("models")]
            if "vision" not in mcols:
                conn.execute(text("ALTER TABLE models ADD COLUMN vision BOOLEAN DEFAULT 0"))
        if "messages" in insp.get_table_names():
            mcols = [c["name"] for c in insp.get_columns("messages")]
            if "images" not in mcols:
                conn.execute(text("ALTER TABLE messages ADD COLUMN images TEXT"))


def _rebuild_for_autoincrement():
    """SQLite 的 AUTOINCREMENT 只能在建表时指定。
    对缺少 AUTOINCREMENT 的旧表做一次保数据重建（rename → create → copy → drop），
    保证删除过的 id 永不复用。
    使用原生 sqlite3 连接：迁移期间需关闭外键检查并启用 legacy_alter_table
    （否则 RENAME 会自动改写引用方 FK 子句，导致 DROP 旧表失败或 FK 悬空）。"""
    import sqlite3
    from sqlalchemy.schema import CreateTable

    log.info("检测到旧版表结构，开始 AUTOINCREMENT 迁移（表：%s）", ", ".join(_AUTOINCREMENT_TABLES))
    raw = sqlite3.connect(config.DB_PATH)
    try:
        raw.execute("PRAGMA foreign_keys=OFF")
        raw.execute("PRAGMA legacy_alter_table=ON")
        raw.isolation_level = None  # 手动事务
        raw.execute("BEGIN IMMEDIATE")
        for tname in _AUTOINCREMENT_TABLES:
            row = raw.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tname,)
            ).fetchone()
            if not row or not row[0]:
                continue  # 表不存在，create_all 会新建
            if "AUTOINCREMENT" in row[0].upper():
                continue  # 已是新版表
            ddl = str(CreateTable(Base.metadata.tables[tname]).compile(engine)).strip()
            tmp = f"{tname}__old"
            cols = [c.name for c in Base.metadata.tables[tname].columns]
            collist = ", ".join(f'"{c}"' for c in cols)
            raw.execute(f'ALTER TABLE "{tname}" RENAME TO "{tmp}"')
            raw.execute(ddl)
            raw.execute(f'INSERT INTO "{tname}" ({collist}) SELECT {collist} FROM "{tmp}"')
            raw.execute(f'DROP TABLE "{tmp}"')
        raw.execute("COMMIT")
    finally:
        try:
            raw.execute("PRAGMA legacy_alter_table=OFF")
        finally:
            raw.close()


def _create_indexes():
    """补建查询索引（幂等）：日志按厂商+日期统计、按 API 级联删除、消息按对话加载"""
    stmts = [
        "CREATE INDEX IF NOT EXISTS ix_usage_logs_provider_created ON usage_logs (provider_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_usage_logs_api ON usage_logs (api_id)",
        "CREATE INDEX IF NOT EXISTS ix_messages_conversation ON messages (conversation_id)",
        "CREATE INDEX IF NOT EXISTS ix_memory_docs_conversation ON memory_docs (conversation_id)",
    ]
    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))


def init_db():
    """自动创建所有表并执行轻量迁移"""
    import models  # noqa: F401 确保模型已注册
    from sqlalchemy import inspect

    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    if "user_apis" in insp.get_table_names():
        _add_missing_columns(insp)
        _rebuild_for_autoincrement()
    _create_indexes()
    config.ensure_memory_dir()  # 确保记忆文档目录存在


def get_db():
    """FastAPI 依赖：请求级数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

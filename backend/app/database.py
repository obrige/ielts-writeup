from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from .config import settings

# 每个 Celery task 独立 event loop。async engine connection 绑 loop 会跨 task 错配。
# 用 NullPool 每次新建连接，避免 stale connection 跨 task 复用。
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,    # 不用 pool：每次新连接，避免跨 event loop 错配
    pool_pre_ping=True,    # 借出连接前 PING 验证（防 MySQL 8h wait_timeout）
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase): pass

async def get_db():
    async with SessionLocal() as s:
        yield s
import re
# ============================================================
# Bug #11 TODO: _auto_migrate() 多容器并发 ALTER 风险未修复
# 原 Bug: backend + worker 容器同时启动, 都跑 auto-migrate, ALTER TABLE 互相 metadata lock
# 暂未实现 MySQL GET_LOCK 互斥 (修复方案见 _archive/_fix*.py)
# 临时缓解: docker-compose.yml 里 worker depends_on backend healthy
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from . import models  # noqa
from .routers import auth, users, admin, models as model_routes, grading, reports
from .config import settings

app = FastAPI(title="IELTS 写作批改系统", version="1.1.0")
# Bug #26: CORS 收紧 (默认只允许 localhost:3000, 通过 ALLOWED_ORIGINS 环境变量扩展)
import os as _os
_allowed_raw = _os.environ.get("ALLOWED_ORIGINS", "").strip()
if not _allowed_raw:
    # Bug #18 fix: 空配置给默认, 不要给空列表导致前端连不上
    _allowed = ["http://localhost:3000", "http://127.0.0.1:3000"]
else:
    _allowed = [o.strip() for o in _allowed_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
    allow_credentials=False,
)
for r in (auth.router, users.router, admin.router, model_routes.router, grading.router, reports.router):
    app.include_router(r, prefix="/api")


@app.on_event("startup")
async def startup():
    await _init_db(retries=30, delay=2)
    await _auto_migrate()
    await _seed_admin()
    await _check_security()


async def _init_db(retries=30, delay=2):
    import asyncio
    for i in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception:
            if i == retries - 1:
                raise
            await asyncio.sleep(delay)


async def _auto_migrate():
    """Auto-add missing columns to existing tables (ALTER TABLE)."""
    from sqlalchemy import text, inspect
    from .models import User, ModelConfig, GradingJob, RechargeLog, InviteCode, RedeemCode

    # Define expected columns: {table: [(col_name, col_type_sql)]}
    migrations = {
        "users": [
            ("email", "VARCHAR(128)"),
            ("disabled", "BOOLEAN DEFAULT 0"),
        ],
        # grading_jobs 第一处注释版本已合并到下面
        # "grading_jobs_old_comment": "旧 result 列类型为 JSON (65KB)，如需扩为 MEDIUMTEXT 手动执行: ALTER TABLE grading_jobs MODIFY `result` MEDIUMTEXT",

        "model_configs": [
            ("is_default", "BOOLEAN DEFAULT 0"),
            ("priority", "INT DEFAULT 0"),
            ("fallback_models", "JSON"),
            ("search_off", "JSON"),
            ("is_text", "BOOLEAN DEFAULT 1"),
            ("label", "VARCHAR(128)"),
            ("tags", "JSON"),
        ],
        "grading_jobs": [
            ("cost_credits", "INT DEFAULT 1"),
            ("error", "TEXT"),
            ("finished_at", "DATETIME"),
            ("title", "VARCHAR(128)"),
            ("label", "VARCHAR(128)"),
            ("tags", "JSON"),
            ("grading_result", "MEDIUMTEXT"),  # 列名从 result 改成 grading_result
        ],
    }

    async with engine.begin() as conn:
        for table_name, cols in migrations.items():
            # Check if table exists
            def table_exists_sync(conn):
                ins = inspect(conn)
                return table_name in ins.get_table_names()
            exists = await conn.run_sync(table_exists_sync)
            if not exists:
                continue

            # Get existing column names
            def get_columns_sync(conn):
                ins = inspect(conn)
                return [c["name"] for c in ins.get_columns(table_name)]
            existing = await conn.run_sync(get_columns_sync)








            # 列重命名：旧 result 列 → 新 grading_result
            if table_name == "grading_jobs":
                try:
                    await conn.execute(text("ALTER TABLE `grading_jobs` CHANGE COLUMN `result` `grading_result` MEDIUMTEXT"))
                    print("[migrate] Renamed column grading_jobs.result to grading_result")
                except Exception:
                    pass  # 列已不存在/已是新名
            for col_name, col_type in cols:
                if col_name not in existing:
                    try:
                        await conn.execute(text(
                            f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_type}"
                        ))
                        print(f"[migrate] Added column {table_name}.{col_name}")
                    except Exception as e:
                        print(f"[migrate] Failed to add {table_name}.{col_name}: {e}")


async def _check_security():
    """严格校验 JWT_SECRET: 非默认 + 长度>=32 + 至少 2 种字符类"""
    raw = settings.JWT_SECRET or ""
    norm = raw.strip().lower()
    if norm == "" or norm == "change-me" or norm == "changeme":
        raise RuntimeError(
            "Set JWT_SECRET in .env (>= 32 chars). Generate: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

    if len(raw) < 32:
        raise RuntimeError("[SECURITY FATAL] JWT_SECRET 长度 < 32 字符, 不安全")
    classes = sum(bool(re.search(p, raw)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^a-zA-Z0-9]"))
    if classes < 2:
        raise RuntimeError("[SECURITY FATAL] JWT_SECRET 必须包含至少 2 种字符类 (大小写字母/数字/符号)")
    import logging
    logging.getLogger(__name__).info("JWT_SECRET strength OK (len=%d, classes>=%d)", len(raw), classes)

async def _seed_admin():
    from .database import SessionLocal
    from .models import User
    from .auth import hash_pw
    from .config import settings
    from sqlalchemy import select
    async with SessionLocal() as db:
        exists = (await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))).scalar_one_or_none()
        if not exists:
            db.add(User(username=settings.ADMIN_USERNAME, email=settings.ADMIN_EMAIL,
                        password_hash=hash_pw(settings.ADMIN_PASSWORD), role="admin", credits=9999))
            await db.commit()

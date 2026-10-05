from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import User, InviteCode
from ..schemas import Token, LoginReq, RegisterReq, ChangePasswordReq
from ..auth import hash_pw, verify_pw, create_token
from ..deps import get_current_user
from datetime import datetime, timezone

import redis.asyncio as _redis_async
from ..config import settings as _s
_router_redis = None
def _get_router_redis():
    global _router_redis
    if _router_redis is None:
        _router_redis = _redis_async.from_url(_s.REDIS_URL)
    return _router_redis

async def _rate_limit_login(username: str, ip: str):
    """Bug #5 fix: 登录限流, 10 次/分钟/IP+账号。"""
    try:
        r = _get_router_redis()
        k = f"login_rl:{username}:{ip}"
        cur = await r.incr(k)
        if cur == 1:
            await r.expire(k, 60)
        if cur > 10:
            raise HTTPException(429, "尝试次数过多, 请稍后再试")
    except HTTPException:
        raise
    except Exception:
        import logging
        logging.getLogger(__name__).warning("login rate-limit check failed")

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
async def login(req: LoginReq, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    await _rate_limit_login(req.username, ip)
    user = (await db.execute(select(User).where(User.username == req.username))).scalar_one_or_none()
    if not user or not verify_pw(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    if user.disabled:
        raise HTTPException(403, "账号已被禁用")
    return {"access_token": create_token(user), "role": user.role, "username": user.username}

@router.post("/register")
async def register(req: RegisterReq, db: AsyncSession = Depends(get_db)):

    inv = (await db.execute(
        select(InviteCode).where(InviteCode.code == req.invite_code).with_for_update()
    )).scalar_one_or_none()
    # Bug #35 fix: 合并两种邀请码错误消息, 防攻击者探测邀请码状态
    if not inv or inv.used_by is not None:
        raise HTTPException(400, "邀请码无效")
    # 用户名查重 (Bug 修复: 加行锁防并发重名注册)
    existing_user = (await db.execute(
        select(User).where(User.username == req.username).with_for_update()
    )).scalar_one_or_none()
    if existing_user:
        raise HTTPException(400, "用户名已存在")
    user = User(username=req.username, email=req.email, password_hash=hash_pw(req.password), credits=0)
    db.add(user)
    await db.flush()
    inv.used_by = user.id
    inv.used_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}

@router.post("/change-password")
async def change_password(req: ChangePasswordReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_pw(req.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    user.password_hash = hash_pw(req.new_password)
    await db.commit()
    return {"ok": True}

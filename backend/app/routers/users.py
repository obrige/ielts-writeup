from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..deps import get_current_user
from ..models import User, RedeemCode
from ..schemas import UpdateEmailReq, RedeemReq
from datetime import datetime, timezone

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "role": user.role, "credits": user.credits}

@router.put("/email")
async def update_email(req: UpdateEmailReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.email = req.email
    await db.commit()
    return {"ok": True, "email": user.email}

@router.post("/redeem")
async def redeem_code(req: RedeemReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Bug #10: 加 SELECT FOR UPDATE 行锁，防 TOCTOU 并发刷码
    code = (await db.execute(
        select(RedeemCode).where(RedeemCode.code == req.code).with_for_update()
    )).scalar_one_or_none()
    if not code:
        raise HTTPException(400, "兑换码无效")
    if code.used_by is not None:
        raise HTTPException(400, "兑换码已被使用")
    # 同时给 user 也加锁（防用户级并发）
    user_locked = (await db.execute(
        select(User).where(User.id == user.id).with_for_update()
    )).scalar_one_or_none()
    if not user_locked:
        raise HTTPException(404, "用户不存在")
    user_locked.credits += code.credits
    code.used_by = user.id
    code.used_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "credits": user_locked.credits, "added": code.credits}
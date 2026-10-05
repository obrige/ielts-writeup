from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .auth import decode_token
from .models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")  # Bug #4: Swagger UI

async def get_current_user(token: str = Depends(oauth2), db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(401, "登录已失效")
    user = await db.get(User, user_id)
    if not user or user.disabled:
        raise HTTPException(401, "用户不存在或已禁用")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user
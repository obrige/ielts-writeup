import hashlib
import hmac
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..deps import get_current_user
from ..models import GradingJob, User
from ..config import settings

# HTML 报告生成端点 (GET /{job_id}) 已整体移除:
# 原实现调用了不存在的 _render_for_job (死代码, 激活即 500)。
# 本文件只保留临时下载 token 机制, 供 /grading/{id}/radar-data 与
# /grading/{id}/image 两个端点做免 Authorization 的短时访问鉴权。

router = APIRouter(prefix="/reports", tags=["reports"])

DOWNLOAD_TOKEN_TTL = 300


def make_download_token(user_id: int, job_id: int) -> str:
    expiry = int(time.time()) + DOWNLOAD_TOKEN_TTL
    msg = f"{user_id}:{job_id}:{expiry}".encode()
    sig = hmac.new(settings.JWT_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return f"{user_id}:{job_id}:{expiry}:{sig}"


def verify_download_token(token: str, job_id: int) -> int:
    try:
        parts = token.split(":")
        if len(parts) != 4:
            raise ValueError("invalid format")
        user_id_t, job_id_t, expiry_t, sig_t = parts
        if int(job_id_t) != job_id:
            raise ValueError("job mismatch")
        if int(expiry_t) < int(time.time()):
            raise ValueError("expired")
        msg = f"{user_id_t}:{job_id_t}:{expiry_t}".encode()
        expected_sig = hmac.new(settings.JWT_SECRET.encode(), msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_t, expected_sig):
            raise ValueError("bad signature")
        return int(user_id_t)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(401, "Invalid or expired download token")


@router.get("/{job_id}/download-token")
async def get_download_token(
    job_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(GradingJob, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "任务不存在")
    if job.status != "done":
        raise HTTPException(400, "报告尚未生成")
    token = make_download_token(user.id, job_id)
    return {"token": token, "expires_in": DOWNLOAD_TOKEN_TTL}

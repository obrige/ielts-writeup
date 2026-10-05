import json










def _clean_title(t):
    """从 JSON dict 或 Python dict repr 字符串中提取 title 字段"""
    if not t:
        return ""
    s = str(t).strip()
    if s.startswith(chr(123)):
        # 优先 JSON 解析 (双引号)
        try:
            import json as _json
            d = _json.loads(s)
            return d.get("title", s)
        except Exception:
            # 退而求其次: Python dict repr (单引号)
            try:
                import ast as _ast
                d = _ast.literal_eval(s)
                return d.get("title", s)
            except Exception:
                return s
    return s

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..deps import require_admin
from ..models import User, RechargeLog, RefundLog, InviteCode, RedeemCode, GradingJob, ModelConfig
from ..config import settings
from ..schemas import RechargeReq, ResetPasswordReq, GenerateInviteReq, GenerateRedeemReq, ModelUpdateReq, SettingsUpdate

from ..auth import hash_pw, generate_code
from datetime import datetime, timezone

def safe_json_loads(s, default=None):
    """Bug: 防御性 json.loads, 损坏数据返回 default"""
    if not s: return default if default is not None else {}
    try: return json.loads(s)
    except (json.JSONDecodeError, TypeError): return default if default is not None else {}


router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users")
async def users(_=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(User).order_by(User.id))).scalars().all()
    return [{"id": u.id, "username": u.username, "email": u.email, "role": u.role,
             "credits": u.credits, "disabled": u.disabled} for u in rows]

@router.post("/recharge")
async def recharge(req: RechargeReq, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, req.user_id)
    if not user: return {"ok": False, "msg": "用户不存在"}
    user.credits += req.amount
    db.add(RechargeLog(user_id=req.user_id, amount=req.amount, admin_id=admin.id))
    await db.commit()
    return {"ok": True, "credits": user.credits}

@router.post("/reset-password")
async def reset_password(req: ResetPasswordReq, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, req.user_id)
    if not user: raise HTTPException(404, "用户不存在")
    user.password_hash = hash_pw(req.new_password)
    await db.commit()
    return {"ok": True}

@router.post("/toggle-disable")
async def toggle_disable(user_id: int, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user: raise HTTPException(404, "用户不存在")
    if user.id == admin.id: raise HTTPException(400, "不能禁用自己")
    user.disabled = not user.disabled
    await db.commit()
    return {"ok": True, "disabled": user.disabled}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete as sa_delete
    import os
    user = await db.get(User, user_id)
    if not user: raise HTTPException(404, "用户不存在")
    if user.id == admin.id: raise HTTPException(400, "不能删除自己")
    if user.role == "admin": raise HTTPException(400, "不能删除管理员")

    try:
        # Bug 修复: 先收集图片, 用单条 SQL 删 jobs (避免 N+1)
        jobs = (await db.execute(select(GradingJob.image_path).where(GradingJob.user_id == user_id))).scalars().all()
        await db.execute(sa_delete(GradingJob).where(GradingJob.user_id == user_id))
        await db.execute(sa_delete(RechargeLog).where(RechargeLog.user_id == user_id))
        await db.execute(sa_delete(RefundLog).where(RefundLog.user_id == user_id))
        await db.execute(sa_delete(InviteCode).where(InviteCode.created_by == user_id))
        await db.execute(sa_delete(RedeemCode).where(RedeemCode.created_by == user_id))
        from sqlalchemy import update as sa_update
        await db.execute(sa_update(InviteCode).where(InviteCode.used_by == user_id).values(used_by=None, used_at=None))
        await db.execute(sa_update(RedeemCode).where(RedeemCode.used_by == user_id).values(used_by=None, used_at=None))
        await db.delete(user)
        await db.commit()
        # 事务提交后再删图片文件, 避免 DB 回滚但文件已删的不一致
        for img in jobs:
            if img and os.path.exists(img):
                try: os.remove(img)
                except: pass
    except Exception:
        await db.rollback()
        raise
    return {"ok": True}

@router.get("/grading")
async def all_grading(page: int = 1, page_size: int = 20, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    offset = (page - 1) * page_size
    q = select(GradingJob, User).join(User, GradingJob.user_id == User.id).order_by(GradingJob.id.desc()).offset(offset).limit(page_size)
    rows = (await db.execute(q)).all()
    total_q = select(func.count()).select_from(GradingJob)
    total = (await db.execute(total_q)).scalar()
    return {
        "items": [{"id": j.id, "user_id": j.user_id, "username": u.username,
                   "task_type": j.task_type, "status": j.status,
                   "predicted_band": (safe_json_loads(j.grading_result) if j.grading_result else {}).get("predicted_band") if j.grading_result else None,
                   "title": _clean_title(j.title),
                   "question": j.question or "",
                   "created_at": j.created_at.isoformat() + "Z" if j.created_at else None} for j, u in rows],
        "total": total, "page": page, "page_size": page_size
    }

@router.delete("/grading/{job_id}")
async def delete_grading(job_id: int, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    import os
    job = await db.get(GradingJob, job_id)
    if not job: raise HTTPException(404, "记录不存在")
    if job.image_path and os.path.exists(job.image_path):
        try: os.remove(job.image_path)
        except: pass
    # 修复: RefundLog.job_id 有 FK 无级联, 先清退款记录再删 job
    from sqlalchemy import delete as _sa_delete
    from ..models import RefundLog as _RefundLog
    await db.execute(_sa_delete(_RefundLog).where(_RefundLog.job_id == job_id))
    await db.delete(job)
    await db.commit()
    return {"ok": True}

@router.post("/invite-codes")
async def generate_invites(req: GenerateInviteReq, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    codes = []
    for _ in range(req.count):
        c = generate_code(16)
        db.add(InviteCode(code=c, created_by=admin.id))
        codes.append(c)
    await db.commit()
    return {"codes": codes}

@router.get("/invite-codes")
async def list_invites(_=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(InviteCode).order_by(InviteCode.id.desc()))).scalars().all()
    return [{"id": r.id, "code": r.code, "created_by": r.created_by,
             "used_by": r.used_by, "used_at": r.used_at.isoformat() + "Z" if r.used_at else None,
             "created_at": r.created_at.isoformat() + "Z" if r.created_at else None} for r in rows]

@router.delete("/invite-codes/{code_id}")
async def delete_invite(code_id: int, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    inv = await db.get(InviteCode, code_id)
    if not inv: raise HTTPException(404, "邀请码不存在")
    if inv.used_by: raise HTTPException(400, "已使用的邀请码不能删除")
    await db.delete(inv)
    await db.commit()
    return {"ok": True}

@router.post("/redeem-codes")
async def generate_redeems(req: GenerateRedeemReq, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    codes = []
    for _ in range(req.count):
        c = generate_code(20)
        db.add(RedeemCode(code=c, credits=req.credits, created_by=admin.id))
        codes.append({"code": c, "credits": req.credits})
    await db.commit()
    return {"codes": codes}

@router.get("/redeem-codes")
async def list_redeems(_=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(RedeemCode).order_by(RedeemCode.id.desc()))).scalars().all()
    return [{"id": r.id, "code": r.code, "credits": r.credits, "created_by": r.created_by,
             "used_by": r.used_by, "used_at": r.used_at.isoformat() + "Z" if r.used_at else None,
             "created_at": r.created_at.isoformat() + "Z" if r.created_at else None} for r in rows]

@router.delete("/redeem-codes/{code_id}")
async def delete_redeem(code_id: int, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rc = await db.get(RedeemCode, code_id)
    if not rc: raise HTTPException(404, "兑换码不存在")
    if rc.used_by: raise HTTPException(400, "已使用的兑换码不能删除")
    await db.delete(rc)
    await db.commit()
    return {"ok": True}


@router.get("/settings")
async def get_settings(_=Depends(require_admin)):
    return {
        "LLM_TIMEOUT": int(settings.LLM_TIMEOUT),
        "LLM_MAX_TOKENS": int(settings.LLM_MAX_TOKENS),
        "LLM_MAX_RETRIES": int(settings.LLM_MAX_RETRIES),
        "GRADER_CONCURRENCY": int(getattr(settings, "GRADER_CONCURRENCY", 4)),
    }

@router.put("/settings")
async def update_settings(payload: SettingsUpdate, _=Depends(require_admin)):
    # Bug 修复: 用 SettingsUpdate schema 验证输入 (替代 dict)
    if payload.LLM_TIMEOUT is not None:
        settings.LLM_TIMEOUT = payload.LLM_TIMEOUT
    if payload.LLM_MAX_TOKENS is not None:
        settings.LLM_MAX_TOKENS = payload.LLM_MAX_TOKENS
    if payload.LLM_MAX_RETRIES is not None:
        settings.LLM_MAX_RETRIES = payload.LLM_MAX_RETRIES
    if payload.GRADER_CONCURRENCY is not None:
        settings.GRADER_CONCURRENCY = payload.GRADER_CONCURRENCY

    _fields = {"LLM_TIMEOUT": payload.LLM_TIMEOUT, "LLM_MAX_TOKENS": payload.LLM_MAX_TOKENS, "LLM_MAX_RETRIES": payload.LLM_MAX_RETRIES, "GRADER_CONCURRENCY": payload.GRADER_CONCURRENCY}
    for _k, _v in _fields.items():
        if _v is not None: setattr(settings, _k, _v)
    try:
        _env_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", ".env"))
        if os.path.exists(_env_path):
            with open(_env_path, "r", encoding="utf-8") as _ef:
                _lines = _ef.readlines()
            _idx_map = {ln.split("=", 1)[0]: i for i, ln in enumerate(_lines) if "=" in ln and not ln.strip().startswith("#")}
            for _k, _v in _fields.items():
                if _v is None: continue
                _line = f"{_k}={_v}" + chr(10)
                if _k in _idx_map: _lines[_idx_map[_k]] = _line
                else: _lines.append(_line)
            with open(_env_path, "w", encoding="utf-8") as _ef:
                _ef.writelines(_lines)
    except Exception as _e:
        import logging
        logging.getLogger(__name__).warning("persist settings to .env failed: %s", _e)
    return {"ok": True, "LLM_TIMEOUT": int(settings.LLM_TIMEOUT), "LLM_MAX_TOKENS": int(settings.LLM_MAX_TOKENS), "LLM_MAX_RETRIES": int(settings.LLM_MAX_RETRIES), "GRADER_CONCURRENCY": int(settings.GRADER_CONCURRENCY)}

def safe_json_loads(s, default=None):
    """Bug: 防御性 json.loads, 损坏数据返回 default"""
    if not s: return default if default is not None else {}
    try: return json.loads(s)
    except (json.JSONDecodeError, TypeError): return default if default is not None else {}

import json
import os, uuid
def _clean_title(t):
    """从 JSON dict 或 Python dict repr 字符串中提取 title 字段"""
    if not t:
        return ""
    s = str(t).strip()
    if s.startswith(chr(123)):
        try:
            d = json.loads(s)
            return d.get("title", s)
        except Exception:
            try:
                import ast as _ast
                d = _ast.literal_eval(s)
                return d.get("title", s)
            except Exception:
                return s
    return s
from fastapi import Request, APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response  # Curio Bug #B: radar 需要 Response
from jose import jwt
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..deps import get_current_user
from ..models import User, GradingJob
from ..credits import charge
from ..config import settings
from ..tasks import grade_task
from .. import prompts, llm
from ..database import SessionLocal  # Bug #3
from .reports import verify_download_token  # Bug #3

router = APIRouter(prefix="/grading", tags=["grading"])

@router.post("/submit")
async def submit(task_type: str = Form(...), question: str = Form(...), essay: str = Form(...),
                 image: UploadFile = File(None),
                 user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if task_type not in ("task1", "task2"):
        raise HTTPException(400, "task_type 必须是 task1 或 task2")
    # 阻断 DoS / 超长 submission
    if len(question) > 5000:
        raise HTTPException(400, "题目过长（最多 5000 字符）")
    if len(essay) > settings.MAX_ESSAY_CHARS:
        raise HTTPException(400, f"作文字数过多（最多 {settings.MAX_ESSAY_CHARS} 字符）")

    image_bytes = None
    ext = None
    if image and task_type == "task1":
        image_bytes = await image.read()
        if len(image_bytes) > settings.MAX_IMAGE_BYTES:
            raise HTTPException(400, f"图片过大（最多 {settings.MAX_IMAGE_BYTES // (1024*1024)} MB）")
        ext = os.path.splitext(image.filename or "")[1] or ".png"
    await charge(db, user.id)
    job = GradingJob(user_id=user.id, task_type=task_type, question=question, essay=essay, cost_credits=settings.GRADING_COST)
    db.add(job); await db.commit(); await db.refresh(job)
    image_path = None
    if image_bytes is not None:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        temp_path = os.path.join(settings.UPLOAD_DIR, "tmp_" + uuid.uuid4().hex + ext)
        with open(temp_path, "wb") as f:
            f.write(image_bytes)
        image_path = temp_path
        job.image_path = image_path
    try:
        await db.commit()
    except Exception:
        if image_path and os.path.exists(image_path):
            try: os.remove(image_path)
            except: pass
        raise
    if image_path:

        final_path = os.path.join(settings.UPLOAD_DIR, str(job.id) + "_" + uuid.uuid4().hex + ext)
        try:
            os.rename(image_path, final_path)
        except OSError:
            final_path = image_path
        if final_path != job.image_path:
            job.image_path = final_path
            await db.commit()

    try:
        grade_task.delay(job.id)
    except Exception as e:
        try:
            from .tasks import _mark_failed
            await _mark_failed(job.id, f"dispatch_failed: {str(e)[:200]}")
        except Exception:
            await db.rollback()
        raise HTTPException(503, "任务队列不可用，积分已退回，请稍后重试")
    return {"job_id": job.id, "status": "pending"}

@router.get("/{job_id}")
async def status(job_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    job = await db.get(GradingJob, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "任务不存在")
    try:
        result = safe_json_loads(job.grading_result) if job.grading_result else {}
    except (json.JSONDecodeError, TypeError):  # Bug: 防御性 - DB 数据损坏时返回空 dict
        result = {}
    dims = result.get("dimensions", {}) if result else {}
    # 计算进度
    dims_done = 0
    sub_done = 0
    dim_total = 4
    sub_total = 16
    if dims:
        for k, v in dims.items():
            if v.get("score") is not None:
                dims_done += 1
            if v.get("sub_scores"):
                sub_done += len([s for s in v["sub_scores"] if s.get("score") is not None])
    progress = {"stage": job.status, "precheck_done": job.precheck is not None,
                "dims_done": dims_done, "dims_total": dim_total,
                "sub_done": sub_done, "sub_total": sub_total, "dimensions": dims}
    if job.precheck:
        progress["precheck"] = job.precheck
    return {
        "job_id": job.id,
        "status": job.status,
        "task_type": job.task_type,
        "question": job.question or "",
        "essay": job.essay or "",
        "title": job.title or "",  # Bug Fix: 前端 renderReport 需要原文渲染可折叠卡
        "has_image": bool(job.image_path),
        "precheck": job.precheck,
        "result": result,
        "predicted_band": result.get("predicted_band") if result else None,
        "has_image_result": result.get("has_image") if result else None,
        "vlm_used": result.get("vlm_used") if result else None,
        "image_description": result.get("image_description") if result else None,
        "models_used": result.get("models_used") if result else None,
        "progress": progress,
        "error": job.error,
        "created_at": job.created_at.isoformat() + "Z" if job.created_at else None,
        "finished_at": job.finished_at.isoformat() + "Z" if job.finished_at else None
    }

@router.delete("/{job_id}")
async def delete_job(job_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    job = await db.get(GradingJob, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "任务不存在")
    # 删除图片文件
    if job.image_path and os.path.exists(job.image_path):
        try: os.remove(job.image_path)
        except: pass
    # 修复: RefundLog.job_id 有 FK 无级联, 直接删 job 会 IntegrityError 500
    from sqlalchemy import delete as _sa_delete
    from ..models import RefundLog as _RefundLog
    await db.execute(_sa_delete(_RefundLog).where(_RefundLog.job_id == job_id))
    await db.delete(job)
    await db.commit()
    return {"ok": True}

@router.get("/")
async def history(page: int = 1, page_size: int = 10, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    offset = (page - 1) * page_size
    q = select(GradingJob).where(GradingJob.user_id == user.id).order_by(GradingJob.id.desc()).offset(offset).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    total_q = select(func.count()).select_from(GradingJob).where(GradingJob.user_id == user.id)
    total = (await db.execute(total_q)).scalar()
    return {
        "items": [{"id": j.id, "task_type": j.task_type, "status": j.status,
                   "predicted_band": (safe_json_loads(j.grading_result) if j.grading_result else {}).get("predicted_band") if j.grading_result else None,
                   "title": _clean_title(j.title), "question": j.question, "essay": (j.essay or "")[:200],
                   "created_at": j.created_at.isoformat() + "Z" if j.created_at else None} for j in rows],
        "total": total, "page": page, "page_size": page_size
    }

@router.post("/{job_id}/sample-essay")
async def generate_sample_essay(job_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """生成范文。限流两层: 同一 job SAMPLE_ESSAY_COOLDOWN 秒防抖; 每用户 SAMPLE_ESSAY_USER_QUOTA 次 / SAMPLE_ESSAY_USER_WINDOW 秒 兜底."""
    _cooldown = int(getattr(settings, "SAMPLE_ESSAY_COOLDOWN", 60))
    _user_quota = int(getattr(settings, "SAMPLE_ESSAY_USER_QUOTA", 10))
    _user_window = int(getattr(settings, "SAMPLE_ESSAY_USER_WINDOW", 60))
    try:
        import redis.asyncio as _r_async
        _r = _r_async.from_url(settings.REDIS_URL)
        # 1) per-job 防抖: 同一 job 在 cooldown 内不重生成
        _kj = f"sample_essay_job:{user.id}:{job_id}"
        if await _r.get(_kj):
            raise HTTPException(429, f"该任务范文冷却中: {_cooldown}s 内只能生成一次")
        # 2) per-user 兜底: 窗口内总次数限制 (防刷量, 不同 job 间共享)
        _ku = f"sample_essay_user:{user.id}"
        _cnt = await _r.incr(_ku)
        if _cnt == 1:
            await _r.expire(_ku, _user_window)
        if _cnt > _user_quota:
            raise HTTPException(429, f"范文生成限流: {_user_window}s 内最多 {_user_quota} 次")
        await _r.set(_kj, "1", ex=_cooldown)
    except HTTPException:
        raise
    except Exception:
        import logging
        logging.getLogger(__name__).warning("sample_essay rate-limit check failed, allow through")
    job = await db.get(GradingJob, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "任务不存在")
    try:
        result = safe_json_loads(job.grading_result) if job.grading_result else {}
    except (json.JSONDecodeError, TypeError):
        result = {}
    if not result or job.status != "done":
        raise HTTPException(400, "任务未完成批改，无法生成范文")
    dims = result.get("dimensions", {})
    sent_suggs = result.get("sentence_suggestions", [])
    img_desc = result.get("image_description")
    # Bug Fix: 先算 target_band, 9 分直接跳过 (避免无谓 LLM 调用)
    _predicted = result.get("predicted_band")
    if _predicted is not None and _predicted >= 9:
        return {
            "job_id": job.id, "essay": "", "improvements": [],
            "model_used": None, "target_band": None,
            "skipped": True, "reason": "已是 Band 9 最高分, 无需范文参考"
        }
    if _predicted is not None and _predicted < 6:
        _target = 6.0
    elif _predicted is not None:
        _target = min(9.0, round((_predicted + 0.5) * 2) / 2)
    else:
        _vs = [d.get("score") for d in dims.values() if isinstance(d.get("score"), (int, float))]
        _target = min(9.0, max(5.0, round((sum(_vs) / len(_vs) + 0.5) * 2) / 2)) if _vs else 7.5
    prompt = prompts.sample_essay_prompt(
        job.task_type, job.question, job.essay or "",
        dims, sent_suggs, img_desc
    )
    try:
        text_models = await llm.get_models(db, vision=False)
        if not text_models:
            raise HTTPException(400, "无可用文本模型")
        result_text, model_name = await llm.call_with_fallback(text_models, prompt)
        # result_text 可能是 dict 或 str
        if isinstance(result_text, dict):
            parsed = result_text
        elif isinstance(result_text, str):
            parsed = llm.extract_json(result_text)
            if not parsed:
                parsed = {"essay": result_text, "improvements": []}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"生成范文失败: {str(e)}")
    return {
        "job_id": job.id,
        "essay": parsed.get("essay", ""),
        "improvements": parsed.get("improvements", []),
        "model_used": model_name,
        "target_band": _target
    }

@router.get("/{job_id}/radar-data")
async def get_job_radar_data(job_id: int, request: Request, token: str = None, db: AsyncSession = Depends(get_db)):
    """雷达 JSON 数据 - 前端 ECharts 渲染用 (避开 matplotlib 中文字体问题)"""
    user = None
    if token:
        try:
            uid = verify_download_token(token, job_id)
            if uid is None:
                raise HTTPException(401, "Invalid token")
            async with SessionLocal() as s2:
                user = (await s2.execute(select(User).where(User.id == uid))).scalar_one_or_none()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(401, "Invalid token")
    else:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                user = await get_current_user(auth.replace("Bearer ", ""), db)
            except Exception:
                raise HTTPException(401, "Invalid token")
        else:
            raise HTTPException(401, "Missing auth")
    if not user:
        raise HTTPException(401, "Invalid user")
    job = await db.get(GradingJob, job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "无权访问")
    if job.status != "done":
        raise HTTPException(400, "报告尚未生成")
    result = safe_json_loads(job.grading_result, default={}) if job.grading_result else {}
    dims = result.get("dimensions", {}) or {}
    dim_codes = list(dims.keys())
    dim_names_map = {"TR": "任务回应情况", "TA": "任务完成情况", "CC": "连贯性与衔接", "LR": "词汇丰富度", "GRA": "语法多样性及准确性"}
    task_names = {"task1": "Task 1 小作文", "task2": "Task 2 大作文"}
    indicators = []
    values = []
    for c in dim_codes:
        s = dims.get(c, {}).get("score")
        if s is None: s = 0
        indicators.append({"name": dim_names_map.get(c, c) + " (" + c + ")", "max": 9})
        values.append(float(s))
    return {
        "task_type": job.task_type,
        "task_name": task_names.get(job.task_type, job.task_type),
        "predicted_band": result.get("predicted_band"),
        "indicators": indicators,
        "values": values,
    }

@router.get("/{job_id}/image")
async def get_job_image(job_id: int, request: Request, token: str = None, db: AsyncSession = Depends(get_db)):
    """图片端点 - 支持 Bearer 或 query token"""
    user = None
    if token:
        try:
            uid = verify_download_token(token, job_id)
            if uid is None:
                raise HTTPException(401, "Invalid token")
            async with SessionLocal() as s2:
                user = (await s2.execute(select(User).where(User.id == uid))).scalar_one_or_none()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(401, "Invalid token")
    else:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                user = await get_current_user(auth.replace("Bearer ", ""), db)
            except Exception:
                raise HTTPException(401, "Invalid token")
        else:
            raise HTTPException(401, "Missing auth")
    if not user:
        raise HTTPException(401, "Invalid user")
    job = await db.get(GradingJob, job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "无权访问")
    if not job.image_path or not os.path.exists(job.image_path):
        raise HTTPException(404, "图片不存在")
    return FileResponse(job.image_path, headers={"Cache-Control": "no-cache"})
@router.post("/{job_id}/cancel")
async def cancel_job(job_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """取消任务 + 退还积分 (幂等).
    Celery 任务正在跑时不能直接 kill, 但 grader.run_job 开头/结尾检查
    status=cancelled 提前退出.
    退款: 用 RefundLog 防重复. 不论 status 是 pending/running/flagged/cancelled,
    只要还没有 RefundLog 就退 1 分.
    'done' 状态已完成不退款 (用户得到评分).
    'failed' 状态 _mark_failed 已经退过, 这里也跳过."""
    from sqlalchemy import select as _sel
    from ..models import User as _U, RefundLog as _RL
    from datetime import datetime as _dt, timezone as _tz
    job = await db.get(GradingJob, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "任务不存在")
    if job.status == "done":
        return {"ok": True, "already_finished": True, "refunded": 0}
    # 查是否已退过 (避免 _mark_failed 已退 + 用户再 cancel 重复退)
    existing = (await db.execute(
        _sel(_RL).where(_RL.job_id == job_id)
    )).scalar_one_or_none()
    already_refunded = bool(existing)
    refunded_this_call = 0
    if not existing and job.cost_credits and job.cost_credits > 0:
        cap = min(int(job.cost_credits), int(settings.GRADING_COST))
        u = (await db.execute(
            _sel(_U).where(_U.id == job.user_id).with_for_update()
        )).scalar_one_or_none()
        if u:
            u.credits += cap
            db.add(_RL(user_id=u.id, amount=cap, job_id=job_id, reason="user_cancel_refund"))
            refunded_this_call = cap
    if job.status != "cancelled":
        job.status = "cancelled"
        job.finished_at = _dt.now(_tz.utc)
    await db.commit()
    return {
        "ok": True,
        "refunded": refunded_this_call,
        "already_refunded": already_refunded,
        "amount": (existing.amount if existing else refunded_this_call),
    }


@router.patch("/{job_id}/title")
async def rename_job(job_id: int, body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """用户重命名评分结果标题。仅改 job.title, 不影响内容。"""
    new_title = (body or {}).get("title", "")
    if not isinstance(new_title, str):
        raise HTTPException(400, "title 必须是字符串")
    new_title = new_title.strip()[:120]
    if not new_title:
        raise HTTPException(400, "title 不能为空")
    job = await db.get(GradingJob, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "任务不存在")
    job.title = new_title
    await db.commit()
    return {"ok": True, "title": new_title}


@router.post("/{job_id}/retry")
async def retry_job(job_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """失败/取消的任务继续评分: 重扣费(失败时已退) -> 状态重置 pending -> 重新入队.
    grading_result 保留, grader 会跳过已出分的子维度 (断点续评)."""
    from sqlalchemy import select as _sel
    from ..models import RefundLog as _RL
    from ..credits import charge as _charge
    job = await db.get(GradingJob, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "任务不存在")
    if job.status not in ("failed", "cancelled"):
        raise HTTPException(400, "只能继续失败或已取消的任务")
    # 失败时已退款 -> 重新扣费; 若未退过款(异常路径)则跳过扣费防双收
    refunded = (await db.execute(_sel(_RL).where(_RL.job_id == job_id))).scalar_one_or_none()
    if refunded:
        await _charge(db, user.id)
        job.cost_credits = settings.GRADING_COST
    job.status = "pending"
    job.error = None
    job.finished_at = None
    await db.commit()
    try:
        grade_task.delay(job.id)
    except Exception:
        # 队列不可达时回滚状态, 不吞用户的钱
        job.status = "failed"
        job.error = "重试入队失败, 请稍后再试"
        await db.commit()
        raise HTTPException(503, "评分队列暂不可用")
    return {"ok": True, "job_id": job_id, "resumed": True}


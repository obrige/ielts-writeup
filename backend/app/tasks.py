import asyncio
from celery.exceptions import MaxRetriesExceededError
from .celery_app import celery
from .config import settings


def _run_async(coro):
    """Safely run an async coroutine, handling event loop lifecycle."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # 关键：跑完关闭 loop，避免 leak
        try:
            loop.close()
        except Exception:
            pass


@celery.task(name="grade", bind=True, max_retries=settings.LLM_MAX_RETRIES)
def grade_task(self, job_id: int):
    from .grader import run_job
    try:
        _run_async(run_job(job_id))
    except Exception as exc:
        # 不传 exc=exc, 这样 celery 在重试耗尽时会抛 MaxRetriesExceededError (传了反而 raise 原始 exc, 永远不会触发)
        try:
            self.retry(countdown=30)
        except MaxRetriesExceededError:

            try:
                _run_async(_mark_failed(job_id, str(exc)))
            except Exception as refund_err:
                import logging
                logging.getLogger(__name__).critical(
                    "REFUND FAILED for job=%s err=%s original=%s", job_id, refund_err, exc, exc_info=True
                )


async def _mark_failed(job_id: int, error: str):
    """Bug #2/#16 fix: 退费加 SELECT FOR UPDATE 行锁, 退款上限 = min(实际扣费, GRADING_COST)。
    防止: cost_credits 历史值被滥用导致 credits 暴涨。"""
    from .database import SessionLocal
    from .models import GradingJob, User, RefundLog
    from .config import settings
    from sqlalchemy import select
    async with SessionLocal() as db:
        try:
            job = (await db.execute(select(GradingJob).where(GradingJob.id == job_id))).scalar_one_or_none()
            if job:
                from datetime import datetime, timezone
                job.status = "failed"
                job.error = error[:2000]
                if job.cost_credits and job.cost_credits > 0:
                    cap_amount = min(int(job.cost_credits), int(settings.GRADING_COST))
                    user = (await db.execute(
                        select(User).where(User.id == job.user_id).with_for_update()
                    )).scalar_one_or_none()
                    if user:
                        user.credits += cap_amount
                        db.add(RefundLog(
                            user_id=user.id, amount=cap_amount,
                            job_id=job_id,
                            reason=f"grading_failed_refund: {error[:80]}"))
                await db.commit()
        except Exception:
            await db.rollback()
            raise

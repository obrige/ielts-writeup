from fastapi import HTTPException
from sqlalchemy import select
from .config import settings
from .models import User


async def charge(db, user_id: int):
    """扣费。必须传 user_id (而不是 user 对象)，因为我们要重新查询加行锁。

    原代码直接修改传入的 user 对象，没有锁 → 并发扣费可透支积分（Bug #5）。
    修复：用 SELECT ... FOR UPDATE 拿行锁，保证扣费的原子性。
    """
    from .models import User
    # 重新查询并加行锁（事务结束自动释放）
    user = (await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.credits < settings.GRADING_COST:
        raise HTTPException(402, "满分币不足")
    user.credits -= settings.GRADING_COST
    # 不在 charge commit，由调用方统一事务

from celery import Celery
from .config import settings

celery = Celery("ielts", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery.conf.update(
    task_acks_late=True,  # 任务完成后才 ack，防止崩溃丢失
    task_reject_on_worker_lost=True,  # worker 崩溃时未完成任务自动重派
    worker_prefetch_multiplier=1,  # 每个 worker 一次只取 1 个任务，防止一个任务占满 worker
    task_track_started=True,  # 跟踪任务开始状态
    broker_connection_retry_on_startup=True,  # 启动时 broker 不在线则重试
    # 评分任务含 16+ 次 LLM 调用, 必须有超时, 防止 worker 永久卡住
    task_time_limit=3600,        # 硬超时 1 小时, 超时直接 kill
    task_soft_time_limit=3300,   # 软超时 55 分钟, 让任务优雅退出
    worker_max_tasks_per_child=200,  # 每 worker 处理 200 任务后重启, 防内存泄漏
    # 结果后端保留时间 (默认 1 天)
    result_expires=86400,
)

# 必须导入 tasks 模块，否则 worker 不认识 @celery.task 注册的任务
from . import tasks  # noqa: E402, F401

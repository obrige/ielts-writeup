from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+asyncmy://ielts:ielts123@mysql:3306/ielts?charset=utf8mb4"
    REDIS_URL: str = "redis://redis:6379/0"
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_MINUTES: int = 1440  # 1 天
    GRADING_COST: int = 1
    MAX_ESSAY_CHARS: int = 20000  # 作文字数上限（防 DoS/DB 溢出）
    MAX_IMAGE_BYTES: int = 10 * 1024 * 1024  # 10MB 图片大小
    UPLOAD_DIR: str = "/app/uploads"
    WORKER_CONCURRENCY: int = 4
    GRADER_CONCURRENCY: int = 4
    MAX_PARALLEL_MODELS: int = 4  # Bug #16: 并发尝试的最大模型数(原 LLM_MAX_RETRIES 被错误复用)  # 并发评分 sub-dim/dim-synthesis 的数量上限（管理后台可调）
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "CHANGE_ME_IN_DOTENV"  # Bug #34: 默认值改为占位符, 强制 .env 必须覆盖
    ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_MODEL_BASE_URL: str = "http://host.docker.internal:8000/v1"
    DEFAULT_MODEL_API_KEY: str = "sk-temporarychat"
    LLM_TIMEOUT: int = 180
    LLM_MAX_TOKENS: int = 8000
    LLM_MAX_RETRIES: int = 3

# 范文生成限流 (per-job 防抖 + per-user 兜底)
    SAMPLE_ESSAY_COOLDOWN: int = 60  # 同一 job 范文生成冷却秒数
    SAMPLE_ESSAY_USER_QUOTA: int = 10  # 单用户窗口内最大范文次数
    SAMPLE_ESSAY_USER_WINDOW: int = 60  # 用户配额窗口秒数
    model_config = {"env_file": ".env"}

settings = Settings()
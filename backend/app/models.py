from sqlalchemy import Column, BigInteger, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey, func
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128))
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), default="user")
    credits = Column(Integer, default=0)
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class ModelConfig(Base):
    __tablename__ = "model_configs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)
    base_url = Column(String(256), nullable=False)
    api_key = Column(String(256), default="")
    model_name = Column(String(128), nullable=False)
    is_vision = Column(Boolean, default=False)
    is_text = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    priority = Column(Integer, default=0)
    fallback_models = Column(JSON, default=list)
    search_off = Column(JSON, default=dict)
    label = Column(String(128))
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())

class GradingJob(Base):
    __tablename__ = "grading_jobs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    task_type = Column(String(8), nullable=False)
    question = Column(Text, nullable=False)
    essay = Column(Text, nullable=False)
    image_path = Column(String(512))
    cost_credits = Column(Integer, default=1)
    status = Column(String(16), default="pending")
    precheck = Column(JSON)
    grading_result = Column(Text, nullable=True)  # 简单 TEXT，grader.py 端 json.dumps 序列化
    error = Column(Text)
    title = Column(String(128))
    created_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime)

class RechargeLog(Base):
    __tablename__ = "recharge_logs"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    amount = Column(Integer)
    admin_id = Column(BigInteger, nullable=True)
    reason = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())


class RefundLog(Base):
    """评分失败退费流水（与充值分开，便于审计）"""
    __tablename__ = "refund_logs"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    amount = Column(Integer)
    job_id = Column(BigInteger, ForeignKey("grading_jobs.id"), nullable=True)
    reason = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

class InviteCode(Base):
    __tablename__ = "invite_codes"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    created_by = Column(BigInteger, ForeignKey("users.id"))
    used_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class RedeemCode(Base):
    __tablename__ = "redeem_codes"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    credits = Column(Integer, nullable=False, default=1)
    created_by = Column(BigInteger, ForeignKey("users.id"))
    used_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

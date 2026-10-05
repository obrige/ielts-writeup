import bcrypt, secrets
from jose import jwt
from datetime import datetime, timedelta, timezone
from .config import settings


def hash_pw(p: str) -> str:
    # Bug #32
    encoded = p.encode("utf-8")[:72]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode()


def verify_pw(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode("utf-8")[:72], h.encode())


def create_token(u):
    return jwt.encode(
        {"sub": str(u.id), "role": u.role, "username": u.username,
         "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)},
        settings.JWT_SECRET, algorithm="HS256")


def decode_token(t):
    return jwt.decode(t, settings.JWT_SECRET, algorithms=["HS256"])


def generate_code(length: int = 16) -> str:
    """生成随机码 (Bug #5: 满熵)"""
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

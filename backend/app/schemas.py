from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    role: str
    username: str = ""

class LoginReq(BaseModel):
    username: str
    password: str

class RegisterReq(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: EmailStr | None = None
    invite_code: str = Field(..., description="邀请码")

class ChangePasswordReq(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)

class ResetPasswordReq(BaseModel):
    user_id: int
    new_password: str = Field(min_length=6, max_length=128)

class UpdateEmailReq(BaseModel):
    email: EmailStr | None = None

class PullModelsReq(BaseModel):
    base_url: str
    api_key: str = ""

class ModelCreateReq(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str = Field(min_length=1, max_length=64)
    base_url: str = Field(min_length=1, max_length=256)
    api_key: str = Field(default="", max_length=256)
    model_name: str = Field(min_length=1, max_length=128)
    is_vision: bool = False
    is_text: bool = True
    is_default: bool = False
    priority: int = 0
    fallback_models: list[str] = []
    label: Optional[str] = None
    tags: Optional[list] = None
    enabled: bool = True

class ModelUpdateReq(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    is_vision: Optional[bool] = None
    is_text: Optional[bool] = None
    is_default: Optional[bool] = None
    priority: Optional[int] = None
    fallback_models: Optional[list] = None
    label: Optional[str] = None
    tags: Optional[list] = None
    enabled: Optional[bool] = None

class RechargeReq(BaseModel):
    user_id: int
    amount: int = Field(gt=0, le=10000, description="充值金额必须为正数且不超过10000")

class GenerateInviteReq(BaseModel):
    count: int = Field(default=1, ge=1, le=50)

class GenerateRedeemReq(BaseModel):
    count: int = Field(default=1, ge=1, le=50)
    credits: int = Field(default=1, ge=1, le=100)

class RedeemReq(BaseModel):
    code: str


class SettingsUpdate(BaseModel):
    LLM_TIMEOUT: int = Field(default=180, ge=30, le=600)
    LLM_MAX_TOKENS: int = Field(default=8000, ge=1000, le=32000)
    LLM_MAX_RETRIES: int = Field(default=3, ge=1, le=10)
    GRADER_CONCURRENCY: int = Field(default=4, ge=1, le=32)

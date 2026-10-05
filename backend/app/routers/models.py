def _validate_base_url(url):
    """防 SSRF: 拒绝私有/回环/链路本地/多播/保留 IP (含 IPv6)。
    开发态可白名单 host.docker.internal 等 (默认开启), 生产可设 SSRF_STRICT=1 锁死。
    """
    import ipaddress, socket, os
    from urllib.parse import urlparse
    try:
        p = urlparse(url)
    except Exception:
        raise HTTPException(400, "无效的 URL")
    if p.scheme not in ("http", "https"):
        raise HTTPException(400, "只支持 http/https 协议")
    if not p.hostname:
        raise HTTPException(400, "URL 缺少 hostname")
    hostname = p.hostname.strip("[]").lower()
    if hostname in ("localhost", "0.0.0.0", "ip6-localhost", "ip6-loopback", "::"):
        raise HTTPException(400, "禁止访问 " + hostname)
    # 开发态白名单: SSRF_STRICT=1 关闭, 否则 host.docker.internal 等始终放行
    if os.environ.get("SSRF_STRICT") != "1":
        builtin_allow = {"host.docker.internal", "gateway.docker.internal"}
        user_allow = {h.strip().lower() for h in os.environ.get("SSRF_ALLOW_HOSTS", "").split(",") if h.strip()}
        if hostname in (builtin_allow | user_allow):
            return url
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(400, "无法解析 " + hostname)
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if (ip.is_private or ip.is_loopback or ip.is_link_local or
            ip.is_multicast or ip.is_reserved or ip.is_unspecified):
            raise HTTPException(400, "禁止访问私有/保留 IP: " + str(ip))
    return url


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..deps import require_admin
from ..models import ModelConfig
from ..schemas import PullModelsReq, ModelCreateReq, ModelUpdateReq
from .. import llm

router = APIRouter(prefix="/admin/models", tags=["models"])

@router.post("/pull")
async def pull(req: PullModelsReq, _=Depends(require_admin)):
    _validate_base_url(req.base_url)
    return {"models": await llm.pull_models(req.base_url, req.api_key)}

@router.post("")
async def create(req: ModelCreateReq, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    _validate_base_url(req.base_url)
    data = req.model_dump()
    if data.get("label") is None:
        data["label"] = data.get("name", "")
    if data.get("tags") is None:
        data["tags"] = []
    m = ModelConfig(**data)
    db.add(m); await db.commit()
    return {"id": m.id}

@router.get("")
async def list_models(_=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(ModelConfig).order_by(ModelConfig.priority.desc(), ModelConfig.id))).scalars().all()
    out = []
    for m in rows:
        ak = (m.api_key or "").strip()
        out.append({
            "id": m.id,
            "name": m.name,
            "label": m.label or m.name,
            "model_name": m.model_name,
            "base_url": m.base_url,
            "has_api_key": bool(ak),
            "api_key_preview": ("*" * max(0, len(ak) - 4) + ak[-4:]) if len(ak) > 4 else ("*" * len(ak)),
            "is_vision": m.is_vision,
            "is_text": m.is_text,
            "enabled": m.enabled,
            "is_default": m.is_default,
            "priority": m.priority,
            "fallback_models": m.fallback_models or [],
            "tags": m.tags or [],
        })
    return out

@router.patch("/{model_id}")
async def update_model(model_id: int, req: ModelUpdateReq, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    m = await db.get(ModelConfig, model_id)
    if not m: raise HTTPException(404, "模型不存在")
    if req.base_url is not None:
        _validate_base_url(req.base_url)
    data = req.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(m, k, v)
    await db.commit()
    return {"ok": True}

@router.delete("/{model_id}")
async def delete(model_id: int, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    m = await db.get(ModelConfig, model_id)
    if m: await db.delete(m); await db.commit()
    return {"ok": True}

@router.post("/{model_id}/toggle")
async def toggle_model(model_id: int, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    m = await db.get(ModelConfig, model_id)
    if not m: raise HTTPException(404, "模型不存在")
    m.enabled = not m.enabled
    await db.commit()
    return {"ok": True, "enabled": m.enabled}

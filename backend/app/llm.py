import asyncio, httpx, json, re
from sqlalchemy import select
from .database import SessionLocal
from .models import ModelConfig
from .config import settings

REFUSAL = ["知识库中没有找到", "没有找到相关信息", "我无法回答", "无法回答这个问题", "no relevant info", "no relevant information", "cannot answer", "i cannot", "i am not able", "unable to", "as an ai", "i do not have"]

BT = chr(96)

async def get_models(db, vision=False):
    """获取可用模型。vision=False 过滤 is_text，vision=True 过滤 is_vision。"""
    q = select(ModelConfig).where(ModelConfig.enabled == True)
    if vision:
        q = q.where(ModelConfig.is_vision == True)
    else:
        q = q.where(ModelConfig.is_text == True)  # Bug Fix: 文本任务严格过滤，不调用视觉模型
    q = q.order_by(ModelConfig.priority.desc(), ModelConfig.id)
    return list((await db.execute(q)).scalars())


async def chat_json(cfg, prompt, image_b64=None, mime="image/png"):
    messages = [{"role": "user", "content": _content(prompt, image_b64, mime)}]
    # 每次 new client，无锁并发；httpx 内部连接池自动管理
    async with httpx.AsyncClient(timeout=float(settings.LLM_TIMEOUT), limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)) as c:
        r = await c.post(cfg.base_url.rstrip("/") + "/chat/completions",
            json={"model": cfg.model_name, "messages": messages, "temperature": 0.2,
                  "max_tokens": int(settings.LLM_MAX_TOKENS), "response_format": {"type": "json_object"}},
            headers={"Authorization": "Bearer " + cfg.api_key})
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        if any(k in content for k in REFUSAL):
            raise RuntimeError("refused: " + content[:80])
        return extract_json(content)


async def chat_text(cfg, prompt, image_b64=None, mime="image/png"):
    """Call LLM and return raw text (not JSON)."""
    messages = [{"role": "user", "content": _content(prompt, image_b64, mime)}]
    async with httpx.AsyncClient(timeout=float(settings.LLM_TIMEOUT), limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)) as c:
        r = await c.post(cfg.base_url.rstrip("/") + "/chat/completions",
            json={"model": cfg.model_name, "messages": messages, "temperature": 0.2,
                  "max_tokens": int(settings.LLM_MAX_TOKENS)},
            headers={"Authorization": "Bearer " + cfg.api_key})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# 全局并发闸: 限制同时在途 LLM HTTP 请求总数, 防止打爆本地上游 (ReadTimeout 雪崩根因)
# Bug fix: Semaphore 不能在模块级创建后跨 event loop 复用 (Celery 每任务新建 loop,
# 报 "bound to a different event loop" 导致全部子维度调用阵亡). 改为按 loop 懒创建.
import os as _os
_LLM_SEMS = {}
def _llm_sem():
    loop = asyncio.get_running_loop()
    sem = _LLM_SEMS.get(loop)
    if sem is None:
        sem = asyncio.Semaphore(int(_os.environ.get("LLM_MAX_INFLIGHT", "4")))
        _LLM_SEMS[loop] = sem
    return sem


async def _try_with_fallback(cfgs, prompt, chat_fn, image_b64=None, mime="image/png"):
    """并发尝试所有模型，取第一个成功的；失败都失败时 raise 最后一个错。"""
    if not cfgs:
        raise RuntimeError("no models available")
    async def _one(cfg):
        async with _llm_sem():
            return await chat_fn(cfg, prompt, image_b64=image_b64, mime=mime), cfg.name

    tasks = [asyncio.create_task(_one(cfg)) for cfg in cfgs[:int(getattr(settings, "MAX_PARALLEL_MODELS", 4))]]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except Exception:
        for t in tasks: t.cancel()
        raise
    last_exc = None
    for t in done:
        try:
            result, name = t.result()
            for p in pending:
                if not p.done():
                    p.cancel()
            return result, name
        except Exception as e:
            last_exc = e
    for p in pending:
        if not p.done():
            p.cancel()
    if last_exc:
        raise last_exc
    raise RuntimeError("all models failed")


async def call_with_fallback(cfgs, prompt, image_b64=None, mime="image/png"):
    """Call LLM with JSON output and fallback. Returns (result, model_name)."""
    return await _try_with_fallback(cfgs, prompt, chat_json, image_b64, mime)


async def call_text_with_fallback(cfgs, prompt, image_b64=None, mime="image/png"):
    """Call LLM with text output and fallback. Returns (text, model_name)."""
    return await _try_with_fallback(cfgs, prompt, chat_text, image_b64, mime)


def _content(prompt, image_b64, mime):
    if not image_b64:
        return prompt
    return [{"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + image_b64}}]


def _escape_inner_quotes(s):
    """容错处理: 把 JSON 字符串里未转义的 " 改成 \" .
    启发式: 进 string 后, 看到 " 时, 看下一个非空白字符是不是 , : } ], 是则当字符串真正结束 (不转义), 否则当 stray.
    这能恢复 LLM 常见的 "abc"def 这种内嵌引号."""
    out = []
    in_string = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if in_string and c == "\\" and i + 1 < n:
            # 保留已有转义序列
            out.append(c); out.append(s[i+1]); i += 2; continue
        if c == '"':
            if not in_string:
                in_string = True
                out.append(c); i += 1; continue
            # 已进 string: 判断是不是真边界
            j = i + 1
            while j < n and s[j] in " \t\n":
                j += 1
            if j >= n or s[j] in ",:}]":
                # 真正结尾
                in_string = False
                out.append(c)
            else:
                # stray, 加 \
                out.append("\\"); out.append(c)
            i += 1; continue
        out.append(c); i += 1
    return "".join(out)


def extract_json(s):
    """多层 fallback 提取 LLM 输出里的 JSON.
    1) 严格 parse: 标准 JSON
    2) 容错 1: 把内嵌的 stray " 转义后再 parse (修复 LLM 把英文引号直接写入 string value 的常见错误)
    3) 容错 2: 用 raw_decode, 容忍 JSON 后面跟着解释文字
    都失败则显式抛 ValueError, 让 Celery 重试 / 上层处理"""
    s = re.sub(r"^" + BT*3 + r"[a-zA-Z]*\s*", "", s.strip())
    s = re.sub(r"\s*" + BT*3 + r"$", "", s)
    start = s.find("{")
    if start < 0:
        raise ValueError("no JSON object found: " + s[:200])
    candidate = s[start:]
    # Strategy 1: 严格 parse
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # Strategy 2: 转义 inner stray quotes 后再 parse
    try:
        return json.loads(_escape_inner_quotes(candidate))
    except json.JSONDecodeError:
        pass
    # Strategy 3: raw_decode, 容忍尾部说明文字
    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(candidate)
        return obj
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed at offset {e.pos}: {s[:100]}...")


async def pull_models(base_url, api_key):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(base_url.rstrip("/") + "/models", headers={"Authorization": "Bearer " + api_key})
        r.raise_for_status()
        return r.json()["data"]

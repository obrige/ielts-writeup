"""安全相关: SSRF 拦截 / extract_json 严格 / JWT secret 强度"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException
from app.routers.models import _validate_base_url
from app.llm import extract_json


def _expect_fail(url):
    try:
        _validate_base_url(url)
    except HTTPException as e:
        assert e.status_code == 400, "expected 400 for %s, got %d" % (url, e.status_code)
        return
    raise AssertionError("expected HTTPException for " + url)


def test_ssrf_blocks_loopback():
    _expect_fail("http://127.0.0.1/api")
    _expect_fail("http://localhost/api")


def test_ssrf_blocks_private():
    """private range should be rejected"""
    os.environ["SSRF_STRICT"] = "1"
    try:
        _expect_fail("http://10.0.0.5/api")
        _expect_fail("http://192.168.1.1/api")
        _expect_fail("http://172.16.0.1/api")
    finally:
        os.environ.pop("SSRF_STRICT", None)


def test_extract_json_strict_parses_valid():
    j = extract_json('{"a": 1, "b": [1,2,3]}')
    assert j == {"a": 1, "b": [1, 2, 3]}


def test_extract_json_strips_codefence():
    s = chr(96)*3 + chr(10) + '{"x": 1}' + chr(10) + chr(96)*3
    j = extract_json(s)
    assert j == {"x": 1}


def test_extract_json_rejects_truncated():
    """Bug fix: no auto-fix, truncated JSON should raise"""
    with pytest.raises(ValueError):
        extract_json('{"a": 1, "b": [1, 2')


def test_extract_json_rejects_garbage():
    with pytest.raises(ValueError):
        extract_json("not json at all")


def test_extract_json_rejects_object_in_codefence():
    with pytest.raises(ValueError):
        extract_json("hello {not json} world")


def test_jwt_secret_too_short_rejected():
    import importlib, asyncio
    os.environ["JWT_SECRET"] = "tooShort"
    try:
        import app.config; importlib.reload(app.config)
        import app.main; importlib.reload(app.main)
        from app.main import _check_security
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            asyncio.run(_check_security())
    finally:
        os.environ["JWT_SECRET"] = "x" * 32
        import app.config; importlib.reload(app.config)


def test_jwt_secret_default_rejected():
    import importlib, asyncio
    os.environ["JWT_SECRET"] = "change-me"
    try:
        import app.config; importlib.reload(app.config)
        import app.main; importlib.reload(app.main)
        from app.main import _check_security
        with pytest.raises(RuntimeError, match="[JS]?WT_SECRET"):
            asyncio.run(_check_security())
    finally:
        os.environ["JWT_SECRET"] = "x" * 32
        import app.config; importlib.reload(app.config)

def test_extract_json_unescaped_quote_recovers():
    """LLM 偶发把英文引号直接写入 string value, extract_json 应自动恢复 (不抛错)"""
    bad = '{"area":"段落结构","score":4.0,"explanation":"文章通篇只有一个段落，如原文"With video..."}'
    j = extract_json(bad)
    assert j["area"] == "段落结构"
    assert j["score"] == 4.0
    assert "With video" in j["explanation"]


def test_extract_json_trailing_content_recovers():
    """LLM 输出 JSON 后跟解释文字, raw_decode 应能剥掉"""
    bad = '{"a":1, "b":2}\n\n以上是评分结果，祝你进步！'
    j = extract_json(bad)
    assert j["a"] == 1
    assert j["b"] == 2


def test_extract_json_pure_prose_raises():
    """LLM 完全答非所问时, 必须显式抛错 (不能编造)"""
    with pytest.raises(ValueError):
        extract_json("您好我是灵犀，我理解您希望进行雅思写作评估，但我是 AI 助手不能给官方评分...")


def test_extract_json_real_json_still_parses():
    """确认标准 JSON 仍然能 parse (没被新逻辑破坏)"""
    # 标准 JSON 含正常转义
    j = extract_json('{"a": 1, "b": [1, 2, 3], "c": "中英文 mixed \\\"quotes\\\" ok"}')
    assert j["a"] == 1
    assert j["b"] == [1, 2, 3]
    assert "mixed" in j["c"]


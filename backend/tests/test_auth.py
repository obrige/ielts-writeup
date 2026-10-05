"""Auth 路径测试: 登录、限流、邀请码注册、弱密码拒绝"""
import time
import requests
import pytest
from tests._helpers import unique_name, unique_code


def test_admin_login_ok(api, base_url):
    r = api.post(base_url + "/auth/login", json={"username": "admin", "password": "Admin_84z881q5u6d"}, timeout=10)
    assert r.status_code == 200, "admin login should succeed"
    j = r.json()
    assert "access_token" in j
    assert j["role"] == "admin"


def test_wrong_password_returns_401(api, base_url):
    r = api.post(base_url + "/auth/login", json={"username": "admin", "password": "wrong!"}, timeout=10)
    assert r.status_code == 401


@pytest.mark.parametrize("pwd_len", [3, 5])
def test_too_short_password_rejected_on_register(api, base_url, auth_headers, pwd_len):
    """注册时密码 < 6 位应被拒绝"""
    code = unique_code()
    # 先生成一个邀请码让 admin
    r = api.post(base_url + "/admin/invite-codes", headers=auth_headers, json={"count": 1}, timeout=10)
    assert r.status_code == 200
    invite = r.json()["codes"][0]
    # 用短密码注册
    name = unique_name("shortpw")
    r = api.post(base_url + "/auth/register", json={
        "username": name, "password": "a" * pwd_len,
        "email": None, "invite_code": invite,
    }, timeout=10)
    assert r.status_code in (400, 422)


def test_invite_code_uniqueness(api, base_url, auth_headers):
    """同一邀请码第二次注册应被拒绝 (合并错误消息)"""
    r = api.post(base_url + "/admin/invite-codes", headers=auth_headers, json={"count": 1}, timeout=10)
    code = r.json()["codes"][0]
    r = api.post(base_url + "/auth/register", json={
        "username": unique_name("first"), "password": "password123",
        "email": None, "invite_code": code,
    }, timeout=10)
    assert r.status_code == 200
    # 第二次用同一邀请码
    r = api.post(base_url + "/auth/register", json={
        "username": unique_name("second"), "password": "password123",
        "email": None, "invite_code": code,
    }, timeout=10)
    assert r.status_code == 400
    # Bug #35: 合并错误消息, 不暴露码是否用过
    assert "邀请码" in r.json().get("detail", "")


def test_rate_limit_triggers_429(api, base_url):
    """连续 10+ 次登录失败, 第 10 次触发 429"""
    name = unique_name("ratelimit")
    statuses = []
    for _ in range(11):
        r = api.post(base_url + "/auth/login", json={"username": name, "password": "wrong"}, timeout=10)
        statuses.append(r.status_code)
        if r.status_code == 429:
            break
    # 限流必须在至少 10 次内触发
    assert 429 in statuses, "429 should trigger within 11 attempts: %s" % statuses
    # 触发 429 时已经累计若干 401
    assert any(s == 401 for s in statuses), "expected some 401s before 429"

"""管理 API 测试: 模型、用户、邀请码、兑换码、设置"""
import pytest
from tests._helpers import unique_name, unique_code


def test_models_list_empty_or_some(api, base_url, auth_headers):
    r = api.get(base_url + "/admin/models", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_invite_code_generate_and_list(api, base_url, auth_headers):
    r = api.post(base_url + "/admin/invite-codes", headers=auth_headers, json={"count": 3}, timeout=10)
    assert r.status_code == 200
    codes = r.json()["codes"]
    assert len(codes) == 3
    # 每个码 16 字符
    for c in codes:
        assert len(c) >= 12


def test_redeem_code_generate(api, base_url, auth_headers):
    r = api.post(base_url + "/admin/redeem-codes", headers=auth_headers,
                 json={"count": 2, "credits": 5}, timeout=10)
    assert r.status_code == 200
    arr = r.json()["codes"]
    assert len(arr) == 2
    assert all(c["credits"] == 5 for c in arr)


def test_users_list(api, base_url, auth_headers):
    r = api.get(base_url + "/admin/users", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    users = r.json()
    assert isinstance(users, list)
    assert any(u["username"] == "admin" for u in users)


def test_grading_listing(api, base_url, auth_headers):
    r = api.get(base_url + "/grading/", headers=auth_headers, params={"page_size": 5}, timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert "items" in j
    assert "total" in j


def test_unauthorized_access_blocked(api, base_url):
    """没 token 应被 401"""
    r = api.get(base_url + "/admin/users", timeout=10)
    assert r.status_code == 401
    r = api.get(base_url + "/admin/models", timeout=10)
    assert r.status_code == 401
    r = api.post(base_url + "/auth/login", json={"username": "admin", "password": "x"}, timeout=10)
    assert r.status_code == 401

"""共享 fixtures: HTTP 客户端 + admin token + 提工具"""
import os, time, secrets, pytest, requests

# Base URL resolution order:
# 1. IELTS_API_DIRECT env override
# 2. Inside container: localhost (api 在同一容器内或通过 docker network 的 "backend:8000")
# 3. Outside container (host): host.docker.internal (Docker Desktop/Windows 用法)
DIRECT = os.environ.get("IELTS_API_DIRECT") or (
    "http://localhost:8000/api"
    if os.path.exists("/.dockerenv")
    else "http://host.docker.internal:8000/api"
)
ADMIN_USER = os.environ.get("IELTS_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("IELTS_ADMIN_PASS", "Admin_84z881q5u6d")


from tests._helpers import unique_name

def _wait_api(timeout=60):
    """轮询直到后端起来"""
    health_url = DIRECT.replace("/api", "") + "/openapi.json"
    for i in range(timeout):
        try:
            r = requests.get(health_url, timeout=3)
            if r.status_code == 200:
                return DIRECT
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("API not ready in %ds at %s" % (timeout, DIRECT))


@pytest.fixture(scope="session")
def base_url():
    _wait_api()
    return DIRECT


@pytest.fixture(scope="session")
def api(base_url):
    return requests.Session()


@pytest.fixture(scope="session")
def admin_token(api, base_url):
    r = api.post(base_url + "/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=10)
    if r.status_code != 200:
        pytest.skip("admin login failed: %s %s" % (r.status_code, r.text[:200]))
    return r.json().get("access_token")


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}



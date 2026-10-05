"""评分相关"""
import time
import pytest
from tests._helpers import unique_name

SMALL_ESSAY = 'Technology has changed our lives. ' * 60

def make_essay(words=300):
    para = 'Modern technology plays an important role in daily life, and people discuss whether it makes us more social. ' * 8
    target_words = max(words, 50)
    return para[:target_words * 6]


def test_submit_and_status(api, base_url, auth_headers):
    fd = {'task_type': 'task2', 'question': 'Test question', 'essay': make_essay(280)}
    r = api.post(base_url + '/grading/submit', headers=auth_headers, data=fd, timeout=30)
    assert r.status_code in (200, 402)
    if r.status_code != 200: return
    job_id = r.json()['job_id']
    r = api.get(base_url + f'/grading/{job_id}', headers=auth_headers, timeout=10)
    assert r.status_code == 200, r.text[:200]


def test_cancel_refunds_credits(api, base_url, auth_headers):
    r = api.get(base_url + '/users/me', headers=auth_headers, timeout=10)
    if r.status_code != 200: pytest.skip('cant get user info')
    before = r.json()['credits']
    fd = {'task_type': 'task2', 'question': 'q', 'essay': make_essay(260)}
    r = api.post(base_url + '/grading/submit', headers=auth_headers, data=fd, timeout=30)
    if r.status_code == 402: pytest.skip('not enough credits')
    if r.status_code != 200: pytest.skip('submit failed')
    job_id = r.json()['job_id']
    time.sleep(0.5)
    r = api.post(base_url + f'/grading/{job_id}/cancel', headers=auth_headers, timeout=10)
    assert r.status_code == 200, r.text[:200]
    j = r.json()
    assert j.get('ok') is True
    assert 'refunded' in j
    r = api.get(base_url + '/users/me', headers=auth_headers, timeout=10)
    after = r.json()['credits']
    assert after == before, f'credits before/after mismatch: {before} -> {after}'


def test_rename_title(api, base_url, auth_headers):
    fd = {'task_type': 'task2', 'question': 'q', 'essay': make_essay(260)}
    r = api.post(base_url + '/grading/submit', headers=auth_headers, data=fd, timeout=30)
    if r.status_code == 402: pytest.skip('not enough credits')
    if r.status_code != 200: pytest.skip('submit failed')
    job_id = r.json()['job_id']
    new_title = 'My Renamed Test Title - ' + str(int(time.time()))
    r = api.request('PATCH', base_url + f'/grading/{job_id}/title', headers=auth_headers, json={'title': new_title}, timeout=10)
    assert r.status_code == 200
    assert r.json()['title'] == new_title
    r = api.get(base_url + f'/grading/{job_id}', headers=auth_headers, timeout=10)
    assert r.json().get('title') == new_title


def test_submit_empty_essay_rejected(api, base_url, auth_headers):
    fd = {'task_type': 'task2', 'question': 'q', 'essay': ''}
    r = api.post(base_url + '/grading/submit', headers=auth_headers, data=fd, timeout=10)
    assert r.status_code in (400, 422)


def test_submit_too_long_essay_rejected(api, base_url, auth_headers):
    huge = 'x' * 25000
    fd = {'task_type': 'task2', 'question': 'q', 'essay': huge}
    r = api.post(base_url + '/grading/submit', headers=auth_headers, data=fd, timeout=30)
    assert r.status_code == 400


# Regression: grader.L292 must use db.refresh(job, attribute_names=['status']) to avoid clobbering grading_result
def test_grader_finalize_writes_predicted_band():
    import inspect, re
    from app import grader
    src = inspect.getsource(grader.run_job)
    # L292 must use attribute_names
    assert 'attribute_names' in src, 'L292 must refresh specific fields, not the whole row'
    # 必须带 attribute_names=['status'] 参数 (用正则匹配)
    assert re.search(r'db\.refresh\s*\(\s*job\s*,\s*attribute_names\s*=', src), \
           'L292 must specify attribute_names to avoid SELECT-ing grading_result'
    # 反向: 不可有裸 db.refresh(job)
    bad = re.findall(r'db\.refresh\s*\(\s*job\s*\)(?!\s*[,])', src)
    assert not bad, f'Found bare db.refresh(job): {bad}'



def test_delete_job_with_refund_log(api, base_url, auth_headers):
    """Regression: RefundLog.job_id 有 FK 无级联.
    先 submit+cancel 产生退款记录, 再删 job.
    旧代码直接 db.delete(job) 触发 FK IntegrityError 500."""
    fd = {"task_type": "task2", "question": "del-refund-test", "essay": make_essay(260)}
    r = api.post(base_url + "/grading/submit", headers=auth_headers, data=fd, timeout=30)
    if r.status_code == 402:
        pytest.skip("not enough credits")
    if r.status_code != 200:
        pytest.skip(f"submit failed: {r.text[:200]}")
    job_id = r.json()["job_id"]
    time.sleep(0.5)
    # cancel 产生 RefundLog
    r = api.post(base_url + f"/grading/{job_id}/cancel", headers=auth_headers, timeout=10)
    assert r.status_code == 200, r.text[:200]
    # 删除该 job (有退款记录), 旧代码此处 500
    r = api.delete(base_url + f"/grading/{job_id}", headers=auth_headers, timeout=10)
    assert r.status_code == 200, f"delete failed: {r.text[:200]}"
    # job 已不存在
    r = api.get(base_url + f"/grading/{job_id}", headers=auth_headers, timeout=10)
    assert r.status_code == 404


def test_cancel_idempotent(api, base_url, auth_headers):
    """cancel 幂等: 同一 job 多次 cancel 应只退 1 次分.
    Bug fix: 之前返回 refunded 字段会误导前端 (一直显示 1), 现在分 already_refunded 区分."""
    fd = {"task_type": "task2", "question": "q", "essay": make_essay(260)}
    r = api.post(base_url + "/grading/submit", headers=auth_headers, data=fd, timeout=30)
    if r.status_code == 402: pytest.skip("not enough credits")
    if r.status_code != 200: pytest.skip("submit failed")
    job_id = r.json()["job_id"]
    time.sleep(0.5)
    me1 = api.get(base_url + "/users/me", headers=auth_headers, timeout=10).json()
    before = me1["credits"]
    # 第一次 cancel
    r1 = api.post(base_url + f"/grading/{job_id}/cancel", headers=auth_headers, timeout=10)
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["ok"] is True
    assert j1.get("refunded") == 1, f"first cancel should refund 1, got {j1}"
    assert j1.get("already_refunded") is False, f"first cancel: already_refunded should be False, got {j1}"
    time.sleep(0.5)
    me2 = api.get(base_url + "/users/me", headers=auth_headers, timeout=10).json()
    after_first = me2["credits"]
    # 第二次 cancel (幂等测试)
    r2 = api.post(base_url + f"/grading/{job_id}/cancel", headers=auth_headers, timeout=10)
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2.get("refunded") == 0, f"second cancel should NOT add credit, got {j2}"
    assert j2.get("already_refunded") is True, f"second cancel: already_refunded should be True, got {j2}"
    me3 = api.get(base_url + "/users/me", headers=auth_headers, timeout=10).json()
    after_second = me3["credits"]
    # 实际积分变化只有 1
    assert after_second - before == 1, f"total credit change should be +1, got {after_second - before}"
    assert after_first - before == 1, f"after first cancel should be +1, got {after_first - before}"
    assert after_second == after_first, f"after second cancel should not change credits, got {after_second} vs {after_first}"


def test_sample_essay_per_job_cooldown(api, base_url, auth_headers):
    """同一 job 在 SAMPLE_ESSAY_COOLDOWN (默认 60s) 内连续两次生成范文 -> 第二次 429"""
    # 用 make_essay 避免预检把"测试作文"判为模板/不相关 (导致整个测试被跳过无法验证限流)
    fd = {"task_type": "task2", "question": "Should rich countries help poorer ones?", "essay": make_essay(300)}
    r = api.post(base_url + "/grading/submit", headers=auth_headers, data=fd, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"submit failed: {r.status_code} {r.text[:200]}")
    jid = r.json().get("job_id")
    if not jid:
        pytest.skip("no job_id")
    for _ in range(120):
        st = api.get(base_url + f"/grading/{jid}", headers=auth_headers, timeout=5).json().get("status")
        if st == "done": break
    if st == "failed":
        pytest.skip("job failed")
    if st == "flagged":
        # 把预检理由也打出来, 便于排查"为什么正常作文被 flag"
        pc = api.get(base_url + f"/grading/{jid}", headers=auth_headers, timeout=5).json().get("precheck") or {}
        pytest.skip(f"job flagged: off_topic={pc.get('is_off_topic')} safety={pc.get('safety_ok')} wc={pc.get('word_count')} reason={pc.get('relevance_reason')}")
        time.sleep(2)
    else:
        pytest.skip("grading timeout")
    r1 = api.post(base_url + f"/grading/{jid}/sample-essay", headers=auth_headers, timeout=180)
    if r1.status_code == 400 and ("未完成" in r1.text or "无可用" in r1.text):
        pytest.skip("sample essay not available (no model or not done)")
    assert r1.status_code == 200, f"first call expected 200, got {r1.status_code}: {r1.text[:200]}"
    r2 = api.post(base_url + f"/grading/{jid}/sample-essay", headers=auth_headers, timeout=10)
    assert r2.status_code == 429, f"second call should 429, got {r2.status_code}: {r2.text[:200]}"
    body = r2.json() if r2.headers.get("content-type", "").startswith("application/json") else {}
    assert "冷却" in (body.get("detail") or ""), f"unexpected 429 message: {body}"

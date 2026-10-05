// ===== 工具 =====
function byId(id) { return document.getElementById(id); }
function escHtml(s) { if (s == null) return ""; var d = document.createElement("div"); d.textContent = String(s); return d.innerHTML; }
function toast(msg, type) { var t = document.createElement("div"); t.className = "toast" + (type ? " " + type : ""); t.textContent = msg; document.body.appendChild(t); setTimeout(function() { t.classList.add("hide"); setTimeout(function() { t.remove(); }, 300); }, 2700); }
function copyText(text) { navigator.clipboard.writeText(text).then(function() { toast("已复制", "success"); }); }
function timeAgo(iso) { if (!iso) return ""; var d = new Date(iso.indexOf("Z") === -1 && iso.indexOf("+") === -1 ? iso + "Z" : iso), now = new Date(), diff = (now - d) / 1000; if (diff < 60) return "刚刚"; if (diff < 3600) return Math.floor(diff/60) + " 分钟前"; if (diff < 86400) return Math.floor(diff/3600) + " 小时前"; return (d.getMonth()+1) + "/" + d.getDate() + " " + d.getHours() + ":" + String(d.getMinutes()).padStart(2,"0"); }

function confirmDialog(message) {
  return new Promise(function(resolve) {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = '<div class="modal-box"><div class="modal-msg">' + escHtml(message) + '</div><div class="modal-actions"><button class="btn btn-sm btn-outline modal-cancel">取消</button><button class="btn btn-sm btn-danger modal-ok">确认</button></div></div>';
    document.body.appendChild(overlay);
    overlay.querySelector('.modal-ok').onclick = function() { overlay.remove(); resolve(true); };
    overlay.querySelector('.modal-cancel').onclick = function() { overlay.remove(); resolve(false); };
  });
}

function promptDialog(message, defaultValue) {
  return new Promise(function(resolve) {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = '<div class="modal-box"><div class="modal-msg">' + escHtml(message) + '</div><input class="input" style="margin-top:8px" value="' + escHtml(defaultValue || '') + '"/><div class="modal-actions"><button class="btn btn-sm btn-outline modal-cancel">取消</button><button class="btn btn-sm btn-primary modal-ok">确认</button></div></div>';
    document.body.appendChild(overlay);
    var inp = overlay.querySelector('input');
    inp.focus(); inp.select();
    overlay.querySelector('.modal-ok').onclick = function() { var v = inp.value; overlay.remove(); resolve(v); };
    overlay.querySelector('.modal-cancel').onclick = function() { overlay.remove(); resolve(null); };
    inp.onkeydown = function(e) { if (e.key === 'Enter') { var v = inp.value; overlay.remove(); resolve(v); } };
  });
}

// ===== API =====
async function api(method, path, body, isForm) {
  var headers = {}; var t = localStorage.getItem("token");
  if (t) headers.Authorization = "Bearer " + t;
  var payload;
  if (isForm) { payload = body; }
  else { if (method !== "GET") headers["Content-Type"] = "application/json"; payload = JSON.stringify(body || {}); }
  var options = { method: method, headers: headers };
  if (method !== "GET") options.body = payload;
  var res = await fetch("/api" + path, options);
  if (res.status === 401) { localStorage.removeItem("token"); showAuth(); throw new Error("未登录"); }
  var data = await res.json().catch(function() { return {}; });
  if (!res.ok) throw new Error(data.detail || "请求失败");
  return data;
}

// ===== Auth Screen =====
function showAuth() { byId("auth-screen").classList.remove("hidden"); byId("app").classList.add("hidden"); }
function showApp() {
  byId("auth-screen").classList.add("hidden");
  byId("app").classList.remove("hidden");
  loadModelLabels();
}

async function loadModelLabels() {
  try {
    var list = await api("GET", "/admin/models");
    window.__modelLabels = {};
    if (Array.isArray(list)) list.forEach(function(m) { if (m && m.name) window.__modelLabels[m.name] = m; });
  } catch(e) { window.__modelLabels = {}; }
}

// ===== Router =====
function show(view) {
  document.querySelectorAll(".view").forEach(function(v) { v.classList.add("hidden"); });
  var el = byId("view-" + view); if (el) el.classList.remove("hidden");
  document.querySelectorAll(".nav-item").forEach(function(n) { n.classList.remove("active"); });
  var nav = byId("nav-" + view); if (nav) nav.classList.add("active");
  if (view === "grading") loadCredits();
  if (view === "history") loadHistory(1);
  if (view === "admin") switchAdminTab("models");
  if (view === "profile") loadProfile();
  // Bug #22: 切走时清理报告轮询
  if (view !== "report") {
    if (typeof pollTimer !== "undefined" && pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (window._progressTimers) {
      Object.keys(window._progressTimers).forEach(function(tid) { clearInterval(window._progressTimers[tid]); });
      window._progressTimers = {};
    }
  }
}
function router() {
  var h = location.hash || "#grading";
  if (!localStorage.getItem("token")) { showAuth(); return; }
  showApp();
  loadCredits();
  if (h.indexOf("#report/") === 0) { show("report"); pollReport(h.slice(8)); }
  else if (h === "#history") show("history");
  else if (h === "#admin") show("admin");
  else if (h === "#profile") show("profile");
  else show("grading");
}
window.addEventListener("hashchange", router);

// ===== Auth =====
function switchAuthTab(tab) {
  document.querySelectorAll(".auth-tab").forEach(function(t) { t.classList.toggle("active", t.id === "tab-" + tab); });
  byId("login-form").classList.toggle("hidden", tab !== "login");
  byId("register-form").classList.toggle("hidden", tab !== "register");
}
async function login() {
  try { var r = await api("POST", "/auth/login", { username: byId("login-u").value, password: byId("login-p").value }); localStorage.setItem("token", r.access_token); location.hash = "#grading"; router(); }
  catch (e) { toast(e.message, "error"); }
}
async function register() {
  try { var body = { username: byId("reg-u").value, password: byId("reg-p").value, email: byId("reg-email").value || null, invite_code: byId("reg-invite").value };
    await api("POST", "/auth/register", body); toast("注册成功，请登录", "success"); switchAuthTab("login"); byId("login-u").value = byId("reg-u").value; byId("login-p").focus(); }
  catch (e) { toast(e.message, "error"); }
}
function logout() { localStorage.removeItem("token"); location.hash = ""; showAuth(); }

// ===== Profile =====
async function loadProfile() {
  try { var me = await api("GET", "/users/me"); byId("pf-username").textContent = me.username; byId("pf-email").textContent = me.email || "未设置"; byId("pf-email-input").value = me.email || ""; byId("pf-role").textContent = me.role === "admin" ? "管理员" : "用户"; byId("pf-credits").textContent = me.credits; byId("pf-email-input").value = me.email || ""; }
  catch (e) { toast(e.message, "error"); }
}
async function updateEmail() { try { await api("PUT", "/users/email", { email: byId("pf-email-input").value || null }); toast("邮箱已更新", "success"); loadProfile(); } catch (e) { toast(e.message, "error"); } }
async function changePassword() { try { await api("POST", "/auth/change-password", { old_password: byId("pf-old-p").value, new_password: byId("pf-new-p").value }); toast("密码已修改", "success"); byId("pf-old-p").value = ""; byId("pf-new-p").value = ""; } catch (e) { toast(e.message, "error"); } }
async function redeemCode() { try { var r = await api("POST", "/users/redeem", { code: byId("pf-redeem").value }); toast("兑换成功！+" + r.added + " 满分币", "success"); byId("pf-redeem").value = ""; loadProfile(); } catch (e) { toast(e.message, "error"); } }

// ===== Grading =====
var currentType = "task2";
function selectType(type) { currentType = type; document.querySelectorAll(".type-btn").forEach(function(b) { b.classList.toggle("active", b.getAttribute("data-type") === type); }); byId("g-upload-wrap").classList.toggle("hidden", type !== "task1"); }
function initGrading() {
  byId("g-upload-zone").addEventListener("click", function() { byId("g-image").click(); });
  byId("g-image").onchange = function() { var f = byId("g-image").files[0]; if (f) { byId("g-upload-text").textContent = "✅ " + f.name; byId("g-upload-zone").classList.add("has-file"); } };
  // 字数统计
  var essayArea = byId("g-essay");
  var counter = document.createElement("div");
  counter.id = "essay-counter";
  counter.style.cssText = "text-align:right;font-size:12px;color:var(--muted);margin-top:4px";
  counter.textContent = "0 词";
  essayArea.parentNode.insertBefore(counter, essayArea.nextSibling);
  essayArea.addEventListener("input", function() {
    // Bug #18: 中英混合
    var _v = essayArea.value.trim();
    var cnChars = (_v.match(/[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]/g) || []).length;
    var enWords = _v.replace(/[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]/g, " ").split(/\s+/).filter(function(w) { return w.length > 0; }).length;
    var words = cnChars + enWords;
    var minWords = currentType === "task2" ? 250 : 150;
    counter.textContent = words + " 字 (" + cnChars + " 中 + " + enWords + " 英)" + (words < minWords ? " (≥" + minWords + ")" : " ✓");
    counter.style.color = words < minWords ? "var(--amber)" : "var(--green)";
    saveDraft();
  });
}

function saveDraft() {
  try {
    var q = byId("g-question") ? byId("g-question").value : "";
    var e = byId("g-essay") ? byId("g-essay").value : "";
    if (q || e) {
      localStorage.setItem("draft_essay", JSON.stringify({ question: q, essay: e, type: currentType, time: Date.now() }));
      var ind = document.querySelector(".draft-saved");
      if (ind) { ind.classList.add("show"); setTimeout(function() { ind.classList.remove("show"); }, 1500); }
    }
  } catch(e) {}
}
function loadDraft() {
  try {
    var raw = localStorage.getItem("draft_essay");
    if (!raw) return;
    var d = JSON.parse(raw);
    if (d && d.time && (Date.now() - d.time) < 86400000) {
      if (d.question && byId("g-question") && !byId("g-question").value) byId("g-question").value = d.question;
      if (d.essay && byId("g-essay") && !byId("g-essay").value) {
        byId("g-essay").value = d.essay;
        byId("g-essay").dispatchEvent(new Event("input"));
      }
      // Bug #16: 显示草稿距今多久
      var _agoMin = Math.floor((Date.now() - d.time) / 60000);
      var _agoStr = _agoMin < 60 ? _agoMin + " 分钟前" : Math.floor(_agoMin / 60) + " 小时前";
      toast("\u5DF2\u6062\u590D " + _agoStr + " \u7684\u8349\u7A3F", "success");
    }
  } catch(e) {}
}
function clearDraft() { try { localStorage.removeItem("draft_essay"); } catch(e) {} }
async function loadCredits() {
  try {
    var me = await api("GET", "/users/me");
    byId("credit-pill").textContent = "满分币 " + me.credits;
    var adminLink = byId("nav-admin");
    if (adminLink) adminLink.classList.toggle("hidden", me.role !== "admin");
  } catch (e) {
    byId("credit-pill").textContent = "满分币 -";
    // Bug #25: 失败时强制隐藏 admin link
    var _al = byId("nav-admin");
    if (_al) _al.classList.add("hidden");
  }
}

async function submitGrading() {
  var question = byId("g-question").value.trim(); var essay = byId("g-essay").value.trim();
  if (!question || !essay) { toast("请填写题目和作文", "error"); return; }
  var fd = new FormData(); fd.append("task_type", currentType); fd.append("question", question); fd.append("essay", essay);
  var img = byId("g-image").files[0]; if (currentType === "task1" && img) fd.append("image", img);
  var btn = byId("g-submit"); btn.disabled = true; btn.textContent = "提交中…";
  try { var r = await api("POST", "/grading/submit", fd, true); clearDraft(); location.hash = "#report/" + r.job_id; }
  catch (e) {
    // Bug #20: 余额不足引导去兑换
    var _msg = e.message || "";
    if (/满分币|insufficient|402/i.test(_msg)) {
      toast(_msg + " — 请前往个人中心兑换", "error");
      setTimeout(function() { location.hash = "#profile"; }, 1500);
    } else {
      toast(_msg, "error");
    }
    btn.disabled = false; btn.textContent = "提交批改";
  }
}

// ===== Report with Real-time Progress =====
var DN = { task2: { TR: "任务回应情况", CC: "连贯性与衔接", LR: "词汇丰富度", GRA: "语法多样性及准确性" }, task1: { TA: "任务完成情况", CC: "连贯性与衔接", LR: "词汇丰富度", GRA: "语法多样性及准确性" } };
var DIM_TOTAL = { task2: ["TR","CC","LR","GRA"], task1: ["TA","CC","LR","GRA"] };
var SUB_NAMES = { task2: { TR: ["回应题目","立场明确","观点拓展","内容疏漏"], CC: ["组织与逻辑","段落结构","逻辑推进","指代与替换","逻辑衔接"], LR: ["词汇广度","用词精准","词汇搭配","拼写与构词"], GRA: ["句式丰富度","语法准确性","语法及标点错误"] }, task1: { TA: ["整体回应","关键特征筛选","概述","数据支持","内容疏漏"], CC: ["信息组织","连接方式","内容疏漏","段落结构"], LR: ["词汇广度","用词精准","词汇搭配","拼写与构词"], GRA: ["句式丰富度","语法准确性","语法及标点错误"] } };
function badge(s) { var c = s == null ? "#94a3b8" : (s >= 8 ? "#059669" : s >= 7 ? "#6366f1" : s >= 6 ? "#d97706" : "#dc2626"); return '<span class="badge" style="background:' + c + '">' + (s == null ? "-" : s) + '</span>'; }
function fmtS(s) { if (s == null) return ""; if (typeof s === "string") return s; return (s.strength || s.point || "") + (s.example_quote ? ' \u201C' + s.example_quote + '\u201D' : ""); }
function fmtI(x) { if (x == null) return ""; if (typeof x === "string") return x; return (x.issue || x.point || "") + (x.suggestion ? " \u2192 " + x.suggestion : ""); }

var pollTimer = null;
function pollReport(id) {
  if (pollTimer) clearInterval(pollTimer);
  var startTime = Date.now();
  byId("report-body").innerHTML = '<div class="card"><div class="center"><div class="spinner" style="margin:0 auto 12px"></div>\u6b63\u5728\u52a0\u8f7d\u62a5\u544a\u2026</div></div>';
  (async function() {
    try {
      var r = await api("GET", "/grading/" + id);
      if (["done","flagged","failed"].indexOf(r.status) >= 0) {
        if (r.status === "done") {
          r._startTime = startTime;
          renderReport(r);
        } else if (r.status === "flagged") {
          var reason = '';
          if (r.precheck) {
            if (r.precheck.is_off_topic) reason = '\u4f5c\u6587\u5185\u5bb9\u4e0e\u9898\u76ee\u4e0d\u76f8\u5173';
            else if (!r.precheck.safety_ok) reason = '\u5185\u5bb9\u5b58\u5728\u5b89\u5168\u95ee\u9898';
            else if (r.precheck.below_min_words) reason = '\u5b57\u6570\u672a\u8fbe\u5230\u8981\u6c42 (Task 1 \u81f3\u5c11 150 \u8bcd, Task 2 \u81f3\u5c11 250 \u8bcd)';
            else reason = r.precheck.relevance_reason || '\u5185\u5bb9\u4e0d\u7b26\u5408\u8bc4\u5206\u8981\u6c42';
          }
byId('report-body').innerHTML = '<div class="card" style="max-width:680px;margin:24px auto;padding:26px">'
    + '<div style="text-align:center"><div style="font-size:44px;margin-bottom:8px">\u270d\ufe0f</div>'
    + '<h3 style="color:var(--muted);margin-bottom:10px">\u8fd9\u7bc7\u4f5c\u6587\u6682\u672a\u8bc4\u5206</h3>'
    + '<p style="margin-bottom:6px"><b>\u539f\u56e0\uff1a</b>' + escHtml(reason) + '</p>'
    + ((r.precheck && r.precheck.relevance_reason) ? '<p style="color:var(--muted);font-size:13px;margin-bottom:6px">' + escHtml(r.precheck.relevance_reason) + '</p>' : '')
    + ((r.precheck && r.precheck.word_count) ? '<p style="color:var(--muted);font-size:13px">\u5f53\u524d\u8bcd\u6570\uff1a' + r.precheck.word_count + '</p>' : '')
    + '</div>'
    + '<details style="margin-top:16px"><summary style="cursor:pointer;color:#3b82f6;font-weight:600">\ud83d\udcdd \u67e5\u770b\u9898\u76ee</summary>'
    + '<div style="white-space:pre-wrap;line-height:1.8;padding:14px;background:#eff6ff;border-radius:10px;margin-top:10px;color:#1e3a5f;font-size:14px">' + escHtml(r.question || '') + '</div></details>'
    + '<details style="margin-top:12px"><summary style="cursor:pointer;color:#3b82f6;font-weight:600">\u270d\ufe0f \u67e5\u770b\u6211\u7684\u4f5c\u6587</summary>'
    + '<div style="white-space:pre-wrap;line-height:1.8;padding:14px;background:#f8fafc;border-radius:10px;margin-top:10px;font-size:14px;max-height:300px;overflow:auto">' + escHtml(r.essay || '') + '</div></details>'
    + '<div style="text-align:center;margin-top:20px"><button class="btn btn-primary" onclick="refillFromFlagged(' + (r.job_id || r.id || id) + ')">\u270e\ufe0f \u4fee\u6539\u540e\u91cd\u4ea4</button></div>'
    + '</div>';
        } else {
          byId("report-body").innerHTML = '<div class="center">\u274c \u8bc4\u5206\u5931\u8d25\uff1a' + escHtml(r.error || "\u672a\u77e5\u9519\u8bef") + '</div><div class="center" style="margin-top:14px"><button class="btn btn-primary" onclick="retryJob(' + (r.job_id || r.id || id) + ')">\u25b6 \u7ee7\u7eed\u8bc4\u5206</button></div>';
        }
        return;
      }
      r._startTime = startTime;
      renderProgress(r);
    } catch (e) {
      if (/未登录|登录已失效|Invalid token|Unauthorized/i.test(e.message || "")) {
        // Bug #19: 兼容多种文案
        byId("report-body").innerHTML = '<div class="center">\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55\u540e\u67e5\u770b\u62a5\u544a<br><br><a href="#" class="back-btn" onclick="logout();return false;">\u2190 \u91cd\u65b0\u767b\u5f55</a></div>';
      }
      return;
    }
    pollTimer = setInterval(async function() {
      try {
        var r2 = await api("GET", "/grading/" + id);
        if (["done","flagged","failed"].indexOf(r2.status) >= 0) {
          clearInterval(pollTimer); pollTimer = null;
          if (r2.status === "done") {
            r2._startTime = startTime;
            renderReport(r2);
          } else if (r2.status === "flagged") {
byId('report-body').innerHTML = '<div class="card" style="max-width:680px;margin:24px auto;padding:26px">'
    + '<div style="text-align:center"><div style="font-size:44px;margin-bottom:8px">\u270d\ufe0f</div>'
    + '<h3 style="color:var(--muted);margin-bottom:10px">\u8fd9\u7bc7\u4f5c\u6587\u6682\u672a\u8bc4\u5206</h3>'
    + '<p style="margin-bottom:6px"><b>\u539f\u56e0\uff1a</b>' + escHtml(reason) + '</p>'
    + ((r2.precheck && r2.precheck.relevance_reason) ? '<p style="color:var(--muted);font-size:13px;margin-bottom:6px">' + escHtml(r2.precheck.relevance_reason) + '</p>' : '')
    + ((r2.precheck && r2.precheck.word_count) ? '<p style="color:var(--muted);font-size:13px">\u5f53\u524d\u8bcd\u6570\uff1a' + r2.precheck.word_count + '</p>' : '')
    + '</div>'
    + '<details style="margin-top:16px"><summary style="cursor:pointer;color:#3b82f6;font-weight:600">\ud83d\udcdd \u67e5\u770b\u9898\u76ee</summary>'
    + '<div style="white-space:pre-wrap;line-height:1.8;padding:14px;background:#eff6ff;border-radius:10px;margin-top:10px;color:#1e3a5f;font-size:14px">' + escHtml(r2.question || '') + '</div></details>'
    + '<details style="margin-top:12px"><summary style="cursor:pointer;color:#3b82f6;font-weight:600">\u270d\ufe0f \u67e5\u770b\u6211\u7684\u4f5c\u6587</summary>'
    + '<div style="white-space:pre-wrap;line-height:1.8;padding:14px;background:#f8fafc;border-radius:10px;margin-top:10px;font-size:14px;max-height:300px;overflow:auto">' + escHtml(r2.essay || '') + '</div></details>'
    + '<div style="text-align:center;margin-top:20px"><button class="btn btn-primary" onclick="refillFromFlagged(' + (r2.job_id || r2.id || id) + ')">\u270e\ufe0f \u4fee\u6539\u540e\u91cd\u4ea4</button></div>'
    + '</div>';
          } else {
            byId("report-body").innerHTML = '<div class="center">\u274c \u8bc4\u5206\u5931\u8d25\uff1a' + escHtml(r2.error || "\u672a\u77e5\u9519\u8bef") + '</div><div class="center" style="margin-top:14px"><button class="btn btn-primary" onclick="retryJob(' + (r2.job_id || r2.id || id) + ')">\u25b6 \u7ee7\u7eed\u8bc4\u5206</button></div>';
          }
        } else { r2._startTime = startTime; renderProgress(r2); }
      } catch (e) {
        if (/未登录|登录已失效|Invalid token|Unauthorized/i.test(e.message || "")) {
          clearInterval(pollTimer); pollTimer = null;
          byId("report-body").innerHTML = '<div class="center">\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u52a0\u8f7d\u540e\u67e5\u770b\u62a5\u544a<br><br><a href="#" class="back-btn" onclick="logout();return false;">\u2190 \u91cd\u65b0\u767b\u5f55</a></div>';
        }
      }
    }, 2500);
  })();
}

function renderProgress(job, jobStartTime) {
  var taskType = job.task_type || currentType;
  var dims = (job.result || {}).dimensions || {};
  var precheck = job.precheck;
  var dimOrder = DIM_TOTAL[taskType] || DIM_TOTAL.task2;
  var subNames = SUB_NAMES[taskType] || SUB_NAMES.task2;
  var totalSubs = dimOrder.reduce(function(s, d) { return s + subNames[d].length; }, 0);
  var doneSubs = 0;
  var doneDims = 0;
  var subDetails = [];

  dimOrder.forEach(function(dc) {
    if (dims[dc] && dims[dc].sub_scores) {
      dims[dc].sub_scores.forEach(function(s) {
        if (s.score != null) { doneSubs++; subDetails.push({dim: dc, area: s.area, score: s.score}); }
      });
      if (dims[dc].score != null) doneDims++;
    }
  });

  var hasImage = job.has_image || (job.result || {}).has_image;
  var vlmUsed = (job.result || {}).vlm_used;
  var overallPct = 0;
  if (precheck) overallPct += 5;
  if (vlmUsed) overallPct += 10;
  overallPct += Math.round((doneSubs / totalSubs) * 65);
  overallPct += Math.round((doneDims / 4) * 18);
  if (job.status === "done") overallPct += 2;
  overallPct = Math.min(100, overallPct);

  var steps = [
    { key: "precheck", label: "\u9884\u68c0\u68c0\u67e5", desc: "\u5b57\u6570\u3001\u76f8\u5173\u6027\u3001\u5b89\u5168", icon: "\ud83d\udd0d", done: !!precheck },
    { key: "vlm", label: "\u56fe\u7247\u8bc6\u522b", desc: "VLM \u591a\u6a21\u6001\u8bc6\u522b", icon: "\ud83d\uddbc", done: !!vlmUsed, hidden: !hasImage },
    { key: "subs", label: "\u5b50\u7ef4\u5ea6\u8bc4\u5206", desc: "16 \u4e2a\u5b50\u7ef4\u5ea6", icon: "\ud83d\udcca", done: doneSubs >= totalSubs, progress: doneSubs + "/" + totalSubs },
    { key: "dims", label: "\u7ef4\u5ea6\u5408\u6210", desc: "4 \u5927\u7ef4\u5ea6\u7efc\u5408", icon: "\ud83d\udd17", done: doneDims >= 4, progress: doneDims + "/4" },
    { key: "final", label: "\u751f\u6210\u62a5\u544a", desc: "\u603b\u5206\u8ba1\u7b97 + \u5efa\u8bae", icon: "\ud83d\udccb", done: job.status === "done" }
  ];

  var jobId = job.job_id || 0;
  var startTime = (typeof jobStartTime === 'number') ? jobStartTime : (job._startTime || Date.now());
  var elapsedSec = Math.floor((Date.now() - startTime) / 1000);
  var elapsedStr = elapsedSec >= 60 ? Math.floor(elapsedSec/60) + "\u5206" + (elapsedSec%60) + "\u79d2" : elapsedSec + "\u79d2";

  var html = '<div class="progress-modern" data-start-time="' + startTime + '">';
  html += '<div class="progress-header"><div class="progress-title"><span class="progress-spinner"></span><b>AI \u6b63\u5728\u8bc4\u5206\u4e2d</b></div>';
  html += '<div class="progress-overall"><div class="progress-overall-bar"><div class="progress-overall-fill" style="width:' + overallPct + '%"></div></div><span class="progress-overall-text">' + overallPct + '%</span></div></div>';
  html += '<div class="progress-timeline">';

  steps.forEach(function(step, idx) {
    if (step.hidden) return;
    var prevDone = idx === 0 || steps.slice(0, idx).every(function(s) { return s.hidden || s.done; });
    var stateClass = step.done ? "done" : (prevDone ? "active" : "pending");
    var isCurrent = !step.done && prevDone;

    html += '<div class="progress-step-modern ' + stateClass + '">';
    html += '<div class="step-dot">' + (step.done ? "\u2713" : (isCurrent ? '<span class="step-pulse"></span>' : step.icon)) + '</div>';
    html += '<div class="step-content">';
    html += '<div class="step-label">' + step.label + '</div>';
    html += '<div class="step-desc">' + step.desc + (step.progress ? ' \u00b7 ' + step.progress : '') + '</div>';
    html += '</div></div>';

    if (idx < steps.length - 1) {
      var nextStep = steps[idx + 1];
      if (!nextStep.hidden) {
        html += '<div class="step-connector ' + (step.done ? "done" : "") + '"></div>';
      }
    }
  });

  html += '</div>';
  if (subDetails.length > 0) {
    html += '<div class="progress-chips">';
    subDetails.slice(-8).forEach(function(d) {
      html += '<span class="progress-chip">' + escHtml(d.area) + ' <b>' + d.score + '</b></span>';
    });
    html += '</div>';
  }
  html += '<div class="progress-elapsed">\u5df2\u8017\u65f6 <b class="elapsed-time" data-start="' + startTime + '">' + elapsedStr + '</b></div>';
  html += '<div style="margin-top:20px;text-align:center"><button class="btn btn-danger" onclick="cancelJob('+jobId+', this)">\u23d1 \u53d6\u6d88\u8bc4\u5206</button></div>';
  html += '</div>';

  byId("report-body").innerHTML = html;

  if (!window._progressTimers) window._progressTimers = {};
  Object.keys(window._progressTimers).forEach(function(tid) {
    clearInterval(window._progressTimers[tid]);
  });
  window._progressTimers = {};

  window._progressTimers[jobId] = setInterval(function() {
    var el = document.querySelector(".elapsed-time");
    if (el) {
      var st = parseInt(el.getAttribute("data-start"));
      var s = Math.floor((Date.now() - st) / 1000);
      var m = Math.floor(s / 60);
      el.textContent = m > 0 ? m + "\u5206" + (s%60) + "\u79d2" : s + "\u79d2";
    } else {
      clearInterval(window._progressTimers[jobId]);
      delete window._progressTimers[jobId];
    }
  }, 1000);
}

function bandDesc(score) {
  if (typeof score !== 'number') return null;
  var s = Math.round(score * 2) / 2;
  var map = {
    9.0: '专家级', 8.5: '优秀', 8.0: '优秀',
    7.5: '良好', 7.0: '良好',
    6.5: '及格', 6.0: '及格',
    5.5: '中等', 5.0: '中等',
    4.5: '基础', 4.0: '基础',
    3.5: '初级', 3.0: '初级', 2.5: '初级', 2.0: '初级',
    1.0: '入门', 0.0: '入门'
  };
  return map[s] || null;
}

async function retryJob(jobId) {
  try {
    var r = await api("POST", "/grading/" + jobId + "/retry", {});
    if (r && r.ok) { toast("\u2705 \u5df2\u91cd\u65b0\u5165\u961f\uff0c\u4ece\u5df2\u5b8c\u6210\u7684\u8fdb\u5ea6\u7ee7\u7eed"); location.reload(); }
    else toast("\u274c " + (r && r.detail || "\u91cd\u8bd5\u5931\u8d25"));
  } catch (e) { toast("\u274c " + e.message); }
}
window.refillFromFlagged = function(jobId) {
  api("GET", "/grading/" + jobId).then(function(r) {
    var q = document.getElementById("g-question"), e = document.getElementById("g-essay");
    if (q) q.value = r.question || "";
    if (e) e.value = r.essay || "";
    var sel = document.querySelector('input[name=task-type][value="' + (r.task_type || "task2") + '"]');
    if (sel) sel.checked = true;
    location.hash = "#grading";
    toast("\u2705 \u5df2\u56de\u586b\u9898\u76ee\u548c\u4f5c\u6587\uff0c\u4fee\u6539\u540e\u76f4\u63a5\u63d0\u4ea4");
  }).catch(function(err) { toast("\u274c " + err.message); });
};

window.retryJob = retryJob;

window._dlToken = null;
window._dlTokens = {};  // Bug #17: 按 jobId 分桶
function _fetchDlToken(jobId) {
  jobId = jobId || window._currentJobId;
  if (!jobId) return Promise.resolve("");
  var _c = window._dlTokens[jobId]; if (_c && (Date.now() - _c.ts) < 240000) return Promise.resolve(_c.token);
  return api("GET", "/reports/" + jobId + "/download-token", {}, true).then(function(r) {
    window._dlTokens[jobId] = {token: r.token, ts: Date.now()};
    window._dlToken = r.token;
    return r.token;
  }).catch(function() { return ""; });
}
async function renderReport(job) {
  window._currentJobId = job.job_id || job.id || job;
  window._dlToken = await _fetchDlToken(window._currentJobId);  // 接住当前 job 的 token, 防止串号到别的报告
  var jobId = job.job_id || job.id;
  if (window._progressTimers) { Object.keys(window._progressTimers).forEach(function(tid) { clearInterval(window._progressTimers[tid]); }); window._progressTimers = {}; }
  var r = job.result || {};
  var dims = r.dimensions || {};
  var taskType = job.task_type || currentType;
  var dimOrder = DIM_TOTAL[taskType] || DIM_TOTAL.task2;
  var body = byId("report-body");
  body.innerHTML = "";

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function append(parent, tag, cls, text) {
    var e = el(tag, cls, text);
    parent.appendChild(e);
    return e;
  }
  function parseHTML(html) { var t = document.createElement("div"); t.innerHTML = html; return t.firstChild; }
  function _md(s) {
    if (!s) return "";
    var h = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    h = h.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
    h = h.replace(/\x60([^\x60]+)\x60/g, "<code style=\"background:#f1f5f9;padding:1px 6px;border-radius:3px;font-size:12px\">$1</code>");
    h = h.replace(/^#{1,3} (.+)$/gm, function(m, c) { return "<b style=\"color:var(--primary)\">" + c + "</b>"; });
    h = h.replace(/^- (.+)$/gm, "&bull; $1");
    h = h.replace(/\n/g, "<br/>");
    return h;
  }
  function collapseSection(header, contentEl) {
    var arrow = el("span");
    arrow.textContent = "\u25B8";
    arrow.style.cssText = "margin-left:auto;color:#94a3b8;font-size:13px;flex-shrink:0;transition:transform .2s";
    header.style.display = "flex";
    header.style.alignItems = "center";
    header.style.gap = "8px";
    header.style.cursor = "pointer";
    header.style.userSelect = "none";
    header.appendChild(arrow);
    contentEl.style.display = "none";
    var open = false;
    header.onclick = function() {
      open = !open;
      contentEl.style.display = open ? "" : "none";
      arrow.textContent = open ? "\u25BE" : "\u25B8";
      arrow.style.color = open ? "#6366f1" : "#94a3b8";
    };
  }
  function fmtScore(v) {
    if (typeof v !== "number" || isNaN(v)) return (v == null ? "-" : v);
    return Number.isInteger(v) ? String(v) : v.toFixed(1);
  }
  function cardHeader(card, emoji, title, extra) {
    var h = el("div");
    h.style.cssText = "font-weight:600;color:var(--primary);margin-bottom:10px;font-size:15px";
    h.textContent = emoji + " " + title;
    if (extra != null) {
      var s = el("span", "muted");
      s.style.cssText = "font-weight:400;font-size:12px;margin-left:8px";
      s.textContent = extra;
      h.appendChild(s);
    }
    card.appendChild(h);
    return h;
  }

  // ===== 1. 题目 =====
  if (job.question) {
    var qCard = el("div", "card slim-card");
    var qH = cardHeader(qCard, "\uD83D\uDCDD", "题目");
    var qContent = el("div");
    qContent.style.cssText = "line-height:1.8;white-space:pre-wrap;padding:14px 16px;background:#eff6ff;border-radius:10px;border-left:3px solid #3b82f6;color:#1e3a5f";
    qContent.textContent = job.question;
    qCard.appendChild(qContent);
    collapseSection(qH, qContent);
    body.appendChild(qCard);
  }

  // ===== 2. 图片 (仅小作文可能有) =====
  if (r.has_image && jobId) {
    var imgCard = el("div", "card slim-card");
    var imgH = cardHeader(imgCard, "\uD83D\uDDBC", "题目图表");
    var imgEl = el("img");
    imgEl.src = "/api/grading/" + jobId + "/image?token=" + encodeURIComponent(window._dlToken || "");
    imgEl.alt = "题目图表";
    imgEl.style.cssText = "max-width:100%;max-height:240px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);display:block;margin:0 auto;cursor:pointer";
    imgEl.onclick = function() { window.open(this.src, "_blank"); };
    imgEl.onerror = function() { imgCard.style.display = "none"; };
    imgCard.appendChild(imgEl);
    collapseSection(imgH, imgEl);
    body.appendChild(imgCard);
  }

  // ===== 3. 考生作文 =====
  if (job.essay) {
    var eCard = el("div", "card slim-card");
    var ew = (job.essay && job.essay.trim()) ? job.essay.trim().split(/\s+/).length : 0;
    var eH = cardHeader(eCard, "\u270F", "考生作文", ew + " 词");
    var eContent = el("div");
    eContent.style.cssText = "line-height:1.9;white-space:pre-wrap;padding:16px 18px;background:#f8fafc;border-radius:10px;border-left:3px solid #94a3b8;font-size:14px;color:#1e293b";
    eContent.textContent = job.essay;
    eCard.appendChild(eContent);
    collapseSection(eH, eContent);
    body.appendChild(eCard);
  }

  // ===== 4. 按钮行 =====
  var btnRow = el("div");
  btnRow.style.cssText = "margin:0 0 4px;display:flex;gap:8px;flex-wrap:wrap;align-items:center";
  var sBtn = el("button", "btn btn-primary");
  sBtn.textContent = "\u2728 生成个性化范文";
  sBtn.style.cssText = "background:var(--primary);color:#fff;border:none;padding:10px 20px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer";
  sBtn.onclick = function() { generateSampleEssay(jobId); };
  sBtn.id = "sample-essay-btn-" + jobId;
  if (job.status === "running" || job.status === "pending") { sBtn.disabled = true; sBtn.style.opacity = "0.5"; }
  btnRow.appendChild(sBtn);
  if (job.status === "running" || job.status === "pending") {
    var cBtn = el("button", "btn btn-danger");
    cBtn.id = "cancel-btn-" + jobId;
    cBtn.textContent = "\u26D4 取消评分";
    cBtn.onclick = function() { cancelJob(jobId, cBtn); };
    btnRow.appendChild(cBtn);
  }
  body.appendChild(btnRow);

  // ===== 5. 分数 =====
  var scoreDiv = el("div", "report-score");
  var scoreBig = el("div", "big");
  scoreBig.textContent = fmtScore(r.predicted_band);
  scoreDiv.appendChild(scoreBig);
  var scoreLabel = el("div", "muted");
  scoreLabel.style.cssText = "font-size:15px;font-weight:600";
  scoreLabel.textContent = "总分";
  scoreDiv.appendChild(scoreLabel);
  var bdDiv = el("div");
  bdDiv.style.cssText = "font-size:13px;color:var(--slate);font-weight:500;margin-top:4px";
  var bd = bandDesc(r.predicted_band);
  if (bd) bdDiv.textContent = "Band " + fmtScore(r.predicted_band) + " \u00B7 " + bd;
  scoreDiv.appendChild(bdDiv);
  var metaDiv = el("div", "report-meta");
  if (r.models_used && r.models_used.length) {
    var modelTag = el("span", "tag");
    var dN = (r.models_used || []).map(function(n) {
      if (typeof n === "object" && n) return (n.label || n.name) + (n.is_vision ? " \uD83D\uDC41" : "");
      var m = (window.__modelLabels || {})[n]; return (m && m.label) ? m.label + (m.is_vision ? " \uD83D\uDC41" : "") : n;
    });
    modelTag.textContent = "\uD83E\uDDE9 " + dN.join(", ");
    metaDiv.appendChild(modelTag);
  }
  if (job.created_at) {
    var dateTag = el("span", "tag muted");
    dateTag.textContent = "\uD83D\uDCC5 " + timeAgo(job.created_at);
    metaDiv.appendChild(dateTag);
  }
  if (job.finished_at && job.created_at) {
    var fms = new Date(job.finished_at).getTime(), cms = new Date(job.created_at).getTime();
    if (!isNaN(fms) && !isNaN(cms) && fms > cms) {
      var diffSec = Math.floor((fms - cms) / 1000);
      if (diffSec >= 1) {
        var tTag = el("span", "tag");
        tTag.textContent = "\u23F1 耗时 " + (diffSec >= 60 ? Math.floor(diffSec/60) + "分" + (diffSec%60) + "秒" : diffSec + "秒");
        metaDiv.appendChild(tTag);
      }
    }
  }
  scoreDiv.appendChild(metaDiv);
  body.appendChild(scoreDiv);

  // ===== 6. 雷达图 (无标题行, 干净) =====
  if (jobId && window.echarts) {
    var radarCard = el("div", "card");
    var radarDiv = el("div");
    radarDiv.id = "echarts-radar-" + jobId;
    radarDiv.style.cssText = "width:100%;max-width:440px;margin:0 auto;height:260px";
    radarCard.appendChild(radarDiv);
    body.appendChild(radarCard);
    api("GET", "/grading/" + jobId + "/radar-data").then(function(d) {
      var chart = echarts.init(radarDiv);
      var shortInd = (d.indicators || []).map(function(x) { var nm = x.name || ""; var m = /\(([A-Z]{2,4})\)/.exec(nm); return { name: m ? m[1] : nm, max: x.max }; });
      chart.setOption({
        tooltip: { show: false },
        radar: {
          indicator: shortInd,
          shape: "polygon",
          splitNumber: 4,
          center: ["50%", "52%"],
          radius: "62%",
          axisName: { color: "#334155", fontSize: 12, padding: [3, 3] },
          splitLine: { lineStyle: { color: "#94a3b8", width: 0.8 } },
          splitArea: { areaStyle: { color: ["rgba(250,251,252,0.6)", "rgba(241,245,249,0.6)"] } },
          axisLine: { lineStyle: { color: "#cbd5e1" } }
        },
        series: [{
          type: "radar",
          data: [{
            value: d.values,
            symbol: "circle",
            symbolSize: 8,
            lineStyle: { color: "#4f46e5", width: 3 },
            itemStyle: { color: "#4f46e5" },
            areaStyle: { color: "rgba(79, 70, 229, 0.25)" },
            label: { show: true, position: "top", color: "#1e293b", fontSize: 13, fontWeight: "bold", formatter: function(p) { return p.value; } }
          }]
        }]
      });
      window.addEventListener("resize", function() { chart.resize(); });
    }).catch(function(e) { radarDiv.textContent = "雷达图加载失败: " + e.message; });
  }

  // ===== 7. 合成维度 × 4 (含折叠子维度) =====
  dimOrder.forEach(function(k) {
    if (!dims[k]) return;
    var d = dims[k];
    var card = el("div", "report-dim-card");
    var head = el("div", "report-dim-head");
    var codeBig = el("b");
    codeBig.style.cssText = "color:var(--primary);font-size:18px";
    codeBig.textContent = k;
    head.appendChild(codeBig);
    var nameB = el("b");
    nameB.textContent = (DN[taskType] || {})[k] || "";
    head.appendChild(nameB);
    head.appendChild(parseHTML(badge(d.score)));
    card.appendChild(head);
    if (d.analysis_summary) {
      var analysis = el("div", "muted");
      analysis.style.cssText = "line-height:1.8;margin-top:8px";
      analysis.textContent = d.analysis_summary;
      card.appendChild(analysis);
    }
    if (d.sub_scores && d.sub_scores.length) {
      var subWrap = el("div");
      subWrap.style.cssText = "margin-top:12px;border-top:1px solid #e2e8f0";
      d.sub_scores.forEach(function(s) {
        if (!s || s.score == null) return;
        var row = el("div");
        row.style.cssText = "padding:10px 2px;border-bottom:1px solid #f1f5f9";
        var rowHead = el("div");
        rowHead.style.cssText = "display:flex;justify-content:space-between;align-items:center;gap:10px";
        var areaSpan = el("span");
        areaSpan.style.cssText = "font-weight:600;font-size:14px;color:#1e293b";
        areaSpan.textContent = s.area || "";
        rowHead.appendChild(areaSpan);
        var scoreChip = el("span");
        var sc = fmtScore(s.score);
        var chipColor = (s.score >= 7) ? "#16a34a" : (s.score >= 5.5 ? "#d97706" : "#dc2626");
        scoreChip.style.cssText = "flex-shrink:0;font-size:13px;font-weight:700;color:" + chipColor + ";background:" + chipColor + "1a;padding:2px 12px;border-radius:12px";
        scoreChip.textContent = sc;
        rowHead.appendChild(scoreChip);
        row.appendChild(rowHead);
        if (s.explanation) {
          var exDiv = el("div");
          exDiv.style.cssText = "margin-top:5px;font-size:13px;line-height:1.7;color:#64748b";
          exDiv.textContent = s.explanation;
          row.appendChild(exDiv);
        }
        if (s.current_do) {
          var cdDiv = el("div");
          cdDiv.style.cssText = "color:#16a34a;font-size:12px;margin-top:4px;line-height:1.6";
          cdDiv.textContent = "\u2705 " + s.current_do;
          row.appendChild(cdDiv);
        }
        if (s.to_reach_next) {
          var trDiv = el("div");
          trDiv.style.cssText = "color:#d97706;font-size:12px;margin-top:3px;line-height:1.6";
          trDiv.textContent = "\uD83C\uDFAF " + s.to_reach_next;
          row.appendChild(trDiv);
        }
        subWrap.appendChild(row);
      });
      card.appendChild(subWrap);
    }
    if (d.strengths && d.strengths.length) {
      var gb = el("div", "green-box");
      var gbT = el("b"); gbT.textContent = "优势"; gb.appendChild(gbT);
      var gbUl = el("ul"); gbUl.style.cssText = "margin:6px 0 0 18px";
      d.strengths.forEach(function(s) { var li = el("li"); li.textContent = fmtS(s); gbUl.appendChild(li); });
      gb.appendChild(gbUl);
      card.appendChild(gb);
    }
    if (d.improvements && d.improvements.length) {
      var ab = el("div", "amber-box");
      var abT = el("b"); abT.textContent = "待改进"; ab.appendChild(abT);
      var abUl = el("ul"); abUl.style.cssText = "margin:6px 0 0 18px";
      d.improvements.forEach(function(x) { var li = el("li"); li.textContent = fmtI(x); abUl.appendChild(li); });
      ab.appendChild(abUl);
      card.appendChild(ab);
    }
    body.appendChild(card);
  });

  // ===== 8. VLM 识别结果 (仅小作文带图) =====
  if (r.has_image && r.image_description) {
    var vlmCard = el("div", "card slim-card");
    var vlmH = cardHeader(vlmCard, "\uD83E\uDD16", "图片识别结果", r.vlm_used ? "VLM" : "未识别");
    var descDiv = el("div");
    descDiv.style.cssText = "line-height:1.8;padding:14px 16px;background:#f0f9ff;border-radius:10px;border-left:3px solid #0ea5e9;font-size:13px;color:#0c4a6e";
    descDiv.innerHTML = _md(r.image_description);
    vlmCard.appendChild(descDiv);
    collapseSection(vlmH, descDiv);
    body.appendChild(vlmCard);
  }

  // ===== 9. 整体修改建议 =====
  var sugg = r.suggestion;
  if (sugg && sugg.paragraphs) {
    var suggCard = el("div", "card");
    cardHeader(suggCard, "\uD83D\uDCAC", "整体修改建议");
    if (sugg.overall_feedback) {
      var fbDiv = el("div", "muted");
      fbDiv.style.cssText = "margin-bottom:12px;line-height:1.8";
      fbDiv.textContent = sugg.overall_feedback;
      suggCard.appendChild(fbDiv);
    }
    sugg.paragraphs.forEach(function(p) {
      var validItems = (p.items || []).filter(function(item) { return item.original !== item.revised && item.error_type !== "无"; });
      if (!validItems.length) return;
      var pDiv = el("div");
      pDiv.style.cssText = "margin-bottom:12px";
      var pLabel = el("div", "muted");
      pLabel.style.cssText = "font-size:13px;font-weight:600;margin-bottom:4px";
      pLabel.textContent = "第 " + p.paragraph + " 段";
      pDiv.appendChild(pLabel);
      validItems.forEach(function(item) {
        var itemDiv = el("div", "suggestion-item");
        if (item.error_type) {
          var typeSpan = el("span", "suggestion-type");
          typeSpan.textContent = item.error_type;
          itemDiv.appendChild(typeSpan);
        }
        if (item.original) { var o = el("div", "suggestion-original"); o.textContent = item.original; itemDiv.appendChild(o); }
        if (item.revised) { var rv = el("div", "suggestion-revised"); rv.textContent = item.revised; itemDiv.appendChild(rv); }
        if (item.analysis) { var an = el("div", "suggestion-analysis"); an.textContent = item.analysis; itemDiv.appendChild(an); }
        pDiv.appendChild(itemDiv);
      });
      suggCard.appendChild(pDiv);
    });
    body.appendChild(suggCard);
  }

  // ===== 10. 逐句修改建议 =====
  if (r.sentence_suggestions && r.sentence_suggestions.length) {
    var needsRev = r.sentence_suggestions.filter(function(s) { return s && !s.error && s.needs_revision; });
    if (needsRev.length) {
      var sentCard = el("div", "card");
      cardHeader(sentCard, "\uD83D\uDCDD", "逐句修改建议", needsRev.length + " 句需修改");
      var sentList = el("div");
      sentList.style.cssText = "margin-top:12px";
      needsRev.forEach(function(s, idx) {
        var item = el("div");
        var borderColor = "#dc2626", bgColor = "#fef2f2";
        if (s.error_type) {
          if (s.error_type.indexOf("表达") >= 0) { borderColor = "#d97706"; bgColor = "#fffbeb"; }
          else if (s.error_type.indexOf("词汇") >= 0 || s.error_type.indexOf("拼写") >= 0) { borderColor = "#7c3aed"; bgColor = "#f5f3ff"; }
        }
        item.style.cssText = "margin-bottom:14px;padding:14px;background:" + bgColor + ";border-radius:8px;border-left:4px solid " + borderColor + ";box-shadow:0 1px 3px rgba(0,0,0,0.05)";
        var header = el("div");
        header.style.cssText = "display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding-bottom:6px;border-bottom:1px dashed " + borderColor;
        var left = el("div");
        left.style.cssText = "font-weight:600;color:" + borderColor;
        var displayNum = (typeof s._index === "number") ? s._index + 1 : idx + 1;
        left.textContent = "第 " + displayNum + " 句" + (s.error_type ? " \u00B7 " + s.error_type : "");
        header.appendChild(left);
        var right = el("span");
        right.style.cssText = "font-size:11px;background:" + borderColor + ";color:#fff;padding:2px 8px;border-radius:10px";
        right.textContent = "需修改";
        header.appendChild(right);
        item.appendChild(header);
        if (s.original) {
          var origBox = el("div");
          origBox.style.cssText = "background:#fff;padding:10px 12px;border-radius:6px;margin-bottom:6px;font-size:14px;line-height:1.7;color:#475569;text-decoration:line-through;text-decoration-color:#cbd5e1;border:1px solid #e2e8f0";
          origBox.textContent = s.original;
          item.appendChild(origBox);
        }
        if (s.revised) {
          var revBox = el("div");
          revBox.style.cssText = "background:#ecfdf5;padding:10px 12px;border-radius:6px;margin-bottom:6px;font-size:14px;line-height:1.7;color:#065f46;border:1px solid #86efac;font-weight:500";
          revBox.textContent = "\u2713 " + s.revised;
          item.appendChild(revBox);
        }
        if (s.analysis) {
          var anaBox = el("div");
          anaBox.style.cssText = "background:#eff6ff;padding:8px 12px;border-radius:6px;margin-top:6px;font-size:13px;line-height:1.6;color:#1e40af";
          anaBox.textContent = "\uD83D\uDCA1 " + s.analysis;
          item.appendChild(anaBox);
        }
        sentList.appendChild(item);
      });
      sentCard.appendChild(sentList);
      body.appendChild(sentCard);
    }
  }
  if (sugg && sugg.error) {
    var errCard = el("div", "card");
    cardHeader(errCard, "\u26A0", "建议生成失败");
    var errDiv = el("div", "muted");
    errDiv.textContent = sugg.error;
    errCard.appendChild(errDiv);
    body.appendChild(errCard);
  }
}

  // (Radar chart now rendered as PNG via backend endpoint)

function filterAdminTable() {
  var search = (byId("ag-search") ? byId("ag-search").value : "").toLowerCase();
  var status = byId("ag-filter-status") ? byId("ag-filter-status").value : "";
  byId("admin-grading-body").querySelectorAll(".admin-grading-card").forEach(function(card) {
    var text = card.textContent.toLowerCase();
    var cardStatus = card.querySelector(".hist-status");
    var matchSearch = !search || text.indexOf(search) !== -1;
    var matchStatus = !status || (cardStatus && cardStatus.className.indexOf(status) !== -1);
    card.style.display = (matchSearch && matchStatus) ? "" : "none";
  });
}

// ===== History =====
var historyPage = 1;
async function loadHistory(page) {
  if (typeof page === 'number') historyPage = page; if (typeof historyPage !== 'number') historyPage = 1;
  try {
    var r = await api("GET", "/grading/?page=" + historyPage + "&page_size=10");
    if (!r.items || r.items.length === 0) { byId("history-body").innerHTML = '<div class="center">\u6682\u65E0\u5386\u53F2\u8BB0\u5F55</div>'; return; }
    var html = r.items.map(function(j) {
      var statusText = { done: "\u5DF2\u5B8C\u6210", pending: "\u7B49\u5F85\u4E2D", running: "\u8BC4\u5206\u4E2D", failed: "\u5f02\u5e38", flagged: "\u5f85\u4fee\u6539" }[j.status] || j.status;
      return '<div class="hist-card" data-jump="' + j.id + '" style="cursor:pointer"><div class="hist-left"><b>#' + j.id + ' ' + (j.task_type === "task2" ? "大作文" : "小作文") + '</b> <span class="hist-title">' + (j.title || ((j.question || '').length > 24 ? (j.question || '').substring(0, 24) + '\u2026' : j.question)) + '</span> <span class="hist-status ' + j.status + '">' + statusText + '</span><br><span class="muted">' + timeAgo(j.created_at) + '</span></div><div style="display:flex;align-items:center;gap:8px"><b class="hist-score">' + (j.predicted_band == null ? "…" : j.predicted_band) + '</b><button class="delete-btn" data-del-job="' + j.id + '" title="删除">✖</button></div></div>';
    }).join("");
    var totalPages = Math.ceil((r.total || 0) / 10);
    if (totalPages > 1) {
      html += '<div style="display:flex;gap:8px;justify-content:center;margin-top:16px;align-items:center">';
      if (historyPage > 1) html += '<button class="btn btn-sm btn-outline" id="hist-prev">\u4E0A\u4E00\u9875</button>';
      html += '<span class="muted">' + historyPage + ' / ' + totalPages + '</span>';
      if (historyPage < totalPages) html += '<button class="btn btn-sm btn-outline" id="hist-next">\u4E0B\u4E00\u9875</button>';
      html += '</div>';
    }
    byId("history-body").innerHTML = html;
    var prevBtn = byId("hist-prev"); if (prevBtn) prevBtn.onclick = function() { loadHistory(historyPage - 1); };
    var nextBtn = byId("hist-next"); if (nextBtn) nextBtn.onclick = function() { loadHistory(historyPage + 1); };
    byId("history-body").querySelectorAll("button[data-del-job]").forEach(function(btn) {
      btn.onclick = function(e) { e.stopPropagation(); deleteJob(parseInt(btn.getAttribute("data-del-job"))); };
    });
    byId("history-body").querySelectorAll(".hist-card").forEach(function(card) {
      card.onclick = function() { location.hash = "#report/" + card.getAttribute("data-jump"); };
    });
  } catch (e) { byId("history-body").innerHTML = '<div class="center">\u52A0\u8F7D\u5931\u8D25</div>'; }
}
async function deleteJob(id) {
  // Bug #21
  if (!await confirmDialog("\u786E\u8BA4\u5220\u9664\u8FD9\u6761\u8BB0\u5F55\uFF1F")) return;
  try { await api("DELETE", "/grading/" + id); toast("\u5DF2\u5220\u9664", "success"); loadHistory(historyPage); }
  catch (e) { toast(e.message, "error"); }
}

function showLoading(elId) { var el = byId(elId); if (el) el.innerHTML = '<div class="center"><div class="spinner" style="margin:0 auto"></div><div style="margin-top:8px">加载中…</div></div>'; }

// ===== Admin =====
function switchAdminTab(tab) {
  document.querySelectorAll(".admin-tab").forEach(function(t) { t.classList.toggle("active", t.getAttribute("data-tab") === tab); });
  document.querySelectorAll(".admin-panel").forEach(function(p) { p.classList.add("hidden"); });
  var panel = byId("admin-" + tab); if (panel) panel.classList.remove("hidden");
  if (tab === "models") loadModels();
  if (tab === "users") loadUsers();
  if (tab === "grading") loadAdminGrading();
  if (tab === "invites") loadInvites();
  if (tab === "settings") loadSettings();
  if (tab === "redeems") loadRedeems();
}
async function pullModels() {
  try { var r = await api("POST", "/admin/models/pull", { base_url: byId("m-base").value, api_key: byId("m-key").value });
    var html = r.models.map(function(m) { var id = typeof m === "string" ? m : m.id;
      var displayName = (typeof m === "object" && m.name) ? m.name : id;
      var isVlmGuess = /vlm|vision|gpt-4o|claude-3|gemini|qwen-vl|internvl|vl|llava/i.test(id); var capHint = isVlmGuess ? '<span class="cap-hint vision">📷视觉</span><span class="cap-hint text">📝文本</span>' : '<span class="cap-hint text">📝文本</span>'; return '<div class="code-card"><div style="flex:1"><code>' + escHtml(id) + '</code> ' + capHint + '</div><button class="btn btn-sm btn-primary" data-mid="' + encodeURIComponent(id) + '" data-mname="' + encodeURIComponent(displayName) + '">保存</button></div>';
    }).join(""); byId("models-body").innerHTML = html || '<div class="muted">\u65E0\u6A21\u578B</div>';
    byId("models-body").querySelectorAll("button[data-mid]").forEach(function(btn) { btn.onclick = function() { saveModelWithPicker(decodeURIComponent(btn.getAttribute("data-mid")), decodeURIComponent(btn.getAttribute("data-mname") || "")); }; });
  } catch (e) { toast(e.message, "error"); }
}
function closeModelPickerModal() {
  var modals = document.querySelectorAll(".model-picker-overlay");
  for (var i = 0; i < modals.length; i++) modals[i].remove();
}

async function saveModelWithPicker(id, defaultLabel) {
  defaultLabel = defaultLabel || id;
  closeModelPickerModal();
  var isVlmGuess = /vlm|vision|gpt-4o|claude-3|gemini|qwen-vl|internvl|vl|llava/i.test(id);
  var overlay = document.createElement("div");
  overlay.className = "model-picker-overlay";
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px";
  var box = document.createElement("div");
  box.style.cssText = "background:#fff;border-radius:12px;max-width:520px;width:100%;padding:24px;box-shadow:0 20px 60px rgba(0,0,0,0.3)";
  box.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px"><h3 style="margin:0">⚙️ 配置模型</h3><button class="btn btn-sm modal-close">✕</button></div>' +
    '<div style="margin-bottom:16px"><label style="display:block;font-size:13px;color:var(--slate);margin-bottom:4px">模型 ID</label><div style="padding:8px;background:#f8fafc;border-radius:6px;font-family:monospace;font-size:13px;word-break:break-all">' + escHtml(id) + '</div></div>' +
    '<div style="margin-bottom:16px"><label style="display:block;font-size:13px;color:var(--slate);margin-bottom:4px">显示名称 (Label)</label><input id="mp-label" class="input" placeholder="如: DeepSeek-V4-Pro" value="' + escHtml(defaultLabel) + '"/></div>' +
    '<div style="margin-bottom:16px"><label style="display:block;font-size:13px;color:var(--slate);margin-bottom:4px">标签 (逗号分隔)</label><input id="mp-tags" class="input" placeholder="如: 主力, 文本" value="' + (isVlmGuess ? "视觉" : "文本") + '"/></div>' +
    '<div style="margin-bottom:16px;display:flex;gap:20px"><label style="display:flex;align-items:center;gap:6px;cursor:pointer"><input type="checkbox" id="mp-text" ' + (!isVlmGuess ? "checked" : "") + '/> 支持文本</label><label style="display:flex;align-items:center;gap:6px;cursor:pointer"><input type="checkbox" id="mp-vision" ' + (isVlmGuess ? "checked" : "") + '/> 支持视觉 (VLM)</label></div>' +
    '<div style="margin-bottom:16px"><label style="display:block;font-size:13px;color:var(--slate);margin-bottom:4px">优先级 (越高越优先)</label><input type="number" id="mp-priority" class="input" value="0" min="0" max="100"/></div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:24px"><button class="btn btn-outline modal-cancel">取消</button><button class="btn btn-primary modal-save">保存</button></div>';
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  var closeModal = function() { overlay.remove(); };
  box.querySelector(".modal-close").onclick = closeModal;
  box.querySelector(".modal-cancel").onclick = closeModal;
  overlay.onclick = function(e) { if (e.target === overlay) closeModal(); };
  box.querySelector(".modal-save").onclick = async function() {
    var label = byId("mp-label").value.trim() || id;
    var tagsRaw = byId("mp-tags").value || "";
    var tags = tagsRaw.split(",").map(function(t) { return t.trim(); }).filter(function(t) { return t; });
    var isText = byId("mp-text").checked;
    var isVision = byId("mp-vision").checked;
    var priority = parseInt(byId("mp-priority").value) || 0;
    try {
      await api("POST", "/admin/models", {
        name: id,
        label: label,
        tags: tags,
        base_url: byId("m-base").value,
        api_key: byId("m-key").value,
        model_name: id,
        is_vision: isVision,
        is_text: isText,
        priority: priority,
        fallback_models: []
      });
      closeModal();
      toast("模型已保存", "success");
      loadModels();
    } catch (e) {
      toast(e.message, "error");
    }
  };
}

async function saveModel(id) {
  try {
    var isText = byId("cap-text-" + id) ? byId("cap-text-" + id).checked : true;
    var isVision = byId("cap-vision-" + id) ? byId("cap-vision-" + id).checked : /vlm|vision|gpt-4o|claude-3|gemini|qwen-vl|internvl|vl|llava/i.test(id);
var labelVal = byId("model-label-" + id) ? byId("model-label-" + id).value.trim() : "";
    var tagsVal = byId("model-tags-" + id) ? byId("model-tags-" + id).value.split(",").map(function(t) { return t.trim(); }).filter(function(t) { return t; }) : [];
        await api("POST", "/admin/models", { name: id, label: labelVal || id, tags: tagsVal, base_url: byId("m-base").value, api_key: byId("m-key").value, model_name: id, is_vision: isVision, is_text: isText, priority: 0, fallback_models: [] });
    toast("模型已保存", "success"); loadModels();
  } catch (e) { toast(e.message, "error"); }
}
async function editModel(id) {
  var r = await api("GET", "/admin/models");
  var m = r.find(function(x) { return x.id === id; });
  if (!m) { toast("模型不存在", "error"); return; }
  closeModelPickerModal();
  var overlay = document.createElement("div");
  overlay.className = "model-picker-overlay";
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px";
  var box = document.createElement("div");
  box.style.cssText = "background:#fff;border-radius:12px;max-width:520px;width:100%;padding:24px;box-shadow:0 20px 60px rgba(0,0,0,0.3)";
  box.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px"><h3 style="margin:0">✏️ 编辑模型</h3><button class="btn btn-sm modal-close">✕</button></div>' +
    '<div style="margin-bottom:16px"><label style="display:block;font-size:13px;color:var(--slate);margin-bottom:4px">模型 ID</label><div style="padding:8px;background:#f8fafc;border-radius:6px;font-family:monospace;font-size:13px">' + escHtml(m.model_name) + '</div></div>' +
    '<div style="margin-bottom:16px"><label style="display:block;font-size:13px;color:var(--slate);margin-bottom:4px">显示名称 (Label)</label><input id="mp-label" class="input" value="' + escHtml(m.label || "") + '"/></div>' +
    '<div style="margin-bottom:16px"><label style="display:block;font-size:13px;color:var(--slate);margin-bottom:4px">标签 (逗号分隔)</label><input id="mp-tags" class="input" value="' + escHtml((m.tags || []).join(",")) + '"/></div>' +
    '<div style="margin-bottom:16px;display:flex;gap:20px"><label style="display:flex;align-items:center;gap:6px;cursor:pointer"><input type="checkbox" id="mp-text" ' + (m.is_text ? "checked" : "") + '/> 支持文本</label><label style="display:flex;align-items:center;gap:6px;cursor:pointer"><input type="checkbox" id="mp-vision" ' + (m.is_vision ? "checked" : "") + '/> 支持视觉 (VLM)</label></div>' +
    '<div style="margin-bottom:16px"><label style="display:block;font-size:13px;color:var(--slate);margin-bottom:4px">优先级</label><input type="number" id="mp-priority" class="input" value="' + (m.priority === null || m.priority === undefined ? 0 : m.priority) + '" min="0" max="100"/></div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:24px"><button class="btn btn-outline modal-cancel">取消</button><button class="btn btn-primary modal-save">保存</button></div>';
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  var closeModal = function() { overlay.remove(); };
  box.querySelector(".modal-close").onclick = closeModal;
  box.querySelector(".modal-cancel").onclick = closeModal;
  overlay.onclick = function(e) { if (e.target === overlay) closeModal(); };
  box.querySelector(".modal-save").onclick = async function() {
    var label = byId("mp-label").value.trim() || m.name;
    var tags = (byId("mp-tags").value || "").split(",").map(function(t) { return t.trim(); }).filter(function(t) { return t; });
    var isText = byId("mp-text").checked;
    var isVision = byId("mp-vision").checked;
    var priority = parseInt(byId("mp-priority").value) || 0;
    try {
      await api("PATCH", "/admin/models/" + m.id, {
        label: label, tags: tags, is_text: isText, is_vision: isVision, priority: priority
      });
      closeModal();
      toast("模型已更新", "success");
      loadModels();
    } catch (e) {
      toast(e.message, "error");
    }
  };
}

async function loadModels() {
  showLoading("models-body");
  try { var r = await api("GET", "/admin/models");
    byId("models-body").innerHTML = r.length ? r.map(function(m) {
      return '<div class="model-info"><div class="model-label">' + escHtml(m.label || m.name) + '</div><div class="model-meta"><code>' + escHtml(m.model_name) + '</code> <span class="muted">' + (m.is_vision ? "视觉" : "文本") + '</span> <span class="muted">优先级: ' + (m.priority === null || m.priority === undefined ? '未设置' : m.priority) + '</span></div><div class="model-tags">' + (m.tags || []).map(function(t) { return '<span class="model-tag">' + t + '</span>'; }).join('') + '</div><div class="model-actions" style="margin-top:8px;display:flex;gap:8px;align-items:center"><input type="number" data-prio="' + m.id + '" value="' + (m.priority === null || m.priority === undefined ? '' : m.priority) + '" style="width:60px"/><button class="btn btn-sm" data-toggle="' + m.id + '">' + (m.enabled ? "停用" : "启用") + '</button><button class="btn btn-sm" data-edit="' + m.id + '">编辑</button><button class="btn btn-sm btn-danger" data-del="' + m.id + '">删除</button></div></div></div>';
    }).join("") : '<div class="muted">\u5C1A\u672A\u914D\u7F6E\u6A21\u578B</div>';
    byId("models-body").querySelectorAll("button[data-toggle]").forEach(function(btn) { btn.onclick = function() { toggleModel(parseInt(btn.getAttribute("data-toggle"))); }; });
    byId("models-body").querySelectorAll("button[data-del]").forEach(function(btn) { btn.onclick = function() { delModel(parseInt(btn.getAttribute("data-del"))); }; });
    byId("models-body").querySelectorAll("button[data-edit]").forEach(function(btn) { btn.onclick = function() { editModel(parseInt(btn.getAttribute("data-edit"))); }; });
    byId("models-body").querySelectorAll("input[data-prio]").forEach(function(inp) { inp.onchange = function() { updateModelPriority(parseInt(inp.getAttribute("data-prio")), parseInt(inp.value)); }; });
  } catch (e) { byId("models-body").innerHTML = '<div class="center">\u52A0\u8F7D\u5931\u8D25</div>'; }
}
async function toggleModel(id) { try { await api("POST", "/admin/models/" + id + "/toggle"); loadModels(); } catch (e) { toast(e.message, "error"); } }
async function delModel(id) {
  // Bug #21
  if (!await confirmDialog("\u786E\u8BA4\u5220\u9664\uFF1F")) return; try { await api("DELETE", "/admin/models/" + id); toast("\u5DF2\u5220\u9664", "success"); loadModels(); } catch (e) { toast(e.message, "error"); } }
async function updateModelPriority(id, priority) { try { await api("PATCH", "/admin/models/" + id, { priority: priority }); toast("\u4F18\u5148\u7EA7\u5DF2\u66F4\u65B0", "success"); } catch (e) { toast(e.message, "error"); } }

async function loadUsers() {
  showLoading("users-body");
  try { var r = await api("GET", "/admin/users");
    byId("users-body").innerHTML = r.map(function(u) {
      return '<div class="user-card"><div class="u-info"><b>' + escHtml(u.username) + '</b> <span class="muted">' + escHtml(u.role) + (u.disabled ? " \xB7 \u7981\u7528" : "") + '</span><br><span class="muted">' + escHtml(u.email || "\u65E0\u90AE\u7BB1") + ' \xB7 \u6EE1\u5206\u5E01 ' + u.credits + '</span></div><div class="u-actions"><button class="btn btn-sm btn-success" data-recharge="' + u.id + '">+充值</button><button class="btn btn-sm btn-outline" data-reset="' + u.id + '">\u91CD\u7F6E\u5BC6\u7801</button><button class="btn btn-sm ' + (u.disabled ? "btn-success" : "btn-danger") + '" data-toggle-u="' + u.id + '">' + (u.disabled ? "\u542F\u7528" : "\u7981\u7528") + '</button><button class="btn btn-sm btn-danger" data-del-u="' + u.id + '">\u5220\u9664</button></div></div>';
    }).join("");
    byId("users-body").querySelectorAll("button[data-recharge]").forEach(function(btn) { btn.onclick = function() { recharge(parseInt(btn.getAttribute("data-recharge")), 10); }; });
    byId("users-body").querySelectorAll("button[data-reset]").forEach(function(btn) { btn.onclick = function() { resetPassword(parseInt(btn.getAttribute("data-reset"))); }; });
    byId("users-body").querySelectorAll("button[data-toggle-u]").forEach(function(btn) { btn.onclick = function() { toggleUser(parseInt(btn.getAttribute("data-toggle-u"))); }; });
    byId("users-body").querySelectorAll("button[data-del-u]").forEach(function(btn) { btn.onclick = function(e) { e.stopPropagation(); deleteUser(parseInt(btn.getAttribute("data-del-u"))); }; });
  } catch (e) { byId("users-body").innerHTML = '<div class="center">\u52A0\u8F7D\u5931\u8D25</div>'; }
}
async function recharge(id, amt) {
  if (!amt) { amt = parseInt(prompt("输入充值满分币数量", "10")); if (!amt || amt <= 0) return; }
  try { await api("POST", "/admin/recharge", { user_id: id, amount: amt }); toast("\u5145\u503C\u6210\u529F", "success"); loadUsers(); } catch (e) { toast(e.message, "error"); } }
async function resetPassword(id) { var pw = prompt("\u8F93\u5165\u65B0\u5BC6\u7801\uFF08\u81F3\u5C116\u4F4D\uFF09"); if (!pw) return; if (pw.length < 6) { toast("\u5BC6\u7801\u81F3\u5C116\u4F4D", "error"); return; } try { await api("POST", "/admin/reset-password", { user_id: id, new_password: pw }); toast("\u5BC6\u7801\u5DF2\u91CD\u7F6E", "success"); } catch (e) { toast(e.message, "error"); } }
async function toggleUser(id) { try { await api("POST", "/admin/toggle-disable?user_id=" + id); toast("\u5DF2\u5207\u6362", "success"); loadUsers(); } catch (e) { toast(e.message, "error"); } }
async function deleteUser(id) {
  // Bug #21
  if (!await confirmDialog("\u786E\u8BA4\u5220\u9664\u8BE5\u7528\u6237\uFF1F")) return; try { await api("DELETE", "/admin/users/" + id); toast("\u5DF2\u5220\u9664", "success"); loadUsers(); } catch (e) { toast(e.message, "error"); } }

var adminGradingPage = 1;
async function loadAdminGrading(page) {
  if (typeof page === 'number') adminGradingPage = page; if (typeof adminGradingPage !== 'number') adminGradingPage = 1;
  showLoading("admin-grading-body");
  try { var r = await api("GET", "/admin/grading?page=" + adminGradingPage + "&page_size=20");
    if (!r.items || r.items.length === 0) { byId("admin-grading-body").innerHTML = '<div class="muted">\u6682\u65E0\u8BB0\u5F55</div>'; return; }
    var html = '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap"><input class="input" id="ag-search" placeholder="搜索题目或用户名..." style="flex:1;min-width:150px"/><select class="input" id="ag-filter-status" style="width:auto"><option value="">全部状态</option><option value="done">已完成</option><option value="running">评分中</option><option value="pending">等待中</option><option value="failed">失败</option><option value="flagged">违规</option></select></div><div class="agc-list"><th>ID</th><th>\u7528\u6237</th><th>\u7C7B\u578B</th><th>\u72B6\u6001</th><th>\u5206\u6570</th><th>\u9898\u76EE</th><th>\u65F6\u95F4</th><th></th>';
    html += r.items.map(function(j) {
      var statusText = { done: "\u5DF2\u5B8C\u6210", pending: "\u7B49\u5F85\u4E2D", running: "\u8BC4\u5206\u4E2D", failed: "\u5f02\u5e38", flagged: "\u5f85\u4fee\u6539" }[j.status] || j.status;
      return '<div class="admin-grading-card" data-jump-ag="' + j.id + '"><div class="agc-id">#' + j.id + '</div><div class="agc-main"><div class="agc-title">' + escHtml(j.title || ((j.question || '').length > 30 ? (j.question || '').substring(0, 30) + '\u2026' : j.question)) + '</div><div class="agc-meta"><span><b>' + escHtml(j.username) + '</b></span><span class="dot">·</span><span>' + (j.task_type === "task2" ? "大作文" : "小作文") + '</span><span class="dot">·</span><span class="hist-status ' + j.status + '">' + statusText + '</span><span class="dot">·</span><span>' + timeAgo(j.created_at) + '</span></div></div><div class="agc-score">' + (j.predicted_band == null ? "…" : j.predicted_band) + '</div><div class="agc-actions"><button class="delete-btn" data-del-ag="' + j.id + '" title="删除">✖</button></div></div>';
    }).join("");
    html += '</div>';
    var totalPages = Math.ceil((r.total || 0) / 20);
    if (totalPages > 1) {
      html += '<div style="display:flex;gap:8px;justify-content:center;margin-top:12px;align-items:center">';
      if (adminGradingPage > 1) html += '<button class="btn btn-sm btn-outline" id="ag-prev">\u4E0A\u4E00\u9875</button>';
      html += '<span class="muted">' + adminGradingPage + ' / ' + totalPages + '</span>';
      if (adminGradingPage < totalPages) html += '<button class="btn btn-sm btn-outline" id="ag-next">\u4E0B\u4E00\u9875</button>';
      html += '</div>';
    }
    byId("admin-grading-body").innerHTML = html;
    var prevBtn = byId("ag-prev"); if (prevBtn) prevBtn.onclick = function() { loadAdminGrading(adminGradingPage - 1); };
    var nextBtn = byId("ag-next"); if (nextBtn) nextBtn.onclick = function() { loadAdminGrading(adminGradingPage + 1); };
    byId("admin-grading-body").querySelectorAll("button[data-del-ag]").forEach(function(btn) { btn.onclick = function(e) { e.stopPropagation(); deleteAdminGrading(parseInt(btn.getAttribute("data-del-ag"))); }; });
    byId("admin-grading-body").querySelectorAll(".admin-grading-card").forEach(function(card) { card.onclick = function() { location.hash = "#report/" + card.getAttribute("data-jump-ag"); }; });
    var searchInput = byId("ag-search");
    if (searchInput) {
      // Bug #24: 300ms debounce
      var _searchTimer = null;
      searchInput.oninput = function() {
        clearTimeout(_searchTimer);
        _searchTimer = setTimeout(filterAdminTable, 300);
      };
    }
    var filterStatus = byId("ag-filter-status");
    if (filterStatus) filterStatus.onchange = function() { filterAdminTable(); };
  } catch (e) { byId("admin-grading-body").innerHTML = '<div class="center">\u52A0\u8F7D\u5931\u8D25</div>'; }
}
async function deleteAdminGrading(id) {
  // Bug #21
  if (!await confirmDialog("\u786E\u8BA4\u5220\u9664\u8FD9\u6761\u8BB0\u5F55\uFF1F")) return; try { await api("DELETE", "/admin/grading/" + id); toast("\u5DF2\u5220\u9664", "success"); loadAdminGrading(); } catch (e) { toast(e.message, "error"); } }

async function genInvites() { try { var count = parseInt(byId("invite-count").value) || 1; var r = await api("POST", "/admin/invite-codes", { count: count }); toast("\u5DF2\u751F\u6210 " + r.codes.length + " \u4E2A\u9080\u8BF7\u7801", "success"); loadInvites(); } catch (e) { toast(e.message, "error"); } }
async function loadInvites() {
  showLoading("invites-body");
  try { var r = await api("GET", "/admin/invite-codes");
    byId("invites-body").innerHTML = r.length ? r.map(function(c) {
      var status = c.used_by ? '<span style="color:var(--red)">\u5DF2\u4F7F\u7528</span>' : '<span style="color:var(--green)">\u53EF\u7528</span>';
      var delBtn = c.used_by ? '' : '<button class="delete-btn" data-del-inv="' + c.id + '">\u2716</button>';
      return '<div class="code-card"><code>' + escHtml(c.code) + '</code><div>' + status + (c.used_by ? ' \xB7 \u7528\u6237#' + c.used_by : '') + ' ' + delBtn + '</div></div>';
    }).join("") : '<div class="muted">\u6682\u65E0\u9080\u8BF7\u7801</div>';
    byId("invites-body").querySelectorAll("code").forEach(function(el) { el.onclick = function() { copyText(el.textContent); }; });
    byId("invites-body").querySelectorAll("button[data-del-inv]").forEach(function(btn) { btn.onclick = function() { deleteInvite(parseInt(btn.getAttribute("data-del-inv"))); }; });
  } catch (e) { byId("invites-body").innerHTML = '<div class="center">\u52A0\u8F7D\u5931\u8D25</div>'; }
}
async function deleteInvite(id) {
  // Bug #21
  if (!await confirmDialog("\u786E\u8BA4\u5220\u9664\uFF1F")) return; try { await api("DELETE", "/admin/invite-codes/" + id); toast("\u5DF2\u5220\u9664", "success"); loadInvites(); } catch (e) { toast(e.message, "error"); } }

async function genRedeems() { try { var count = parseInt(byId("redeem-count").value) || 1; var credits = parseInt(byId("redeem-credits").value) || 1; var r = await api("POST", "/admin/redeem-codes", { count: count, credits: credits }); toast("\u5DF2\u751F\u6210 " + r.codes.length + " \u4E2A\u5151\u6362\u7801", "success"); loadRedeems(); } catch (e) { toast(e.message, "error"); } }
async function loadRedeems() {
  showLoading("redeems-body");
  try { var r = await api("GET", "/admin/redeem-codes");
    byId("redeems-body").innerHTML = r.length ? r.map(function(c) {
      var status = c.used_by ? '<span style="color:var(--red)">\u5DF2\u4F7F\u7528</span>' : '<span style="color:var(--green)">\u53EF\u7528</span>';
      var delBtn = c.used_by ? '' : '<button class="delete-btn" data-del-red="' + c.id + '">\u2716</button>';
      return '<div class="code-card"><code>' + escHtml(c.code) + '</code><div>' + status + ' \xB7 ' + c.credits + '\u5E01' + (c.used_by ? ' \xB7 \u7528\u6237#' + c.used_by : '') + ' ' + delBtn + '</div></div>';
    }).join("") : '<div class="muted">\u6682\u65E0\u5151\u6362\u7801</div>';
    byId("redeems-body").querySelectorAll("code").forEach(function(el) { el.onclick = function() { copyText(el.textContent); }; });
    byId("redeems-body").querySelectorAll("button[data-del-red]").forEach(function(btn) { btn.onclick = function() { deleteRedeem(parseInt(btn.getAttribute("data-del-red"))); }; });
  } catch (e) { byId("redeems-body").innerHTML = '<div class="center">\u52A0\u8F7D\u5931\u8D25</div>'; }
}
async function deleteRedeem(id) {
  // Bug #21
  if (!await confirmDialog("\u786E\u8BA4\u5220\u9664\uFF1F")) return; try { await api("DELETE", "/admin/redeem-codes/" + id); toast("\u5DF2\u5220\u9664", "success"); loadRedeems(); } catch (e) { toast(e.message, "error"); } }

async function loadSettings() {
  try {
    var s = await api("GET", "/admin/settings");
    byId("settings-body").innerHTML = 
      '<div class="setting-row"><label class="setting-label">LLM 超时（秒）</label><input class="input" type="number" id="set-timeout" value="' + s.LLM_TIMEOUT + '" min="30" max="600"/></div>' +
      '<div class="setting-row"><label class="setting-label">最大 Token</label><input class="input" type="number" id="set-tokens" value="' + s.LLM_MAX_TOKENS + '" min="1000" max="32000"/></div>' +
      '<div class="setting-row"><label class="setting-label">失败重试次数</label><input class="input" type="number" id="set-retries" value="' + s.LLM_MAX_RETRIES + '" min="1" max="10"/></div>' + '<div class="setting-row"><label class="setting-label">并发设置</label><input class="input" type="number" id="set-concurrency" value="' + s.GRADER_CONCURRENCY + '" min="1" max="32"/></div>' +
      '<button class="btn btn-primary" style="margin-top:12px" onclick="saveSettings()">保存设置</button>';
  } catch (e) { byId("settings-body").innerHTML = '<div class="center"><p style="color:#dc2626">加载失败：' + (e.message || '未知错误') + '</p><p style="color:#64748b;font-size:13px;margin-top:8px">请检查后端是否已重新构建并包含 SettingsUpdate 端点</p><button class="btn btn-primary btn-sm" style="margin-top:8px" onclick="loadSettings()">重试</button></div>'; }
}

async function saveSettings() {
  try {
    var data = {
      LLM_TIMEOUT: parseInt(byId("set-timeout").value),
      LLM_MAX_TOKENS: parseInt(byId("set-tokens").value),
      LLM_MAX_RETRIES: parseInt(byId("set-retries").value),
      GRADER_CONCURRENCY: parseInt(byId("set-concurrency").value),
    };
    var r = await api("PUT", "/admin/settings", data);
    toast("设置已保存", "success");
  } catch (e) { toast(e.message, "error"); }
}
async function generateSampleEssay(jobId) {
  var btn = byId("sample-essay-btn-" + jobId);
  if (btn) { btn.disabled = true; btn.textContent = "⏳ 正在生成..."; }
  try {
    var r = await api("POST", "/grading/" + jobId + "/sample-essay", {}, true);
    if (r.skipped) {
      toast(r.reason || "该分数不需要生成范文", "info");
      return;
    }
    showSampleEssayModal(r.essay, r.improvements || [], r.target_band || '');
  } catch (e) {
    toast("生成失败: " + e.message, "error");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "✨ 生成个性化范文"; }
  }
}

function closeSampleEssayModal() {
  var modals = document.querySelectorAll(".sample-essay-overlay");
  for (var i = 0; i < modals.length; i++) modals[i].remove();
}

function copySampleEssay() {
  var modal = document.querySelector(".sample-essay-overlay");
  var text = modal ? modal.querySelector("div[style*=font-family]").textContent : "";
  copyText(text);
  if (event && event.target) event.target.textContent = "✓ 已复制";
}

function showSampleEssayModal(essay, improvements, targetBand) {
  closeSampleEssayModal();
  var overlay = document.createElement("div");
  overlay.className = "sample-essay-overlay";
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px";
  var box = document.createElement("div");
  box.style.cssText = "background:#fff;border-radius:12px;max-width:800px;max-height:90vh;overflow:auto;padding:24px;box-shadow:0 20px 60px rgba(0,0,0,0.3)";
  var imp_html = "";
  if (improvements && improvements.length > 0) {
    imp_html = '<div style="background:#f0f9ff;border-left:3px solid #3b82f6;padding:12px;margin-bottom:16px;border-radius:6px"><b style="color:#1e40af">主要改进点:</b><ul style="margin:8px 0 0 20px;padding:0;color:#1e40af">';
    for (var i = 0; i < improvements.length; i++) imp_html += '<li style="margin:4px 0">' + escHtml(improvements[i]) + '</li>';
    imp_html += '</ul></div>';
  }
  box.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px"><h3 style="margin:0;color:var(--primary)">✨ 个性化范文 (Band ' + (targetBand || '7-8') + ')</h3>' + '<button class="btn btn-sm" onclick="closeSampleEssayModal()" style="background:#ef4444;color:#fff;border:none">✕</button></div>' + imp_html + '<div style="background:#f8fafc;padding:16px;border-radius:8px;line-height:1.8;white-space:pre-wrap;font-family:Georgia,serif">' + escHtml(essay) + '</div><div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end"><button class="btn btn-primary" onclick="copySampleEssay()">📋 复制</button><button class="btn" onclick="closeSampleEssayModal()" style="background:#ef4444;color:#fff;border:none">关闭</button></div>';
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
}

// 启动
initGrading();
router();

async function cancelJob(jobId, btn) {
  if (!await confirmDialog("确定取消这个评分任务? 已扣积分会退还。")) return;
  if (btn) { btn.disabled = true; btn.textContent = "取消中..."; }
  try {
    var r = await api("POST", "/grading/" + jobId + "/cancel");
    toast("已取消, 退还 " + (r.refunded || 0) + " 满分币", "success");
    location.reload();
  } catch (e) { toast(e.message, "error"); if (btn) { btn.disabled = false; btn.textContent = "⛔ 取消评分"; } }
}


async function renameTitle(jobId, currentTitle) {
  var next = await promptDialog("给这次评分起个标题", currentTitle || "");
  if (next == null || !next.trim()) return;
  try {
    var r = await api("PATCH", "/grading/" + jobId + "/title", { title: next.trim() });
    toast("标题已更新", "success");
    setTimeout(function() { location.reload(); }, 600);
  } catch (e) { toast(e.message, "error"); }
}

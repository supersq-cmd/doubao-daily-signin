"""豆包每日签到 —— 在 computer_use_tool(plane="bu") 单元格中直接执行的完整代码。

用法：把本文件全文作为 computer_use_tool 的 code 参数运行（plane="bu"）。
它会在已登录的豆包页面上下文里调用活动接口，打印一行 JSON 结果：
  {"status":"checked-in|already|no-activity|auth-required|failed", ...}

设计要点：
- 用页面内 fetch（credentials: include），登录态由浏览器自动携带，不导出、不读取任何 cookie。
- bu.js 只支持同步返回，因此 fetch 结果先写入 window 变量，再轮询读取。
- version_code 由本机豆包客户端版本实时派生，失败时依次回退候选值。
"""

import json
import time
import ctypes
import ctypes.wintypes as wt
import glob
import os

import aha_browser_use as bu

DETAIL = "https://www.doubao.com/alice/ug/campaign/v3/detail/"
CHECKIN = "https://www.doubao.com/alice/ug/campaign/landing/checkin"
GROUP = "pc_incentive_task_mvp_v3"
LOGIN_CODE = 710012001
SYSTEM_ERR = 710010702


def client_info():
    """返回 (版本串, version_code)，读不到则 (None, None)。"""
    exe = None
    for p in glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Doubao", "Application", "Doubao.exe")):
        exe = p
    if not exe:
        return None, None
    size = ctypes.windll.version.GetFileVersionInfoSizeW(exe, None)
    if not size:
        return None, None
    buf = ctypes.create_string_buffer(size)
    if not ctypes.windll.version.GetFileVersionInfoW(exe, 0, size, buf):
        return None, None
    rptr = ctypes.c_void_p()
    ln = wt.UINT()
    if not ctypes.windll.version.VerQueryValueW(buf, "\\", ctypes.byref(rptr), ctypes.byref(ln)):
        return None, None

    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [
            ("dwSignature", wt.DWORD), ("dwStrucVersion", wt.DWORD),
            ("dwFileVersionMS", wt.DWORD), ("dwFileVersionLS", wt.DWORD),
            ("dwProductVersionMS", wt.DWORD), ("dwProductVersionLS", wt.DWORD),
            ("dwFileFlagsMask", wt.DWORD), ("dwFileFlags", wt.DWORD),
            ("dwFileOS", wt.DWORD), ("dwFileType", wt.DWORD),
            ("dwFileSubtype", wt.DWORD), ("dwFileDateMS", wt.DWORD), ("dwFileDateLS", wt.DWORD),
        ]

    fi = ctypes.cast(rptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
    major = fi.dwFileVersionMS >> 16
    minor = fi.dwFileVersionMS & 0xFFFF
    patch = fi.dwFileVersionLS >> 16
    return "%d.%d.%d" % (major, minor, patch), major * 10000 + minor * 100 + patch


def js_fetch(url_key, slot, body, ver, ver_code):
    """发起一个页面内 POST，结果写入 window[slot]；返回 'ok'。"""
    script = """
window.%(slot)s = 'pending';
(function(){
  var q = new URLSearchParams({
    version_code: '%(vc)s', language: 'zh', device_platform: 'web',
    doubao_device_platform: 'web', aid: '497858', real_aid: '497858',
    pkg_type: 'release_version', pc_version: '%(ver)s', doubao_pc_version: '5.72.66',
    samantha_web: '1', web_platform: 'desktop', 'use-olympus-account': '1',
    web_tab_id: '0', device_id: '', region: '', sys_region: ''
  });
  fetch('%(url)s?' + q.toString(), {
    method: 'POST', credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(%(body)s)
  }).then(function(r){ return r.text().then(function(t){ window.%(slot)s = r.status + '|' + t; }); })
    .catch(function(e){ window.%(slot)s = 'ERR ' + e; });
})();
'ok'
""" % {"slot": slot, "vc": ver_code, "ver": ver, "url": url_key, "body": body}
    return bu.js(script)


def wait_json(slot, timeout=25):
    for _ in range(timeout):
        time.sleep(1)
        v = bu.js("window.%s" % slot)
        if v and v != "pending":
            if v.startswith("ERR"):
                return None, v
            status, _, text = v.partition("|")
            try:
                return json.loads(text), status
            except Exception:
                return None, v[:200]
    return None, "timeout"


def pick_task(detail):
    tasks = (detail.get("data") or {}).get("tasks") or []
    for t in tasks:
        if t and t.get("task_kind") == "daily_signin":
            return t
    return None


def main():
    info = bu.page_info()
    if "doubao.com" not in (info.get("url") or ""):
        bu.navigate("https://www.doubao.com/chat/")
        bu.wait_for_load(timeout=15)

    ver, ver_code = client_info()
    candidates = [str(ver_code)] if ver_code else []
    for c in ("23610", "20800"):
        if c not in candidates:
            candidates.append(c)

    detail, used_ver, used_code = None, None, None
    for code in candidates:
        ok = js_fetch(DETAIL, "__sign_detail", "{campaign_group_code: '%s'}" % GROUP, ver or "2.36.10", code)
        d, st = wait_json("__sign_detail")
        if d is None:
            continue
        body_code = int(d.get("code") or 0)
        if body_code == LOGIN_CODE:
            print(json.dumps({"status": "auth-required", "message": "豆包未登录或登录态失效"}, ensure_ascii=False))
            return
        if body_code == 0:
            detail, used_ver, used_code = d, (ver or "2.36.10"), code
            break
        if body_code == SYSTEM_ERR:
            continue
    if detail is None:
        print(json.dumps({"status": "failed", "message": "detail 接口不可用（可能 version_code 已过期或接口变更）"}, ensure_ascii=False))
        return

    task = pick_task(detail)
    if not task:
        print(json.dumps({"status": "no-activity", "message": "当前账号无签到任务（活动未开放或企业/飞书账号不支持）"}, ensure_ascii=False))
        return

    c = task.get("daily_checkin") or {}
    total = ((detail.get("data") or {}).get("progress") or {}).get("total_amount")
    if c.get("checked_in_today") is True:
        print(json.dumps({
            "status": "already",
            "message": "今天已签到",
            "continuous_days": c.get("continuous_days"),
            "reward_amount": (c.get("reward") or {}).get("reward_amount"),
            "total_amount": total,
        }, ensure_ascii=False))
        return

    js_fetch(CHECKIN, "__sign_claim", "{scene: '%s'}" % GROUP, used_ver, used_code)
    r, st = wait_json("__sign_claim")
    if r is None:
        print(json.dumps({"status": "failed", "message": "签到请求失败：%s" % st}, ensure_ascii=False))
        return
    code = int(r.get("code") or 0)
    if code == LOGIN_CODE:
        print(json.dumps({"status": "auth-required", "message": "登录态失效，需重新登录"}, ensure_ascii=False))
        return
    if code != 0:
        print(json.dumps({"status": "failed", "message": "%s (code %s)" % (r.get("msg") or "", code)}, ensure_ascii=False))
        return
    d = r.get("data") or {}
    if d.get("idempotent") is True:
        print(json.dumps({"status": "already", "message": "今天已签到（服务端幂等）", "continuous_days": d.get("continuous_days"),
                          "reward_amount": d.get("reward_amount")}, ensure_ascii=False))
        return
    print(json.dumps({
        "status": "checked-in",
        "message": "签到成功",
        "reward_amount": d.get("reward_amount"),
        "continuous_days": d.get("continuous_days"),
        "checkin_date": d.get("checkin_date"),
        "total_amount": total,
    }, ensure_ascii=False))


main()

"""签到时间设置：读取 / 修改 config.json 中的每日签到时间，并输出对应的 cron 表达式。

用法（普通 shell 即可，不需要 bu 平面）：
    python scripts/schedule.py --show            # 查看当前设置
    python scripts/schedule.py --set 07:40       # 改成每天 07:40
    python scripts/schedule.py --job 123         # 记下已创建的定时任务 id
总是打印一行 JSON：{"ok":true,"signin_time":"07:40","cron":"40 7 * * *",...}
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "config.json")
DEFAULT = {"signin_time": "07:20", "timezone": "Asia/Shanghai", "cron_job_id": None}
PEAK = [(450, 600), (930, 1020), (1170, 1200)]  # 7:30-10:00 / 15:30-17:00 / 19:30-20:00


def load():
    cfg = dict(DEFAULT)
    try:
        with open(CFG, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if v is not None or k == "cron_job_id"})
    except Exception:
        pass
    return cfg


def normalize(text):
    """接受 07:40 / 7：40 / 7:40 / 740 等写法，非法返回 None。"""
    t = str(text).strip().replace("：", ":")
    if ":" in t:
        parts = t.split(":")
        if len(parts) != 2:
            return None
        hh, mm = parts
    elif t.isdigit() and len(t) in (3, 4):
        hh, mm = t[:-2], t[-2:]
    else:
        return None
    try:
        h, m = int(hh), int(mm)
    except Exception:
        return None
    if not (0 <= h < 24 and 0 <= m < 60):
        return None
    return "%02d:%02d" % (h, m)


def cron_of(hhmm):
    h, m = hhmm.split(":")
    return "%d %d * * *" % (int(m), int(h))


def is_peak(hhmm):
    h, m = hhmm.split(":")
    mins = int(h) * 60 + int(m)
    return any(a <= mins <= b for a, b in PEAK)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="只查看当前设置")
    ap.add_argument("--set", dest="set_time", metavar="HH:MM", help="把每日签到时间改成 HH:MM")
    ap.add_argument("--job", type=int, help="记录定时任务 id")
    ap.add_argument("--tz", help="记录时区，默认 Asia/Shanghai")
    args = ap.parse_args()

    cfg = load()
    if args.set_time:
        t = normalize(args.set_time)
        if not t:
            print(json.dumps({"ok": False, "error": "时间格式无法识别，请用 HH:MM，例如 07:40"}, ensure_ascii=False))
            sys.exit(1)
        cfg["signin_time"] = t
    if args.tz:
        cfg["timezone"] = args.tz
    if args.job:
        cfg["cron_job_id"] = args.job

    if args.set_time or args.job or args.tz:
        with open(CFG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "ok": True,
        "signin_time": cfg["signin_time"],
        "timezone": cfg["timezone"],
        "schedule_type": "cron",
        "cron": cron_of(cfg["signin_time"]),
        "cron_job_id": cfg["cron_job_id"],
        "peak_warning": is_peak(cfg["signin_time"]),
    }, ensure_ascii=False))


main()

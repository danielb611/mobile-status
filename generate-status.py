#!/usr/bin/env python3
"""Generate status.json for the mobile status page.

Reads real state only (launchd job status, log file tails/mtimes) — never
fabricates a status. Anything it can't verify is marked unknown rather than
guessed. Deliberately excludes revenue/financial figures and API details;
this repo is public.
"""
import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=1))  # Europe/Dublin (no DST handling, good enough for a status page)


def now_iso():
    return datetime.now(IST).isoformat()


def launchd_job(label):
    """Returns (running: bool, pid: int|None) for a launchd job label."""
    try:
        out = subprocess.run(["launchctl", "list", label], capture_output=True, text=True, timeout=5)
    except Exception:
        return False, None
    if out.returncode != 0:
        return False, None
    m = re.search(r'"PID"\s*=\s*(\d+)', out.stdout)
    return True, (int(m.group(1)) if m else None)


def tail(path, n=1):
    p = Path(path)
    if not p.exists():
        return []
    try:
        lines = p.read_text(errors="replace").splitlines()
        return lines[-n:]
    except Exception:
        return []


def mtime_iso(path):
    p = Path(path)
    if not p.exists():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime, tz=IST).isoformat()


def next_weekday(hour, minute, weekday):
    """Next occurrence of weekday (0=Mon) at hour:minute, IST, from now."""
    n = datetime.now(IST)
    days_ahead = (weekday - n.weekday()) % 7
    candidate = (n + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= n:
        candidate += timedelta(days=7)
    return candidate.isoformat()


# ---------------------------------------------------------------------------
# Trading (forex paper loop)
# ---------------------------------------------------------------------------
trading_log = "/Users/daniel/Setup-Runner/Trading/agent/logs/live_loop.log"
running, pid = launchd_job("com.danielbaker.forex-live-loop")
last_lines = tail(trading_log, 30)
last_scan = None
last_error = None
for line in reversed(last_lines):
    if last_scan is None and "INFO scan:" in line:
        last_scan = line.split(" INFO scan: ", 1)
        last_scan = {"timestamp": last_scan[0], "detail": last_scan[1]} if len(last_scan) == 2 else None
    if last_error is None and (" ERROR " in line):
        last_error = line
    if last_scan and last_error:
        break

trading = {
    "label": "AI Trading (forex paper validation)",
    "launchd_running": running,
    "pid": pid,
    "last_scan": last_scan,
    "last_error_line": last_error,
    "log_mtime": mtime_iso(trading_log),
}

# ---------------------------------------------------------------------------
# Etsy auto-generation (weekly, Monday 9am Europe/Dublin)
# ---------------------------------------------------------------------------
etsy_log = "/Users/daniel/Setup-Runner/Etsy/pipeline/launchd.out.log"
etsy_err_log = "/Users/daniel/Setup-Runner/Etsy/pipeline/launchd.err.log"
running_e, pid_e = launchd_job("com.inkandrise.etsy.scheduler")
last_etsy_lines = tail(etsy_log, 5)
last_run_complete = None
for line in reversed(last_etsy_lines):
    if "Weekly run complete" in line:
        last_run_complete = line
        break
err_tail = tail(etsy_err_log, 3)

etsy = {
    "label": "Etsy auto-generation (weekly, Mon 09:00 Dublin)",
    "launchd_running": running_e,
    "pid": pid_e,
    "last_run_complete_line": last_run_complete,
    "log_mtime": mtime_iso(etsy_log),
    "recent_errors": [l for l in err_tail if l.strip()],
    "next_scheduled": next_weekday(9, 0, 0),  # Monday
}

# ---------------------------------------------------------------------------
# Upload reminders (static schedule, tracked in Money Brain / portfolio-status.md)
# ---------------------------------------------------------------------------
reminders = [
    {"method": "Etsy", "cadence": "Tue / Thu / Sun", "note": "Upload reminder surfaced in Money Brain"},
    {"method": "SiteSmith", "cadence": "Monday 10:00", "note": "LeadLu CSV export reminder in Money Brain"},
]

# ---------------------------------------------------------------------------
# Weekly timetable — mirrors Money Brain's Week Planner exactly: same
# accounts, times, platform/brand colours and day grouping, sourced from
# src/lib/postSchedules.js + youtubeChannels.js + scheduleUtils.js +
# palette.js (colorForMethodId/FIXED_ORDER/CATEGORICAL) as of 2026-08-23.
# This is a static hand-mirrored snapshot, not read live from Money Brain's
# source — if the schedule changes there, this needs a manual re-sync.
# ---------------------------------------------------------------------------
TIMETABLE = {
    "Monday": [
        {"time": "10:00 am", "platform": "SiteSmith", "account": "SiteSmith", "detail": "Export fresh leads from LeadLu", "colour": "#26c6da"},
    ],
    "Tuesday": [
        {"time": "8:00 to 9:00 am", "platform": "YouTube Video", "account": "The Inward Architect", "detail": None, "colour": "#1fbf8f"},
        {"time": "10:30 am", "platform": "Newsletter", "account": "Hardwired Weekly", "detail": None, "colour": "#9b7ef0"},
        {"time": "11:00 am", "platform": "Pinterest", "account": "Inkandrise", "detail": None, "colour": "#e8558f"},
        {"time": "11:00 am", "platform": "Pinterest", "account": "Hardwired Weekly", "detail": None, "colour": "#3987e5"},
        {"time": "12:00 pm", "platform": "YouTube Short", "account": "Hardwired For More", "detail": None, "colour": "#3987e5"},
        {"time": "8:00 pm", "platform": "Etsy", "account": "Inkandrise", "detail": "New Nursery listing", "colour": "#e75454"},
    ],
    "Wednesday": [
        {"time": "3:00 pm", "platform": "YouTube Video", "account": "Built From Within Motivation", "detail": None, "colour": "#9b7ef0"},
    ],
    "Thursday": [
        {"time": "8:00 am", "platform": "YouTube Short", "account": "Built From Within Motivation", "detail": None, "colour": "#9b7ef0"},
        {"time": "12:00 pm", "platform": "Pinterest", "account": "Hardwired Weekly", "detail": None, "colour": "#3987e5"},
        {"time": "8:00 pm", "platform": "Etsy", "account": "Inkandrise", "detail": "New Feminine line art listing", "colour": "#e75454"},
    ],
    "Friday": [
        {"time": "12:00 pm", "platform": "YouTube Short", "account": "Daniel Bakekolo", "detail": None, "colour": "#e0b400"},
    ],
    "Saturday": [
        {"time": "8:00 pm", "platform": "Pinterest", "account": "Inkandrise", "detail": None, "colour": "#e8558f"},
    ],
    "Sunday": [
        {"time": "7:00 pm", "platform": "Etsy", "account": "Inkandrise", "detail": "New Motivational typography listing", "colour": "#e75454"},
        {"time": "7:00 to 8:00 pm", "platform": "YouTube Video", "account": "Daniel Bakekolo", "detail": None, "colour": "#e0b400"},
        {"time": "8:00 pm", "platform": "Pinterest", "account": "Inkandrise", "detail": None, "colour": "#e8558f"},
        {"time": "8:00 pm", "platform": "Pinterest", "account": "Hardwired Weekly", "detail": None, "colour": "#3987e5"},
    ],
}

status = {
    "generated_at": now_iso(),
    "trading": trading,
    "etsy": etsy,
    "reminders": reminders,
    "timetable": TIMETABLE,
}

out_path = Path(__file__).resolve().parent / "status.json"
out_path.write_text(json.dumps(status, indent=2))
print(f"Wrote {out_path}")

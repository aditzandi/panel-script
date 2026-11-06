#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FarmBuddies Auto Claim
Mode kerja: TASK dulu sampai tuntas -> baru FARM.

Endpoint map:
  AUTH    : POST /auth/telegram
  STATE   : GET  /user/bootstrap  |  GET /user/force-join
  STREAK  : POST /user/streak/claim
  ADS     : POST /ads/task/{id}/session | /complete | /reward
  HARVEST : POST /ads/harvest/session + /ads/harvest/complete
  WATER   : POST /ads/farm/session   + /ads/farm/complete
  FARM    : POST /farm/plant | POST /farm/water
  LINK    : POST /tasks/{id}/start | /tasks/{id}/claim
  SHORT   : GET  /shortlinks | POST /shortlinks/{pid}/issue | /claim
"""

import time
import json
import os
import sys
import re
import base64
import urllib.parse
import requests
from datetime import datetime

# ═══════════════ KONSTANTA ═══════════════
CONFIG_FILE = "config.json"
CURRENT_TOKEN = None
CONFIG = {}
BASE_URL = ""
FARM_FP = ""
DEVICE_ID = ""
INIT_DATA = ""

W = 58                      # lebar isi kotak
TASK_RECHECK_SEC = 120      # jeda cek ulang task saat task kosong

# ═══════════════ WARNA ═══════════════
RST = "\033[0m"
BOLD = "\033[1m"


def fg(c):
    return f"\033[38;5;{c}m"


C_TITLE_A = 48     # hijau mint
C_TITLE_B = 39     # biru langit
C_FRAME = 37       # teal
C_LABEL = 109
C_TEXT = 255
C_MUTED = 244
C_OK = 82
C_WARN = 214
C_ERR = 203
C_GOLD = 221
C_WATER = 81


def strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*m', '', s)


def ansi_len(s):
    w = 0
    for ch in strip_ansi(s):
        cp = ord(ch)
        if (0x1F300 <= cp <= 0x1F9FF) or (0x2600 <= cp <= 0x27BF) or (0x2B00 <= cp <= 0x2BFF):
            w += 2
        else:
            w += 1
    return w


def pad(s, n):
    p = n - ansi_len(s)
    return s + (" " * p if p > 0 else "")


def gradient(text, start=C_TITLE_A, end=C_TITLE_B):
    if len(text) <= 1:
        return fg(start) + text + RST
    out, n = "", len(text)
    for i, ch in enumerate(text):
        c = int(round(start + (end - start) * i / max(1, n - 1)))
        out += fg(c) + ch
    return out + RST


# ═══════════════ GLOBAL STATE ═══════════════
_state = {
    "user": "-", "status": "boot", "aksi": "init",
    "start": time.time(),
    "ads_used": 0, "ads_max": 200,
    "coins": 0, "usdt": 0.0, "ads_done": 0, "today_earned": 0,
    "level": 1, "xp": 0, "xp_max": 3200,
    "water": 0, "water_max": 10, "farm_level": 1,
    "plots": [], "tasks": [], "crops": [],
    "streak_day": 0, "streak_claimed": False,
    "claimed_ids": set(),
    "session_gained": 0,
    "tasks_resume_at": 0,
    "logs": [],
}


def now_str():
    return datetime.now().strftime("%H:%M:%S")


def push_log(msg, tag="i"):
    icons = {
        "i": fg(C_TITLE_B) + "•" + RST,
        "ok": fg(C_OK) + "✓" + RST,
        "er": fg(C_ERR) + "✗" + RST,
        "wr": fg(C_WARN) + "!" + RST,
        "in": fg(C_LABEL) + "›" + RST,
        "g": fg(C_GOLD) + "★" + RST,
        "f": fg(C_OK) + "▲" + RST,
        "s": fg(C_OK) + "🌱" + RST,
        "w": fg(C_WATER) + "💧" + RST,
    }
    line = f"{fg(C_MUTED)}{now_str()}{RST} {icons.get(tag, '•')} {fg(C_TEXT)}{msg}{RST}"
    _state["logs"].append(line)
    if len(_state["logs"]) > 6:
        _state["logs"].pop(0)


def fmt_uptime(s):
    s = int(s)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


# ═══════════════ BOX HELPERS (rounded) ═══════════════
F = fg(C_FRAME)


def top():
    return F + "╭" + "─" * (W + 2) + "╮" + RST + "\n"


def bot():
    return F + "╰" + "─" * (W + 2) + "╯" + RST + "\n"


def sep():
    return F + "├" + "─" * (W + 2) + "┤" + RST + "\n"


def row(content=""):
    return F + "│ " + RST + pad(content, W) + " " + F + "│" + RST + "\n"


def section(title, color=C_TITLE_A):
    label = f" {title} "
    fill = W - ansi_len(label) - 2
    return F + "│ " + RST + fg(C_FRAME) + "──" + RST + fg(color) + BOLD + label + RST + \
        fg(C_FRAME) + "─" * max(0, fill) + RST + " " + F + "│" + RST + "\n"


def kv(label, value, vcolor=C_TEXT):
    return row(f"{fg(C_LABEL)}{label:<10}{RST}{fg(vcolor)}{value}{RST}")


def bar(pct, length=10):
    filled = int(length * pct / 100)
    return fg(C_OK) + "▰" * filled + fg(C_MUTED) + "▱" * (length - filled) + RST


# ═══════════════ DASHBOARD ═══════════════
def render_dashboard():
    sys.stdout.write("\033[2J\033[H")
    out = [top()]
    out.append(row(gradient("🌾 FARM BUDDIES AUTO")))
    status = _state["status"].upper()
    scolor = {"TASKS": C_GOLD, "FARMING": C_OK, "IDLE": C_WARN}.get(status, C_TITLE_B)
    out.append(row(f"{fg(scolor)}{BOLD}● {status}{RST}  {fg(C_MUTED)}{_state['aksi']}{RST}"))
    out.append(sep())

    out.append(kv("User", _state["user"], C_GOLD))
    out.append(kv("Uptime", fmt_uptime(time.time() - _state["start"])))
    out.append(kv("Kuota Ads", f"{_state['ads_used']}/{_state['ads_max']}"))
    out.append(sep())

    # TUGAS
    out.append(section("TUGAS", C_GOLD))
    shown = 0
    for t in _state["tasks"]:
        if shown >= 6:
            break
        tid = t.get("id", "?")
        title = str(t.get("title", "Task"))[:12]
        target = t.get("target", 10) or 1
        prog = t.get("progress", 0)
        rew = t.get("reward", 0)
        pct = int((prog / max(1, target)) * 100)
        if t.get("state") == "done":
            st = fg(C_MUTED) + "selesai" + RST
            pct = 100
        elif t.get("adsgramTask"):
            st = fg(C_TITLE_B) + f"ADG +{rew}" + RST
        else:
            st = fg(C_GOLD) + f"{prog}/{target} +{rew}" + RST
        out.append(row(f"{fg(C_TEXT)}#{tid:<3}{title:<12}{RST} {bar(min(pct, 100))} {st}"))
        shown += 1
    if shown == 0:
        out.append(row(f"{fg(C_MUTED)}belum ada data task{RST}"))
    out.append(sep())

    # LAHAN
    out.append(section("LAHAN", C_OK))
    plots = _state["plots"]
    if plots:
        for p in plots:
            idx = p.get("idx", 0)
            name = (p.get("name") or "-")[:12]
            state = (p.get("state") or "empty").lower()
            payout = p.get("payout", 0)
            if state == "ready":
                st = fg(C_OK) + "SIAP PANEN" + RST
            elif state == "growing":
                st = fg(C_GOLD) + "TUMBUH" + RST
            else:
                st = fg(C_MUTED) + "KOSONG" + RST
            pay = f"{fg(C_OK)}+{payout}{RST}" if payout else f"{fg(C_MUTED)}-{RST}"
            out.append(row(f"{fg(C_TEXT)}[{idx}]{RST} {name:<13}{pad(st, 12)} {pay}"))
    else:
        out.append(row(f"{fg(C_MUTED)}belum ada data lahan{RST}"))
    ready = sum(1 for p in plots if p.get("state") == "ready")
    growing = sum(1 for p in plots if p.get("state") == "growing")
    empty = sum(1 for p in plots if p.get("state") == "empty")
    out.append(row(f"{fg(C_MUTED)}siap {ready} · tumbuh {growing} · kosong {empty}{RST}"))
    out.append(sep())

    # STATUS AKUN
    out.append(section("AKUN", C_TITLE_B))
    out.append(kv("Koin", f"{_state['coins']:,}", C_GOLD))
    out.append(kv("Sesi", f"+{_state['session_gained']}", C_OK))
    out.append(kv("Hari ini", f"{_state['today_earned']}", C_OK))
    out.append(kv("Ads", f"{_state['ads_done']} selesai"))
    out.append(kv("USDT", f"{_state['usdt']:.5f}", C_OK))
    out.append(kv("Level", f"{_state['level']}  (XP {_state['xp']}/{_state['xp_max']})"))
    out.append(kv("Air", f"{_state['water']}/{_state['water_max']}", C_WATER))
    out.append(sep())

    # LOG
    out.append(section("AKTIVITAS", C_LABEL))
    logs = _state["logs"]
    for i in range(6):
        out.append(row(logs[i] if i < len(logs) else ""))
    out.append(bot())

    sys.stdout.write("".join(out))
    sys.stdout.flush()


# ═══════════════ CONFIG ═══════════════
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def isi_data():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(top())
    sys.stdout.write(row(gradient("SETUP AKUN")))
    sys.stdout.write(row(fg(C_MUTED) + "Salin dari devtools Telegram WebApp" + RST))
    sys.stdout.write(bot())
    print()
    init_data = input(f"{fg(C_LABEL)}› init_data/query_id :{RST} ").strip()
    device_id = input(f"{fg(C_LABEL)}› deviceId (dev_…)   :{RST} ").strip()
    fingerprint = input(f"{fg(C_LABEL)}› x-farm-fp          :{RST} ").strip()

    save_config({
        "init_data": init_data,
        "device_id": device_id,
        "fingerprint": fingerprint,
        "base_url": "https://farm-buddies-api.nhathaybip2000.workers.dev/api",
    })
    print(f"\n{fg(C_OK)}✓ Config disimpan ke {CONFIG_FILE}{RST}")
    time.sleep(1.6)


# ═══════════════ HTTP ═══════════════
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)",
    "Accept": "*/*",
    "Origin": "https://farm-buddies-4g5.pages.dev",
    "Referer": "https://farm-buddies-4g5.pages.dev/",
    "x-requested-with": "org.telegram.messenger.web",
})


def get_headers():
    return {
        "Content-Type": "application/json",
        "authorization": f"Bearer {CURRENT_TOKEN}",
        "x-farm-fp": FARM_FP,
    }


def parse_initdata(init_data_str):
    if not init_data_str:
        return None
    parts = urllib.parse.parse_qsl(init_data_str, keep_blank_values=True)
    fields = dict(parts)
    try:
        if "user" in fields:
            fields["user"] = json.loads(fields["user"])
    except Exception:
        pass
    dc_pairs = sorted([(k, v) for k, v in parts if k != "hash"], key=lambda x: x[0])
    dc_str = "\n".join(f"{k}={v}" for k, v in dc_pairs)
    return {
        "fields": fields,
        "data_check_string": dc_str,
        "signature": fields.get("signature", ""),
        "hash": fields.get("hash", ""),
        "auth_date": fields.get("auth_date", ""),
        "query_id": fields.get("query_id", ""),
        "user_id": str((fields.get("user") or {}).get("id", "")),
    }


def authenticate():
    global CURRENT_TOKEN
    try:
        _state["aksi"] = "login"
        render_dashboard()
        res = requests.post(
            f"{BASE_URL}/auth/telegram",
            headers={"Content-Type": "application/json"},
            json={"initData": INIT_DATA, "deviceId": DEVICE_ID, "fingerprint": FARM_FP},
            timeout=15,
        )
        if res.status_code == 200:
            data = res.json()
            if data.get("ok"):
                CURRENT_TOKEN = data.get("token")
                push_log("token didapat", "ok")
                return True
        push_log(f"login gagal (HTTP {res.status_code})", "er")
    except Exception as e:
        push_log(f"login error: {str(e)[:40]}", "er")
    return False


def make_request(method, endpoint, json_payload=None):
    global CURRENT_TOKEN
    if not CURRENT_TOKEN and not authenticate():
        return None
    url = f"{BASE_URL}{endpoint}"
    for attempt in range(3):
        try:
            if method.lower() == "get":
                res = session.get(url, headers=get_headers(), timeout=15)
            else:
                payload = json_payload if json_payload is not None else {}
                res = session.post(url, headers=get_headers(), json=payload, timeout=15)

            if res.status_code == 401:
                push_log("token kadaluarsa, login ulang", "wr")
                if authenticate():
                    continue
                return None

            if res.status_code >= 500 and attempt < 2:
                time.sleep(2 * (2 ** attempt))
                continue
            return res
        except Exception as e:
            push_log(f"req err {endpoint}: {str(e)[:40]}", "er")
            if attempt < 2:
                time.sleep(2 * (2 ** attempt))
            else:
                return None
    return None


# ═══════════════ FETCH STATE ═══════════════
def fetch_state():
    res = make_request("get", "/user/bootstrap")
    if res and res.status_code == 200:
        try:
            data = res.json()
        except Exception:
            return None
        if data.get("ok"):
            profile = data.get("profile", {})
            farm = data.get("farm", {})
            streak = data.get("streak", {})
            ads = data.get("ads", {})
            cap = ads.get("cap", {})

            _state["user"] = profile.get("username", "Unknown")
            _state["coins"] = int(profile.get("coins", 0))
            _state["usdt"] = float(profile.get("usdt", 0))
            _state["level"] = profile.get("level", 1)
            _state["xp"] = profile.get("xp", 0)
            _state["xp_max"] = profile.get("xpMax", 3200)
            _state["ads_done"] = profile.get("totalAds", 0)
            _state["today_earned"] = profile.get("todayEarned", 0)
            _state["farm_level"] = profile.get("farmLevel", 1)
            _state["water"] = farm.get("water", 0)
            _state["water_max"] = farm.get("waterMax", 10)
            _state["plots"] = farm.get("plots", [])
            _state["crops"] = farm.get("crops", [])
            _state["tasks"] = data.get("tasks", [])
            _state["ads_used"] = cap.get("used", 0)
            _state["ads_max"] = cap.get("max", 200)
            _state["streak_day"] = streak.get("day", 0)
            _state["streak_claimed"] = streak.get("claimedToday", False)
            return _state
    return None


# ═══════════════ HELPERS ═══════════════
def get_best_affordable(crops, coins):
    unlocked = [c for c in crops if not c.get("locked", True)]
    affordable = [c for c in unlocked if c.get("plantCost", 0) <= coins]
    if affordable:
        best = max(affordable, key=lambda x: x.get("payout", 0))
        return best.get("id", "wheat"), best.get("plantCost", 0)
    if unlocked:
        cheapest = min(unlocked, key=lambda x: x.get("plantCost", 999999))
        return cheapest.get("id", "wheat"), cheapest.get("plantCost", 999999)
    return "wheat", 30


def get_cheapest_crop(crops):
    unlocked = [c for c in crops if not c.get("locked", True)]
    if not unlocked:
        return 30, "wheat"
    c = min(unlocked, key=lambda x: x.get("plantCost", 999999))
    return c.get("plantCost", 30), c.get("id", "wheat")


# ═══════════════ ACTIONS ═══════════════
def action_harvest(plot_idx):
    _state["aksi"] = f"panen lahan {plot_idx}"
    render_dashboard()
    r = make_request("post", "/ads/harvest/session", {"idx": plot_idx})
    if not r:
        return False
    if r.status_code == 409:
        return "COOLDOWN"
    if r.status_code != 200:
        return False
    try:
        d = r.json()
    except Exception:
        return False
    if not d.get("ok"):
        return False

    sid = d.get("sessionId")
    mw = d.get("minWatchSec", 8)
    push_log(f"panen [{plot_idx}] iklan {mw}s", "in")
    render_dashboard()
    time.sleep(mw + 2)

    payload = {"sessionId": sid, "provider": "adsgram", "clicked": True, "adsgramClicked": False}
    r2 = make_request("post", "/ads/harvest/complete", payload)
    if r2 and r2.status_code == 200 and r2.json().get("ok"):
        push_log(f"lahan [{plot_idx}] berhasil dipanen", "ok")
        return True
    return False


def action_water(plot_idx):
    _state["aksi"] = f"siram lahan {plot_idx}"
    render_dashboard()
    r = make_request("post", "/farm/water", {"idx": plot_idx})
    if r and r.status_code == 200 and r.json().get("ok"):
        push_log(f"siram lahan [{plot_idx}]", "w")
        return True
    return False


def action_plant(plot_idx, crop_id):
    _state["aksi"] = f"tanam {crop_id}@{plot_idx}"
    render_dashboard()
    r = make_request("post", "/farm/plant", {"idx": plot_idx, "crop": crop_id})
    if r and r.status_code == 200 and r.json().get("ok"):
        push_log(f"{crop_id.upper()} ditanam di [{plot_idx}]", "s")
        return True
    if r and r.status_code == 400:
        body = r.text.lower()
        if any(k in body for k in ["coin", "insufficient", "balance", "funds"]):
            push_log("koin tidak cukup", "wr")
            return "NO_COINS"
    return False


def action_refill_water():
    _state["aksi"] = "isi air"
    render_dashboard()
    r = make_request("post", "/ads/farm/session", {"ref": "water"})
    if not r:
        return False
    if r.status_code == 409:
        return "COOLDOWN"
    if r.status_code != 200:
        return False
    try:
        d = r.json()
    except Exception:
        return False
    if not d.get("ok"):
        return False

    sid = d.get("sessionId")
    mw = d.get("minWatchSec", 6)
    push_log(f"isi air, iklan {mw}s", "in")
    render_dashboard()
    time.sleep(mw + 2)

    payload = {"sessionId": sid, "ref": "water", "provider": "adsgram",
               "clicked": True, "adsgramClicked": False}
    r2 = make_request("post", "/ads/farm/complete", payload)
    if r2 and r2.status_code == 200 and r2.json().get("ok"):
        push_log("air terisi penuh", "ok")
        return True
    return False


def action_watch_ad_task(task_id, title, min_watch=8):
    _state["aksi"] = f"iklan {title[:12]}"
    render_dashboard()
    r = make_request("post", f"/ads/task/{task_id}/session", {"slotIndex": -1})
    if not r:
        return False
    if r.status_code == 409:
        return "COOLDOWN"
    if r.status_code != 200:
        return False
    try:
        d = r.json()
    except Exception:
        return False
    if not d.get("ok"):
        return False

    sid = d.get("sessionId")
    mw = d.get("minWatchSec", min_watch)
    slot = d.get("slotIndex", 0)
    prov = d.get("provider", "adsgram")
    push_log(f"nonton [{title}] {mw}s", "in")
    render_dashboard()
    time.sleep(mw + 2)

    payload = {"sessionId": sid, "slotIndex": slot, "provider": prov,
               "clicked": True, "adsgramClicked": False}
    r2 = make_request("post", f"/ads/task/{task_id}/complete", payload)
    if r2 and r2.status_code == 200:
        try:
            d2 = r2.json()
            if d2.get("ok"):
                gain = d2.get("reward") or 0
                _state["session_gained"] += gain
                push_log(f"[{title}] +{gain}", "ok")
                return True
        except Exception:
            pass
    return False


def action_adsgram_task(task_id, title, block_id):
    """Adsgram Task: POST /ads/task/{id}/reward."""
    _state["aksi"] = f"adsgram {title[:12]}"
    render_dashboard()

    try:
        initp = parse_initdata(INIT_DATA)
        if initp:
            block_num = re.sub(r"^task-", "", str(block_id))
            params = {
                "envType": "telegram",
                "blockId": block_num,
                "platform": "Linux aarch64",
                "language": "id",
                "top_domain": "farm-buddies-4g5.pages.dev",
                "signature": initp["signature"],
                "data_check_string": base64.b64encode(
                    initp["data_check_string"].encode()).decode(),
                "sdk_version": "2.2.5",
                "tg_id": initp["user_id"],
                "tg_platform": "android",
                "tma_version": "9.6",
            }
            adv = requests.get(
                "https://api.adsgram.ai/adv", params=params,
                headers={"Origin": "https://farm-buddies-4g5.pages.dev",
                         "Referer": "https://farm-buddies-4g5.pages.dev/",
                         "User-Agent": session.headers["User-Agent"],
                         "Accept": "*/*"}, timeout=12)
            if adv.status_code == 200:
                banners = adv.json().get("banners", [])
                if banners:
                    trackings = {t["name"]: t["value"] for t in
                                 banners[0].get("banner", {}).get("trackings", [])}
                    for k in ("render", "show"):
                        if k in trackings:
                            try:
                                requests.get(trackings[k], timeout=6)
                            except Exception:
                                pass
                    push_log(f"[ADG] banner {len(trackings)} tracking", "in")
                    render_dashboard()
                    time.sleep(9)
                    if trackings.get("reward"):
                        try:
                            requests.get(trackings["reward"], timeout=6)
                        except Exception:
                            pass
    except Exception as e:
        push_log(f"[ADG] adv err: {str(e)[:40]}", "wr")

    r = make_request("post", f"/ads/task/{task_id}/reward", {})
    if not r:
        push_log("[ADG] tidak ada respon", "er")
        return False
    if r.status_code == 409:
        push_log("[ADG] cooldown", "wr")
        return "COOLDOWN"
    if r.status_code != 200:
        push_log(f"[ADG] HTTP {r.status_code}", "er")
        return False
    try:
        d = r.json()
    except Exception:
        return False
    if not d.get("ok"):
        push_log(f"[ADG] {d.get('message', 'gagal')}", "er")
        return False

    reward = d.get("reward", 0)
    if d.get("already"):
        push_log("[ADG] sudah diklaim", "wr")
        return "COOLDOWN"

    _state["session_gained"] += reward
    push_log(f"[ADG] +{reward} koin | {d.get('usedToday', '?')}/{d.get('total', '?')}", "ok")
    prof = d.get("profile", {})
    if prof:
        _state["coins"] = prof.get("coins", _state["coins"])
        _state["today_earned"] = prof.get("todayEarned", _state["today_earned"])
        _state["ads_done"] = prof.get("totalAds", _state["ads_done"])
    return True


def action_link_task(task_id, title, url, dwell=15, verify=15):
    _state["aksi"] = f"link {title[:12]}"
    render_dashboard()

    r = make_request("post", f"/tasks/{task_id}/start", {})
    start_reward = 0
    if r and r.status_code == 200:
        try:
            d = r.json()
            if d.get("ok"):
                start_reward = d.get("reward", 0)
                if start_reward:
                    _state["session_gained"] += start_reward
                    push_log(f"[LINK #{task_id}] start +{start_reward}", "ok")
        except Exception:
            pass
    elif r and r.status_code == 409:
        push_log(f"[LINK #{task_id}] cooldown", "wr")
        return "COOLDOWN"

    if url:
        try:
            requests.get(url, headers={
                "User-Agent": session.headers["User-Agent"],
                "Referer": "https://farm-buddies-4g5.pages.dev/",
            }, timeout=20, allow_redirects=True)
            push_log(f"[LINK #{task_id}] URL dibuka", "in")
            render_dashboard()
        except Exception as e:
            push_log(f"[LINK] err: {str(e)[:40]}", "wr")

    time.sleep(dwell + 3)

    r2 = make_request("post", f"/tasks/{task_id}/claim", {})
    if r2 and r2.status_code == 200:
        try:
            d2 = r2.json()
            if d2.get("ok"):
                gain = d2.get("reward", 0) or start_reward
                _state["session_gained"] += gain
                _state["claimed_ids"].add(task_id)
                push_log(f"[LINK #{task_id}] +{gain}", "ok")
                return True
            push_log(f"[LINK #{task_id}] {d2.get('message', 'belum valid')}", "wr")
            _state["claimed_ids"].add(task_id)
        except Exception:
            pass
    elif r2 and r2.status_code == 409:
        push_log(f"[LINK #{task_id}] cooldown", "wr")
        _state["claimed_ids"].add(task_id)
        return "COOLDOWN"
    return False


def action_claim_task(task_id, title, expected_reward=0):
    """Task dengan progress >= target, tinggal klaim."""
    _state["aksi"] = f"klaim #{task_id}"
    render_dashboard()
    for ep in (f"/tasks/{task_id}/claim", f"/tasks/{task_id}/complete"):
        r = make_request("post", ep, {})
        if not r or r.status_code in (404, 405):
            continue
        if r.status_code == 200:
            try:
                d = r.json()
            except Exception:
                continue
            if d.get("ok"):
                gain = (d.get("reward") or d.get("coins") or
                        d.get("claimedCoins") or expected_reward or 0)
                _state["claimed_ids"].add(task_id)
                _state["session_gained"] += gain
                push_log(f"[KLAIM #{task_id}] {title} +{gain}", "ok")
                return True
            msg = d.get("message", "")
            _state["claimed_ids"].add(task_id)
            push_log(f"[KLAIM #{task_id}] {msg or 'dilewati'}", "wr")
            return "COOLDOWN"
        if r.status_code == 409:
            _state["claimed_ids"].add(task_id)
            push_log(f"[KLAIM #{task_id}] cooldown", "wr")
            return "COOLDOWN"
    _state["claimed_ids"].add(task_id)
    return False


def action_streak():
    _state["aksi"] = "klaim streak"
    render_dashboard()
    r = make_request("post", "/user/streak/claim", {})
    if not r:
        return False
    if r.status_code == 200:
        try:
            d = r.json()
        except Exception:
            return False
        if d.get("ok"):
            gained = d.get("reward", 0)
            _state["session_gained"] += gained
            push_log(f"[STREAK] +{gained} koin", "ok")
            return True
        code = d.get("code", "")
        if code == "STREAK_BIO_REQUIRED":
            push_log("[STREAK] butuh link referral di bio Telegram", "wr")
            return "BIO"
        msg = d.get("message", "")
        if "already" in msg.lower() or "claimed" in msg.lower():
            push_log("[STREAK] sudah diklaim hari ini", "wr")
            return "DONE"
        push_log(f"[STREAK] {msg or code}", "wr")
        return False
    if r.status_code == 409:
        push_log("[STREAK] sudah diklaim", "wr")
        return "DONE"
    return False


def action_shortlink(provider_id, provider_name, reward_coins):
    _state["aksi"] = f"short {provider_id[:10]}"
    render_dashboard()

    r = make_request("post", f"/shortlinks/{provider_id}/issue", {})
    short_url = None
    if r and r.status_code == 200:
        try:
            d = r.json()
            if d.get("ok"):
                short_url = d.get("shortUrl") or d.get("url")
                push_log(f"[SHORT] {provider_name}: link dibuat", "in")
        except Exception:
            pass
    if r and r.status_code == 409:
        push_log(f"[SHORT] {provider_name}: cooldown", "wr")
        return "COOLDOWN"
    if not short_url:
        return False

    try:
        requests.get(short_url, headers={
            "User-Agent": session.headers["User-Agent"],
            "Referer": "https://farm-buddies-4g5.pages.dev/",
        }, timeout=20, allow_redirects=True)
        push_log(f"[SHORT] {provider_name}: dibuka", "in")
        render_dashboard()
    except Exception as e:
        push_log(f"[SHORT] err: {str(e)[:40]}", "wr")

    time.sleep(8)

    r2 = make_request("post", f"/shortlinks/{provider_id}/claim", {})
    if r2 and r2.status_code == 200:
        try:
            if r2.json().get("ok"):
                _state["session_gained"] += reward_coins
                push_log(f"[SHORT] {provider_name}: +{reward_coins}", "ok")
                return True
        except Exception:
            pass
    return False


# ═══════════════ FASE 1: TASK ═══════════════
def run_tasks_phase(s):
    """Kerjakan task. True = ada aksi sukses (loop akan sync ulang & lanjut task)."""
    tasks = s["tasks"]

    # T0. klaim task yang progress >= target
    for t in tasks:
        if t.get("state") != "open":
            continue
        tid = t.get("id")
        if tid in _state["claimed_ids"]:
            continue
        rew = t.get("reward", 0)
        if rew <= 0:
            continue
        if t.get("type") in ("link", "telegram", "offerwall"):
            continue
        if t.get("adsgramTask"):
            continue
        prog = t.get("progress", 0)
        tgt = t.get("target", 1)
        if prog >= tgt and tgt > 0:
            if action_claim_task(tid, t.get("title", "?"), rew):
                return True

    # T1. adsgram task
    for t in tasks:
        if not t.get("adsgramTask") or t.get("state") != "open":
            continue
        tid = t.get("id")
        block = t.get("blockId")
        title = t.get("title", "Adsgram Task")
        if not block:
            continue
        nxt = t.get("nextAdAt") or 0
        if nxt and nxt > int(time.time() * 1000):
            continue
        if action_adsgram_task(tid, title, block) is True:
            return True

    # T2. link task
    for t in tasks:
        if t.get("type") != "link" or t.get("state") != "open" or not t.get("url"):
            continue
        tid = t.get("id")
        if tid in _state["claimed_ids"]:
            continue
        dwell = t.get("dwellSec", 15)
        verify = t.get("verifySec", 15)
        res = action_link_task(tid, t.get("title", "Link"), t.get("url"), dwell, verify)
        if res is True:
            return True

    # T3. ads task biasa (reward terbesar dulu)
    ad_tasks = [t for t in tasks if t.get("type") == "ad"
                and not t.get("adsgramTask") and t.get("state") == "open"]
    ad_tasks.sort(key=lambda x: x.get("reward", 0), reverse=True)
    for t in ad_tasks:
        tid = t.get("id")
        title = t.get("title", "Ad")
        if t.get("progress", 0) >= t.get("target", 10):
            continue
        res = action_watch_ad_task(tid, title)
        if res is True:
            return True
        if res == "COOLDOWN":
            time.sleep(1)

    # T4. shortlinks
    sl_res = make_request("get", "/shortlinks")
    if sl_res and sl_res.status_code == 200:
        try:
            summaries = sl_res.json().get("shortlinks", {}).get("summaries", {})
            for pid, info in summaries.items():
                if not info.get("enabled") or not info.get("canIssue"):
                    continue
                if info.get("remainingCount", 0) <= 0:
                    continue
                if info.get("status") == "claimed":
                    continue
                res = action_shortlink(pid, info.get("providerName", pid),
                                       info.get("rewardCoins", 0))
                if res is True:
                    return True
        except Exception:
            pass

    return False


# ═══════════════ FASE 2: FARM ═══════════════
def run_farm_phase(s):
    plots = s["plots"]
    coins = s["coins"]
    water = s["water"]
    crops = s.get("crops") or [
        {"id": "wheat", "payout": 30, "plantCost": 30, "locked": False},
        {"id": "carrot", "payout": 60, "plantCost": 60, "locked": False},
        {"id": "corn", "payout": 90, "plantCost": 90, "locked": False},
    ]

    # F1. panen
    for p in plots:
        if p.get("state") == "ready":
            idx = p.get("idx")
            push_log(f"lahan [{idx}] {p.get('name', 'crop')} siap (+{p.get('payout', 0)})", "f")
            render_dashboard()
            res = action_harvest(idx)
            if res is True:
                return True
            if res == "COOLDOWN":
                time.sleep(1)

    # F2. siram
    if water > 0:
        for p in plots:
            if p.get("state") in ("growing", "ready") and not p.get("watered", False):
                if action_water(p.get("idx")):
                    return True

    # F3. tanam
    empty_plots = [p for p in plots if p.get("state") == "empty" and not p.get("locked", False)]
    cheapest_cost, _ = get_cheapest_crop(crops)
    if empty_plots and coins >= cheapest_cost:
        crop_id, cost = get_best_affordable(crops, coins)
        idx = empty_plots[0].get("idx")
        push_log(f"tanam {crop_id.upper()} (biaya {cost}) @{idx}", "s")
        render_dashboard()
        if action_plant(idx, crop_id) is True:
            return True

    # F4. streak
    if not s.get("streak_claimed"):
        res = action_streak()
        if res is True:
            return True
        if res in ("BIO", "DONE"):
            _state["streak_claimed"] = True

    # F5. isi air
    if water == 0:
        push_log("air habis, isi ulang", "wr")
        render_dashboard()
        if action_refill_water() is True:
            return True

    return False


# ═══════════════ SCANNER: TASK DULU, BARU FARM ═══════════════
def run_smart_scanner(s):
    # Fase 1: task (dilewati sementara kalau barusan kosong)
    if time.time() >= _state["tasks_resume_at"]:
        _state["status"] = "tasks"
        render_dashboard()
        if run_tasks_phase(s):
            return True
        _state["tasks_resume_at"] = time.time() + TASK_RECHECK_SEC
        push_log(f"task kosong, cek ulang {TASK_RECHECK_SEC}s", "g")

    # Fase 2: farm
    _state["status"] = "farming"
    render_dashboard()
    return run_farm_phase(s)


# ═══════════════ MAIN LOOP ═══════════════
def run_bot():
    global BASE_URL, FARM_FP, DEVICE_ID, INIT_DATA
    BASE_URL = CONFIG.get("base_url", "https://farm-buddies-api.nhathaybip2000.workers.dev/api")
    FARM_FP = CONFIG.get("fingerprint", "")
    DEVICE_ID = CONFIG.get("device_id", "")
    INIT_DATA = CONFIG.get("init_data", "")

    _state["start"] = time.time()
    _state["status"] = "boot"
    _state["tasks_resume_at"] = 0
    _state["claimed_ids"].clear()

    if not authenticate():
        push_log("login awal gagal", "er")
        render_dashboard()
        time.sleep(3)
        return

    if fetch_state():
        push_log(f"login sebagai {_state['user']}", "ok")
        render_dashboard()

    push_log("cek force-join...", "in")
    render_dashboard()
    fj = make_request("get", "/user/force-join")
    if fj and fj.status_code == 200:
        try:
            req = fj.json().get("required", [])
            if req:
                push_log(f"[JOIN] wajib join {len(req)} channel", "wr")
            else:
                push_log("[JOIN] semua aman", "ok")
        except Exception:
            pass

    push_log("bot jalan: task dulu, lalu farm", "g")
    render_dashboard()

    idle_count = 0
    while True:
        try:
            s = fetch_state()
            if not s:
                push_log("gagal sync, coba lagi 10s", "wr")
                render_dashboard()
                time.sleep(10)
                continue

            acted = run_smart_scanner(s)

            if acted:
                idle_count = 0
                time.sleep(2)
            else:
                idle_count += 1
                if idle_count >= 3:
                    push_log("semua cooldown, idle 5 menit", "wr")
                    _state["status"] = "idle"
                    _state["aksi"] = "menunggu cooldown"
                    render_dashboard()
                    time.sleep(300)
                    idle_count = 0
                else:
                    push_log(f"idle, tunggu 20s ({idle_count}/3)", "wr")
                    _state["aksi"] = "idle"
                    render_dashboard()
                    time.sleep(20)

        except KeyboardInterrupt:
            push_log("dihentikan manual", "wr")
            render_dashboard()
            print(f"\n{fg(C_WARN)}Dihentikan. Kembali ke menu...{RST}")
            time.sleep(1.5)
            return
        except Exception as e:
            push_log(f"loop error: {str(e)[:50]}", "er")
            render_dashboard()
            time.sleep(30)


# ═══════════════ MENU ═══════════════
def banner_menu():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(top())
    sys.stdout.write(row(gradient("🌾 FARM BUDDIES AUTO")))
    sys.stdout.write(row(fg(C_MUTED) + "mode: task dulu, lalu farm" + RST))
    sys.stdout.write(bot())
    print()


def main():
    global CONFIG
    while True:
        banner_menu()
        print(f"  {fg(C_TITLE_B)}[1]{RST} {fg(C_TEXT)}Jalankan bot{RST}")
        print(f"  {fg(C_TITLE_B)}[2]{RST} {fg(C_TEXT)}Isi init_data{RST}")
        print(f"  {fg(C_TITLE_B)}[3]{RST} {fg(C_TEXT)}Hapus data{RST}")
        print(f"  {fg(C_TITLE_B)}[0]{RST} {fg(C_TEXT)}Keluar{RST}\n")
        pilih = input(f"{fg(C_TITLE_A)}› Pilih menu :{RST} ").strip()

        if pilih == "1":
            if os.path.exists(CONFIG_FILE):
                CONFIG = load_config()
                run_bot()
            else:
                print(f"\n{fg(C_ERR)}Data belum diisi, pilih menu 2 dulu.{RST}")
                time.sleep(2)
        elif pilih == "2":
            isi_data()
        elif pilih == "3":
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
                print(f"\n{fg(C_OK)}config.json dihapus.{RST}")
            else:
                print(f"\n{fg(C_WARN)}Tidak ada config.json.{RST}")
            time.sleep(2)
        elif pilih == "0":
            print(f"\n{fg(C_TITLE_B)}Sampai jumpa!{RST}\n")
            sys.exit(0)
        else:
            print(f"\n{fg(C_ERR)}Pilihan tidak valid.{RST}")
            time.sleep(1)


if __name__ == "__main__":
    main()
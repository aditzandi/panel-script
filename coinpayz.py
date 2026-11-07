# ==========================================
# CoinPayz Auto-Claim Bot — tampilan oleh JEM BOT
# ==========================================
import os
import sys
import re
import json
import time
import math
import base64
import urllib.parse
from datetime import datetime, timezone
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import cv2
import numpy as np

# Aktifkan dukungan warna ANSI di terminal Windows
if os.name == "nt":
    os.system("")

# Pastikan UTF-8 output di terminal Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coinpayz_config.json")

# ANSI color codes
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_RED = "\033[91m"
C_MAGENTA = "\033[95m"
C_DIM = "\033[2m"

# ==========================================
# 1. LOCAL SLIDER SOLVER (BUILT-IN)
# ==========================================
def compute_A(e):
    knots = e['x']['knots']
    speeds = e['x']['speeds']
    i = [0]
    for k in range(len(knots) - 1):
        i.append(i[k] + (knots[k+1] - knots[k]) * (speeds[k] + speeds[k+1]) / 2.0)
    return {"cumulative": i, "total": i[-1]}

def get_N(motion, t):
    T = 65535.0
    r = max(0.0, min(T, float(t))) / T
    A_res = compute_A(motion)
    a = A_res["cumulative"]
    o = A_res["total"]
    s = motion["x"]
    c = 0
    while c < len(s["knots"]) - 2 and r > s["knots"][c + 1]:
        c += 1
    l = s["knots"][c + 1] - s["knots"][c]
    u = (r - s["knots"][c]) / l
    d = u * u * u
    f = a[c] + l * (s["speeds"][c] * u + (s["speeds"][c + 1] - s["speeds"][c]) * (d - 0.5 * d * u))
    
    x = s["start"] if r == 0 else (s["end"] if r == 1 else s["start"] + (s["end"] - s["start"]) * f / o)
    p = 2 * math.pi * r
    y = motion["y"]["center"] + motion["y"]["amplitude"] * math.sin(p + motion["y"]["phase"])
    scale = motion["scale"]["base"] + motion["scale"]["amplitude"] * math.sin(p + motion["scale"]["phase"])
    rotation = motion["rotation"]["amplitude"] * math.sin(p + motion["rotation"]["phase"])
    return x, y, scale, rotation

def solve_local_slider(challenge_data: dict) -> int:
    """Selesaikan challenge puzzle local_slider CoinPayz secara otomatis."""
    ch = challenge_data["challenge"]
    motion = ch["motion"]
    bg_b64 = ch["background_image"].split(",")[1]
    bg_bytes = base64.b64decode(bg_b64)
    bg_img = cv2.imdecode(np.frombuffer(bg_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)

    # Deteksi lubang gelap di background
    dark_val = bg_img.min()
    mask_dark = (bg_img <= dark_val + 2).astype(np.uint8)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_dark)
    candidate_holes = []
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        if 4000 < area < 40000 and 60 < w < 220 and 60 < h < 220:
            candidate_holes.append(centroids[i])

    trajectory_points = []
    for t_val in range(0, 65536, 20):
        x, y, scale, rot = get_N(motion, t_val)
        trajectory_points.append((t_val, x, y))

    target_hole = None
    best_dist = float('inf')
    for cent in candidate_holes:
        min_d = min(math.hypot(x - cent[0], y - cent[1]) for _, x, y in trajectory_points)
        if min_d < best_dist:
            best_dist = min_d
            target_hole = cent

    if target_hole is None:
        target_hole = [500, 300]

    min_dist = float('inf')
    refined_t = 0
    for t_val in range(0, 65536, 1):
        x, y, scale, rot = get_N(motion, t_val)
        d = math.hypot(x - target_hole[0], y - target_hole[1])
        if d < min_dist:
            min_dist = d
            refined_t = t_val

    return refined_t

# ==========================================
# 2. WARYONO / SKIBIDIXXX SOLVER (BUILT-IN)
# ==========================================
class WaryonoSolver:
    BASE_URL = "https://api.waryono.my.id"

    def __init__(self, apikey: str = ""):
        self.apikey = apikey.strip()

    def set_apikey(self, apikey: str):
        self.apikey = apikey.strip()

    def get_balance(self) -> dict:
        """Cek saldo token di SKIBIDIXXX / waryono.my.id"""
        if not self.apikey:
            return {"success": False, "error": "API Key belum diisi"}
        try:
            url = f"{self.BASE_URL}/balance.php?apikey={self.apikey}"
            res = requests.get(url, timeout=15)
            try:
                data = res.json()
                if data.get("status") == 1 or "balance" in data:
                    return {"success": True, "balance": data.get("balance", data.get("request"))}
                return {"success": False, "error": data.get("request", res.text)}
            except Exception:
                if "OK|" in res.text or res.status_code == 200:
                    return {"success": True, "balance": res.text.replace("OK|", "").strip()}
                return {"success": False, "error": res.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def solve_turnstile(self, domain: str = "https://coinpayz.xyz", sitekey: str = "0x4AAAAAAAj5kHUcgK4XbIq_", timeout: int = 90) -> dict:
        if not self.apikey:
            return {"success": False, "error": "Waryono API Key belum disetting"}

        submit_url = f"{self.BASE_URL}/in.php"
        payload = {
            "apikey": self.apikey,
            "methods": "turnstile",
            "domain": domain,
            "sitekey": sitekey,
            "json": 1
        }

        try:
            res = requests.post(submit_url, json=payload, timeout=20)
            data = res.json()
        except Exception as e:
            return {"success": False, "error": f"Gagal submit task Turnstile: {e}"}

        if data.get("status") != 1:
            return {"success": False, "error": f"Submit error: {data.get('request', res.text)}"}

        task_id = data.get("request")
        poll_url = f"{self.BASE_URL}/res.php?apikey={self.apikey}&id={task_id}&action=get&json=1"
        start_time = time.time()

        while time.time() - start_time < timeout:
            time.sleep(5)
            try:
                p_res = requests.get(poll_url, timeout=15)
                p_data = p_res.json()
                if p_data.get("status") == 1:
                    return {"success": True, "token": p_data.get("request")}
                elif p_data.get("request") in ["CAPCHA_NOT_READY", "CAPTCHA_NOT_READY"]:
                    continue
                else:
                    return {"success": False, "error": f"Solver gagal: {p_data.get('request')}"}
            except Exception:
                continue

        return {"success": False, "error": "Timeout menunggu penyelesaian Turnstile"}

# ==========================================
# 3. COINPAYZ CLIENT (BUILT-IN)
# ==========================================
class CoinPayzClient:
    BASE_URL = "https://coinpayz.xyz"
    DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    )

    def __init__(self, cookie_string: str = "", user_agent: str = None):
        self.cookie_string = cookie_string.strip()
        self.user_agent = user_agent or self.DEFAULT_UA
        self.session = cffi_requests.Session(impersonate="chrome124")
        self._update_session_headers()

    def set_cookie(self, cookie_string: str):
        self.cookie_string = cookie_string.strip()
        self._update_session_headers()

    def _extract_xsrf_token(self) -> str:
        for part in self.cookie_string.split(";"):
            part = part.strip()
            if part.startswith("XSRF-TOKEN="):
                return urllib.parse.unquote(part.split("=", 1)[1])
        return ""

    def _update_session_headers(self):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": self.cookie_string,
        }
        xsrf = self._extract_xsrf_token()
        if xsrf:
            headers["X-XSRF-TOKEN"] = xsrf
        self.session.headers.update(headers)

    def _sync_csrf(self):
        if "XSRF-TOKEN" in self.session.cookies:
            self.session.headers["X-XSRF-TOKEN"] = urllib.parse.unquote(self.session.cookies["XSRF-TOKEN"])

    def _parse_inertia_script(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        for s in soup.find_all("script"):
            if not s.get("src") and "component" in s.text:
                try:
                    return json.loads(s.text.strip())
                except Exception:
                    pass
        return {}

    def get_dashboard(self) -> dict:
        res = self.session.get(f"{self.BASE_URL}/dashboard")
        if res.status_code != 200:
            return {"success": False, "status_code": res.status_code, "error": "Failed to fetch dashboard"}
        
        self._sync_csrf()
        data = self._parse_inertia_script(res.text)
        if not data:
            return {"success": False, "status_code": res.status_code, "error": "Invalid dashboard response / session expired"}

        props = data.get("props", {})
        auth = props.get("auth", {})
        user = auth.get("user", {})
        stats = auth.get("stats", {})
        dashboard = props.get("dashboard", {})

        if not user.get("id"):
            return {"success": False, "status_code": res.status_code, "error": "Session cookie is invalid or expired"}

        return {
            "success": True,
            "status_code": 200,
            "user": user,
            "stats": stats,
            "dashboard": dashboard,
            "settings": props.get("settings_public", {})
        }

    def solve_slider_for_page(self, page: str = "ptc") -> dict:
        self._sync_csrf()
        challenge_url = f"{self.BASE_URL}/captcha/local-slider/challenge"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/{page}"
        }

        try:
            c_res = self.session.post(challenge_url, json={"page": page}, headers=headers)
            if c_res.status_code != 200:
                return {"success": False, "error": f"Gagal request challenge slider: HTTP {c_res.status_code}"}
            ch_data = c_res.json()
        except Exception as e:
            return {"success": False, "error": f"Error challenge slider: {e}"}

        ch_id = ch_data.get("challenge_id")
        if not ch_id:
            return {"success": False, "error": f"Invalid challenge response: {ch_data}"}

        t_sol = solve_local_slider(ch_data)
        solve_url = f"{self.BASE_URL}/captcha/local-slider/solve"
        payload = {
            "challenge_id": ch_id,
            "answer": {
                "value": t_sol
            }
        }

        try:
            s_res = self.session.post(solve_url, json=payload, headers=headers)
            s_data = s_res.json()
            if s_data.get("success"):
                return {"success": True, "token": s_data.get("token")}
            return {"success": False, "error": f"Slider solve rejected: {s_data}"}
        except Exception as e:
            return {"success": False, "error": f"Error solve slider: {e}"}

    def get_faucet_status(self) -> dict:
        res = self.session.get(f"{self.BASE_URL}/faucet")
        if res.status_code != 200:
            return {"success": False, "error": f"HTTP {res.status_code}"}

        self._sync_csrf()
        data = self._parse_inertia_script(res.text)
        props = data.get("props", {})
        stats = props.get("auth", {}).get("stats", {})
        settings = props.get("settings_public", {})

        timer = int(settings.get("faucet.timer", {}).get("value", 300))
        daily_limit = int(settings.get("faucet.daily_limit", {}).get("value", 20))
        reward = settings.get("faucet.reward", {}).get("value", "0.0005")
        claims_today = int(stats.get("faucet_claims_today", 0))
        last_claim_at = stats.get("last_faucet_claim_at")

        claims_left = max(0, daily_limit - claims_today)
        cooldown_left = 0
        if last_claim_at:
            try:
                last_dt = datetime.fromisoformat(last_claim_at.replace("Z", "+00:00"))
                now_dt = datetime.now(timezone.utc)
                elapsed = (now_dt - last_dt).total_seconds()
                if elapsed < timer:
                    cooldown_left = int(timer - elapsed)
            except Exception:
                cooldown_left = 0

        is_ready = (claims_left > 0) and (cooldown_left == 0)
        is_limit_reached = (claims_left <= 0)

        return {
            "success": True,
            "reward": reward,
            "timer_seconds": timer,
            "daily_limit": daily_limit,
            "claims_today": claims_today,
            "claims_left": claims_left,
            "last_claim_at": last_claim_at,
            "cooldown_left_seconds": cooldown_left,
            "is_ready": is_ready,
            "is_limit_reached": is_limit_reached
        }

    def claim_faucet(self, captcha_token: str, captcha_provider: str = "local_slider") -> dict:
        self._sync_csrf()
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/html, application/xhtml+xml",
            "X-Inertia": "true",
            "X-Inertia-Version": "506f710dbf6b5717315b2f8ddb37646b",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/faucet"
        }

        payload = {
            "captcha_provider": captcha_provider,
            "captcha_token": captcha_token,
            "use_energy": "0",
            "maximum_energy_cost": 0
        }

        res = self.session.post(f"{self.BASE_URL}/faucet/claim", json=payload, headers=headers)
        self._sync_csrf()

        try:
            data = res.json()
            flash = data.get("props", {}).get("flash", {})
            errors = data.get("props", {}).get("errors", {})
            if errors:
                return {"success": False, "error": errors}
            toast = flash.get("toast", {})
            msg = toast.get("message") if isinstance(toast, dict) else flash.get("success", "Faucet claimed successfully!")
            return {"success": True, "message": msg or "Faucet claimed successfully!"}
        except Exception:
            if res.status_code in [200, 302]:
                return {"success": True, "message": "Faucet claimed! (Redirected)"}
            return {"success": False, "error": f"HTTP {res.status_code}: {res.text[:200]}"}

    def get_ptc_ads(self) -> dict:
        headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/ptc"
        }
        res = self.session.get(f"{self.BASE_URL}/ptc/providers/refresh", headers=headers)
        if res.status_code != 200:
            return {"success": False, "error": f"HTTP {res.status_code}"}

        try:
            data = res.json()
        except Exception as e:
            return {"success": False, "error": f"JSON parse error: {e}"}

        payloads = data.get("payloads", {})
        local = payloads.get("local", {})
        local_ads = local.get("ads", [])
        unclaimed_local = [ad for ad in local_ads if not ad.get("claimed", False)]
        total_local_reward = sum(float(ad.get("reward", 0)) for ad in unclaimed_local)

        return {
            "success": True,
            "local_ads": unclaimed_local,
            "local_count": len(unclaimed_local),
            "total_local_reward": total_local_reward
        }

    def start_ptc_ad(self, ad_hash: str) -> dict:
        url = f"{self.BASE_URL}/ptc/start/{ad_hash}"
        res = self.session.get(url)
        if res.status_code != 200:
            return {"success": False, "error": f"HTTP {res.status_code}"}

        self._sync_csrf()
        data = self._parse_inertia_script(res.text)
        ad = data.get("props", {}).get("ad", {})
        return {
            "success": True,
            "ad": ad,
            "timer": ad.get("timer", 15)
        }

    def claim_ptc_ad(self, ad_hash: str, captcha_token: str, captcha_provider: str = "local_slider") -> dict:
        self._sync_csrf()
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/html, application/xhtml+xml",
            "X-Inertia": "true",
            "X-Inertia-Version": "506f710dbf6b5717315b2f8ddb37646b",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/ptc/start/{ad_hash}"
        }

        payload = {
            "ad_hash": ad_hash,
            "captcha_provider": captcha_provider,
            "captcha_token": captcha_token
        }

        res = self.session.post(f"{self.BASE_URL}/ptc/claim", json=payload, headers=headers)
        self._sync_csrf()

        try:
            data = res.json()
            flash = data.get("props", {}).get("flash", {})
            errors = data.get("props", {}).get("errors", {})
            if errors:
                return {"success": False, "error": errors}
            return {
                "success": True,
                "message": flash.get("success", "PTC Ad claimed successfully!")
            }
        except Exception:
            if res.status_code in [200, 302]:
                return {"success": True, "message": "PTC Ad claimed! (Redirected)"}
            return {"success": False, "error": f"HTTP {res.status_code}: {res.text[:200]}"}

    def get_challenges(self) -> dict:
        res = self.session.get(f"{self.BASE_URL}/challenges")
        if res.status_code != 200:
            return {"success": False, "error": f"HTTP {res.status_code}"}

        self._sync_csrf()
        data = self._parse_inertia_script(res.text)
        challenges_data = data.get("props", {}).get("daily_challenges", {})
        groups = challenges_data.get("groups", [])
        claimable_challenges = []

        for group in groups:
            category = group.get("category", "")
            for ch in group.get("challenges", []):
                item = {
                    "id": ch.get("id"),
                    "category": category,
                    "target": ch.get("target"),
                    "progress": ch.get("progress"),
                    "reward": ch.get("reward"),
                    "claimed": ch.get("claimed", False),
                    "claimable": ch.get("claimable", False)
                }
                if item["claimable"] and not item["claimed"]:
                    claimable_challenges.append(item)

        return {"success": True, "claimable": claimable_challenges}

    def claim_challenge(self, challenge_id: int) -> dict:
        self._sync_csrf()
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/html, application/xhtml+xml",
            "X-Inertia": "true",
            "X-Inertia-Version": "506f710dbf6b5717315b2f8ddb37646b",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/challenges"
        }

        url = f"{self.BASE_URL}/challenges/{challenge_id}/claim"
        res = self.session.post(url, json={}, headers=headers)
        self._sync_csrf()

        try:
            data = res.json()
            flash = data.get("props", {}).get("flash", {})
            errors = data.get("props", {}).get("errors", {})
            if errors:
                return {"success": False, "error": errors}
            return {"success": True, "message": flash.get("success", f"Challenge #{challenge_id} claimed!")}
        except Exception:
            return {"success": False, "error": f"HTTP {res.status_code}"}

# ==========================================
# 4. TAMPILAN (UI) & MENU  —  by JEM BOT
# ==========================================
APP_NAME = "JEM BOT"
APP_VERSION = "2.0"
UI_WIDTH = 64
ANSI_RE = re.compile(r"\033\[[0-9;]*m")

_LOGO = {
    "J": ["     ██╗", "     ██║", "     ██║", "██   ██║", "╚█████╔╝", " ╚════╝ "],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "M": ["███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"],
    "B": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██████╔╝", "╚═════╝ "],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
}


# ---------- Helper tampilan ----------
def vlen(text: str) -> int:
    """Panjang teks yang terlihat (tanpa kode warna ANSI)."""
    return len(ANSI_RE.sub("", text))


def clip(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def ts() -> str:
    return time.strftime("%H:%M:%S")


def center(text: str) -> str:
    return " " * max(0, (UI_WIDTH - vlen(text)) // 2) + text


def hr(char: str = "─", color: str = C_DIM):
    print(f"{color}{char * UI_WIDTH}{C_RESET}")


def box(title: str, lines: list, color: str = C_CYAN):
    """Kotak berbingkai rapi dengan judul opsional."""
    inner = UI_WIDTH - 2
    print(f"{color}╭{'─' * inner}╮{C_RESET}")
    if title:
        pad = inner - vlen(title) - 2
        print(f"{color}│{C_RESET} {C_BOLD}{title}{C_RESET}{' ' * max(0, pad)} {color}│{C_RESET}")
        print(f"{color}├{'─' * inner}┤{C_RESET}")
    for line in lines:
        pad = inner - vlen(line) - 2
        print(f"{color}│{C_RESET} {line}{' ' * max(0, pad)} {color}│{C_RESET}")
    print(f"{color}╰{'─' * inner}╯{C_RESET}")


def kv(label: str, value, width: int = 17) -> str:
    """Baris 'Label : Nilai' yang sejajar."""
    return f"{C_DIM}{label:<{width}}{C_RESET} {value}"


def badge(ok: bool, yes: str = "Tersimpan", no: str = "Belum diisi") -> str:
    if ok:
        return f"{C_GREEN}{C_BOLD}● {yes}{C_RESET}"
    return f"{C_RED}{C_BOLD}○ {no}{C_RESET}"


def chip(name: str, color: str = C_CYAN) -> str:
    return f"{color}{C_BOLD}[{name}]{C_RESET}"


def log(kind: str, msg: str):
    """Log berwaktu: ok / err / warn / info."""
    style = {
        "ok": (C_GREEN, "✓"),
        "err": (C_RED, "✗"),
        "warn": (C_YELLOW, "!"),
        "info": (C_CYAN, "i"),
    }
    color, icon = style.get(kind, style["info"])
    print(f" {C_DIM}{ts()}{C_RESET} {color}{C_BOLD}[{icon}]{C_RESET} {msg}")


def section(title: str, color: str = C_BLUE):
    line = f" {title} "
    side = max(2, (UI_WIDTH - len(line)) // 2)
    print(f"\n{color}{C_BOLD}{'━' * side}{line}{'━' * (UI_WIDTH - side - len(line))}{C_RESET}")


def progress_bar(current: int, total: int, width: int = 22) -> str:
    total = max(1, total)
    filled = int(width * max(0, min(current, total)) / total)
    return f"{C_GREEN}{'█' * filled}{C_DIM}{'░' * (width - filled)}{C_RESET}"


def countdown(seconds: int, label: str = "Menunggu"):
    """Hitung mundur dengan progress bar. Ctrl+C diteruskan ke pemanggil."""
    total = max(1, int(seconds))
    for remaining in range(total, 0, -1):
        mins, secs = divmod(remaining, 60)
        bar = progress_bar(total - remaining, total)
        sys.stdout.write(f"\r {C_DIM}{label:<18}{C_RESET} {bar} {C_YELLOW}{mins:02d}:{secs:02d}{C_RESET}   ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\r" + " " * 79 + "\r")
    sys.stdout.flush()


def ask(prompt: str) -> str:
    return input(f"\n {C_YELLOW}{C_BOLD}❯{C_RESET} {C_BOLD}{prompt}{C_RESET} ").strip()


def wait_enter():
    try:
        input(f"\n {C_DIM}Tekan [Enter] untuk kembali ke menu...{C_RESET}")
        return True
    except (KeyboardInterrupt, EOFError):
        return False


def to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}j {m}m {s}d" if h else f"{m}m {s}d"


def credit_line():
    print(center(f"{C_DIM}Dibuat dengan ♥ oleh{C_RESET} {C_YELLOW}{C_BOLD}{APP_NAME}{C_RESET}"))


# ---------- Config ----------
def load_config() -> dict:
    # Membaca konfigurasi dari coinpayz_config.json
    cfg = {
        "cookie": "",
        "base_url": "https://coinpayz.xyz",
        "waryono_apikey": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg["cookie"] = loaded.get("cookie", "")
                    cfg["base_url"] = loaded.get("base_url", "https://coinpayz.xyz")
                    cfg["waryono_apikey"] = loaded.get("waryono_apikey", "")
        except Exception:
            pass
    return cfg


def save_config(config: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        log("ok", f"Pengaturan tersimpan {C_DIM}({os.path.basename(CONFIG_FILE)}){C_RESET}")
    except Exception as e:
        log("err", f"Gagal menyimpan pengaturan: {e}")


# ---------- Banner & Menu ----------
def print_banner():
    clear_screen()
    rows = []
    for r in range(6):
        left = "".join(_LOGO[c][r] for c in "JEM")
        right = "".join(_LOGO[c][r] for c in "BOT")
        rows.append(left + "   " + right)
    colors = [C_CYAN, C_CYAN, C_BLUE, C_BLUE, C_MAGENTA, C_MAGENTA]

    print()
    for row, col in zip(rows, colors):
        print(f"    {col}{C_BOLD}{row}{C_RESET}")
    print()
    print(center(f"{C_BOLD}CoinPayz Auto-Claim  •  Faucet & PTC{C_RESET}"))
    print(center(f"{C_DIM}by{C_RESET} {C_YELLOW}{C_BOLD}{APP_NAME}{C_RESET} {C_DIM}• versi {APP_VERSION}{C_RESET}"))
    hr("═", C_CYAN)


def print_menu(config: dict):
    cookie_ok = bool(config.get("cookie", "").strip())
    api_key = config.get("waryono_apikey", "").strip()
    api_preview = f" {C_DIM}({api_key[:6]}...){C_RESET}" if api_key else ""

    box("STATUS PENGATURAN", [
        kv("Cookie Login", badge(cookie_ok)),
        kv("API Key Waryono", badge(bool(api_key)) + api_preview),
    ], C_BLUE)
    print()

    def item(num, title, desc):
        return [
            f"{C_CYAN}{C_BOLD}[{num}]{C_RESET} {C_BOLD}{title}{C_RESET}",
            f"    {C_DIM}{desc}{C_RESET}",
        ]

    lines = []
    lines += item(1, "Cookie Login", "Masukkan / perbarui cookie akun CoinPayz")
    lines += item(2, "API Key Waryono", "Atur API Key SKIBIDIXXX (Waryono)")
    lines += item(3, "Profil & Saldo", "Lihat info akun, saldo, dan total pendapatan")
    lines += item(4, "Mulai Auto-Claim", "Jalankan loop Faucet, PTC Ads & Challenges")
    lines += [f"{C_RED}{C_BOLD}[0]{C_RESET} {C_BOLD}Keluar{C_RESET}"]
    box("MENU UTAMA", lines, C_CYAN)


# ---------- Panel ----------
def panel_input_cookie(config: dict, client: CoinPayzClient):
    current_cookie = config.get("cookie", "").strip()

    info = []
    if current_cookie:
        preview = current_cookie[:22] + "..." + current_cookie[-12:]
        info.append(kv("Status", badge(True)))
        info.append(kv("Cookie", f"{C_CYAN}{preview}{C_RESET}"))
        info.append(kv("Panjang", f"{len(current_cookie)} karakter"))
    else:
        info.append(kv("Status", badge(False)))

    print()
    box("PANEL 1  •  COOKIE LOGIN", info, C_YELLOW)
    print()
    box("CARA MENDAPATKAN COOKIE", [
        f"{C_BOLD}1.{C_RESET} Login ke {C_CYAN}https://coinpayz.xyz/{C_RESET} di browser",
        f"{C_BOLD}2.{C_RESET} Salin cookie (cp_session, XSRF-TOKEN, dll)",
        f"{C_BOLD}3.{C_RESET} Tempel di bawah ini",
        f"{C_DIM}Tekan [Enter] kosong untuk memakai cookie yang ada{C_RESET}",
    ], C_DIM)

    try:
        new_cookie = ask("Tempel cookie baru ›")
    except (EOFError, KeyboardInterrupt):
        return

    if not new_cookie:
        if current_cookie:
            new_cookie = current_cookie
            log("warn", "Memakai cookie yang sudah tersimpan.")
        else:
            log("err", "Cookie kosong! Kembali ke menu utama.")
            return

    print()
    log("info", "Memverifikasi cookie ke coinpayz.xyz ...")
    client.set_cookie(new_cookie)
    result = client.get_dashboard()

    print()
    if result.get("success"):
        config["cookie"] = new_cookie
        save_config(config)
        user = result["user"]
        stats = result["stats"]
        box(f"{C_GREEN}✓ LOGIN BERHASIL{C_RESET}", [
            kv("User ID", user.get("id")),
            kv("Username", f"{C_GREEN}{C_BOLD}{user.get('username')}{C_RESET}"),
            kv("Email", clip(user.get("email"), 38)),
            kv("Saldo", f"{C_YELLOW}{C_BOLD}{stats.get('balance')} USD{C_RESET}"),
            kv("Energy", f"{C_CYAN}{stats.get('energy')} RP{C_RESET}"),
        ], C_GREEN)
    else:
        box(f"{C_RED}✗ LOGIN GAGAL{C_RESET}", [
            clip(result.get("error", "Cookie kedaluwarsa atau tidak valid"), 58),
            f"{C_DIM}Coba login ulang di browser lalu salin cookie baru.{C_RESET}",
        ], C_RED)


def panel_input_waryono(config: dict, solver: WaryonoSolver):
    current_key = config.get("waryono_apikey", "").strip()

    info = []
    if current_key:
        preview = current_key[:6] + "..." + current_key[-4:]
        info.append(kv("API Key", f"{C_CYAN}{preview}{C_RESET}"))
        res = solver.get_balance()
        if res.get("success"):
            info.append(kv("Saldo Token", f"{C_GREEN}{C_BOLD}{res.get('balance')} Token{C_RESET}"))
        else:
            info.append(kv("Status Token", f"{C_RED}{clip(res.get('error'), 34)}{C_RESET}"))
    else:
        info.append(kv("API Key", badge(False)))

    print()
    box("PANEL 2  •  API KEY WARYONO", info, C_YELLOW)
    print(f"\n {C_DIM}Tekan [Enter] kosong jika tidak ingin mengubah.{C_RESET}")

    try:
        new_key = ask("Masukkan API Key baru ›")
    except (EOFError, KeyboardInterrupt):
        return

    if new_key:
        solver.set_apikey(new_key)
        res = solver.get_balance()
        print()
        config["waryono_apikey"] = new_key
        if res.get("success"):
            save_config(config)
            log("ok", f"API Key valid! Sisa token: {C_BOLD}{res.get('balance')}{C_RESET}")
        else:
            save_config(config)
            log("warn", f"API Key disimpan, tapi server berkata: {clip(res.get('error'), 40)}")


def show_account_info(client: CoinPayzClient):
    print()
    log("info", "Mengambil data akun ...")
    res = client.get_dashboard()
    if not res.get("success"):
        log("err", f"Gagal mengambil profil: {res.get('error')}")
        return

    user = res["user"]
    stats = res["stats"]
    dash = res.get("dashboard", {})
    earnings = dash.get("earnings", {})

    print()
    box("👤  PROFIL AKUN", [
        kv("ID Akun", user.get("id")),
        kv("Username", f"{C_BOLD}{user.get('username')}{C_RESET}"),
        kv("Email", clip(user.get("email"), 38)),
        kv("Negara", user.get("country_isocode")),
        kv("Member sejak", str(dash.get("profile", {}).get("member_since", "-"))[:10]),
    ], C_CYAN)
    print()
    box("💰  SALDO & STATISTIK", [
        kv("Saldo Utama", f"{C_GREEN}{C_BOLD}{stats.get('balance')} USD{C_RESET}"),
        kv("Saldo Pembelian", f"{stats.get('purchase_balance')} USD"),
        kv("Reward Points", f"{C_YELLOW}{stats.get('energy')} RP{C_RESET}"),
        kv("Experience (EXP)", stats.get("exp")),
        kv("Faucet hari ini", f"{stats.get('faucet_claims_today')} kali"),
    ], C_GREEN)
    print()
    box("📈  TOTAL PENDAPATAN", [
        kv("Total", f"{C_GREEN}{C_BOLD}{earnings.get('total', '0')} USD{C_RESET}"),
        kv("Dari PTC", f"{earnings.get('ptc', '0')} USD"),
        kv("Dari Faucet", f"{earnings.get('faucet', '0')} USD"),
    ], C_MAGENTA)


# ---------- Smart Auto-Claim ----------
def print_session_summary(stats: dict, client: CoinPayzClient, title: str = "RINGKASAN SESI"):
    lines = [
        kv("Durasi sesi", fmt_duration(time.time() - stats["start"])),
        kv("Siklus selesai", stats["cycles"]),
        kv("Faucet berhasil", f"{C_GREEN}{stats['faucet']}{C_RESET}"),
        kv("PTC berhasil", f"{C_GREEN}{stats['ptc']}{C_RESET}"),
        kv("Challenge klaim", f"{C_GREEN}{stats['tasks']}{C_RESET}"),
        kv("Gagal", f"{C_RED if stats['fail'] else C_DIM}{stats['fail']}{C_RESET}"),
        kv("Estimasi didapat", f"{C_YELLOW}{C_BOLD}+{stats['earned']:.5f} USD{C_RESET}"),
    ]
    try:
        dash = client.get_dashboard()
        if dash.get("success"):
            lines.append(kv(
                "Saldo sekarang",
                f"{C_GREEN}{C_BOLD}{dash['stats'].get('balance')} USD{C_RESET} {C_DIM}|{C_RESET} "
                f"{C_CYAN}{dash['stats'].get('energy')} RP{C_RESET}",
            ))
    except Exception:
        pass
    print()
    box(title, lines, C_MAGENTA)


def run_smart_claim(client: CoinPayzClient):
    print()
    box("⚡  SMART AUTO-CLAIM AKTIF", [
        f"Urutan kerja : {C_BOLD}Challenge → Faucet → PTC Ads{C_RESET} (berulang)",
        f"{C_DIM}Tekan Ctrl+C kapan saja untuk menghentikan.{C_RESET}",
    ], C_MAGENTA)

    stats = {"start": time.time(), "cycles": 0, "faucet": 0, "ptc": 0, "tasks": 0, "fail": 0, "earned": 0.0}
    loop_count = 0

    try:
        while True:
            loop_count += 1
            section(f"SIKLUS #{loop_count}  •  {ts()}")

            # 1. Cek Tantangan Harian (Challenges)
            try:
                ch_data = client.get_challenges()
                if ch_data.get("success") and ch_data.get("claimable"):
                    for ch in ch_data["claimable"]:
                        ch_id = ch["id"]
                        log("info", f"{chip('CHALLENGE', C_YELLOW)} Klaim #{ch_id} (reward {ch['reward']} USD)")
                        res = client.claim_challenge(ch_id)
                        if res.get("success"):
                            stats["tasks"] += 1
                            stats["earned"] += to_float(ch.get("reward"))
                            log("ok", f"Challenge #{ch_id} berhasil diklaim!")
                        else:
                            stats["fail"] += 1
            except Exception:
                pass

            # 2. Periksa Status Faucet
            faucet = client.get_faucet_status()
            if not faucet.get("success"):
                log("err", f"{chip('FAUCET', C_BLUE)} Gagal cek status: {faucet.get('error')}")
                faucet_ready = False
                faucet_limit = False
                cooldown_sec = 60
            else:
                claims_left = faucet["claims_left"]
                cooldown_sec = faucet["cooldown_left_seconds"]
                faucet_ready = faucet["is_ready"]
                faucet_limit = faucet["is_limit_reached"]
                log("info", f"{chip('FAUCET', C_BLUE)} Kuota {faucet['claims_today']}/{faucet['daily_limit']} "
                            f"• sisa {claims_left} • cooldown {cooldown_sec // 60}m {cooldown_sec % 60}d")

            # 3. Eksekusi Faucet jika siap
            if faucet_ready:
                log("ok", f"{chip('FAUCET', C_BLUE)} {C_GREEN}{C_BOLD}Siap!{C_RESET} Menyelesaikan slider ...")
                sol = client.solve_slider_for_page("faucet")
                if sol.get("success"):
                    claim_res = client.claim_faucet(sol["token"], "local_slider")
                    if claim_res.get("success"):
                        stats["faucet"] += 1
                        stats["earned"] += to_float(faucet.get("reward"))
                        log("ok", f"{C_GREEN}{C_BOLD}Faucet berhasil!{C_RESET} +{faucet['reward']} USD")
                        if claim_res.get("message"):
                            print(f"            {C_DIM}{clip(claim_res.get('message'), 50)}{C_RESET}")
                        cooldown_sec = faucet["timer_seconds"]
                    else:
                        stats["fail"] += 1
                        log("err", f"Gagal klaim Faucet: {clip(claim_res.get('error'), 44)}")
                else:
                    stats["fail"] += 1
                    log("err", f"Slider Faucet gagal: {clip(sol.get('error'), 44)}")
            elif faucet_limit:
                log("warn", f"{chip('FAUCET', C_BLUE)} Kuota harian habis → lanjut ke PTC Ads")
            else:
                log("warn", f"{chip('FAUCET', C_BLUE)} Masih cooldown ({cooldown_sec}d) → lanjut ke PTC Ads")

            # 4. Scan & Eksekusi PTC Ads
            ptc = client.get_ptc_ads()
            local_ads = ptc.get("local_ads", []) if ptc.get("success") else []

            if local_ads:
                log("ok", f"{chip('PTC', C_GREEN)} Ditemukan {C_BOLD}{len(local_ads)}{C_RESET} iklan lokal")
                for idx, ad in enumerate(local_ads, 1):
                    ad_hash = ad.get("ad_hash")
                    name = ad.get("name", "Tanpa Judul")
                    timer = int(ad.get("timer", 15))
                    reward = ad.get("reward", "0")

                    print(f"\n   {C_BOLD}Iklan {idx}/{len(local_ads)}{C_RESET}  {clip(name, 24)}  "
                          f"{C_DIM}({timer}d • {reward} USD){C_RESET}")
                    start_res = client.start_ptc_ad(ad_hash)
                    if not start_res.get("success"):
                        stats["fail"] += 1
                        log("err", f"Gagal memulai iklan: {clip(start_res.get('error'), 40)}")
                        continue

                    countdown(timer + 1, "Menonton iklan")

                    sol = client.solve_slider_for_page("ptc")
                    if sol.get("success"):
                        claim_ptc = client.claim_ptc_ad(ad_hash, sol["token"], "local_slider")
                        if claim_ptc.get("success"):
                            stats["ptc"] += 1
                            stats["earned"] += to_float(reward)
                            log("ok", f"{C_GREEN}PTC berhasil!{C_RESET} +{reward} USD")
                        else:
                            stats["fail"] += 1
                            log("err", f"Gagal klaim PTC: {clip(claim_ptc.get('error'), 40)}")
                    else:
                        stats["fail"] += 1
                        log("err", f"Slider PTC gagal: {clip(sol.get('error'), 40)}")

                    time.sleep(2)
            else:
                log("info", f"{chip('PTC', C_GREEN)} {C_DIM}Tidak ada iklan lokal yang belum diklaim{C_RESET}")

            # 5. Cek status akhir siklus & tentukan jeda
            stats["cycles"] += 1
            faucet_after = client.get_faucet_status()
            if faucet_after.get("success"):
                if not faucet_after.get("is_limit_reached"):
                    wait_time = faucet_after.get("cooldown_left_seconds", 30)
                else:
                    wait_time = 120
            else:
                wait_time = 60

            print_session_summary(stats, client)

            if wait_time > 0:
                print()
                log("warn", f"Siklus berikutnya dalam {wait_time} detik  {C_DIM}(Ctrl+C untuk berhenti){C_RESET}")
                countdown(wait_time, "Cooldown")

    except KeyboardInterrupt:
        print(f"\n")
        log("warn", "Auto-Claim dihentikan oleh pengguna.")
        print_session_summary(stats, client, "RINGKASAN AKHIR SESI")


def main():
    config = load_config()
    client = CoinPayzClient(config.get("cookie", ""))
    solver = WaryonoSolver(config.get("waryono_apikey", ""))

    while True:
        print_banner()
        print_menu(config)

        try:
            choice = ask("Pilih menu [0-4] ›")
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if choice == "1":
            panel_input_cookie(config, client)
        elif choice == "2":
            panel_input_waryono(config, solver)
        elif choice == "3":
            show_account_info(client)
        elif choice == "4":
            run_smart_claim(client)
        elif choice == "0":
            break
        else:
            print()
            log("err", "Pilihan tidak valid! Masukkan angka 0 - 4.")

        if not wait_enter():
            break

    print()
    box("", [
        f"{C_GREEN}{C_BOLD}Terima kasih telah memakai {APP_NAME}!{C_RESET}",
        f"{C_DIM}Sampai jumpa lagi 👋{C_RESET}",
    ], C_CYAN)
    credit_line()
    print()


if __name__ == "__main__":
    main()
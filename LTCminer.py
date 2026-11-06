# ==============================================================================
# LTC Miner Telegram Mini App - Smart Auto Claim & Mining Bot
# Versi Pintar: Dynamic Cooldown Scheduler (Tanpa Nunggu Cooldown Kaku)
# Dibuat oleh : BANG MIUN "RCH C12"
# ==============================================================================
import os
import re
import sys
import time
import json
import random
import urllib.parse
from datetime import datetime, timezone

try:
    import requests
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    print("Pustaka belum lengkap. Silakan jalankan: pip install requests colorama")
    sys.exit(1)

CREATOR = 'BANG MIUN "RCH C12"'
VERSION = "2.0"

# Konstanta Supabase & Konfigurasi API LTC Miner
SUPABASE_URL = "https://supabase.ltcminer.xyz"
ANON_KEY = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc4NjcxNzIwMCwiZXhwIjo0OTQyMzkwODAwLCJyb2xlIjoiYW5vbiJ9."
    "sUtI3lKmtdBpXDW4StLp_wtdYzUPOZuGEZuMt2tnWZM"
)

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36 Telegram-Android/11.1.3",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://ltcminer.xyz",
    "Referer": "https://ltcminer.xyz/",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ANON_KEY}",
    "apikey": ANON_KEY
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.txt")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# ==============================================================================
# TAMPILAN (UI HELPERS)
# ==============================================================================

WIDTH = 68
C = Fore
RST = Style.RESET_ALL
BOLD = Style.BRIGHT
DIM = Fore.LIGHTBLACK_EX

# level -> (ikon, warna)
LEVELS = {
    "ok":    ("✔", Fore.LIGHTGREEN_EX),
    "info":  ("●", Fore.LIGHTCYAN_EX),
    "start": ("▶", Fore.LIGHTBLUE_EX),
    "watch": ("◔", Fore.LIGHTMAGENTA_EX),
    "wait":  ("⏳", Fore.LIGHTYELLOW_EX),
    "warn":  ("⚠", Fore.YELLOW),
    "err":   ("✖", Fore.LIGHTRED_EX),
    "done":  ("★", Fore.LIGHTGREEN_EX),
}

TAG_LABEL = {
    "SISTEM": "SISTEM",
    "LOGIN": "LOGIN",
    "DAILY": "DAILY",
    "MEGA": "MEGA POP",
    "POP": "POP ADS",
    "RICHADS": "RICHADS",
    "PREMIUM": "PREMIUM",
    "ADSGRAM": "ADSGRAM",
    "ADSUN": "ADSUN",
    "ADWATCH": "AD WATCH",
    "MINING": "MINING",
    "SPIN": "SPIN",
    "TASKS": "TUGAS",
}


def log(tag, msg, level="info", acct=None):
    """Format log: [JAM] │ ikon  LABEL  │ (akun) pesan"""
    icon, color = LEVELS.get(level, LEVELS["info"])
    ts = datetime.now().strftime("%H:%M:%S")
    label = TAG_LABEL.get(tag, tag)
    acct_txt = f"{C.LIGHTWHITE_EX}[{acct}] " if acct else ""
    print(f"{DIM}{ts} │ {color}{icon} {label:<8}{DIM} │ {acct_txt}{color}{msg}{RST}")


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def fmt_ltc(v) -> str:
    try:
        return f"{float(v):.8f} LTC"
    except Exception:
        return f"{v} LTC"


def fmt_time(sec: int) -> str:
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def bar(cur: int, total: int, size: int = 14) -> str:
    if total <= 0:
        return ""
    cur = min(cur, total)
    filled = int(size * cur / total)
    return "█" * filled + "░" * (size - filled)


def line(char="─", color=Fore.CYAN):
    print(color + char * WIDTH + RST)


def box_top(color=Fore.CYAN):
    print(color + "╔" + "═" * (WIDTH - 2) + "╗" + RST)


def box_bottom(color=Fore.CYAN):
    print(color + "╚" + "═" * (WIDTH - 2) + "╝" + RST)


def box_row(text: str = "", color=Fore.CYAN, text_color=Fore.WHITE, center=False):
    inner = WIDTH - 4
    text = text[:inner]
    pad = text.center(inner) if center else text.ljust(inner)
    print(f"{color}║ {text_color}{pad}{color} ║{RST}")


def section(title: str):
    print()
    print(f"{Fore.LIGHTCYAN_EX}┌─ {BOLD}{title}{RST}{Fore.LIGHTCYAN_EX} " + "─" * max(2, WIDTH - len(title) - 5) + RST)


def print_banner():
    print(Fore.LIGHTCYAN_EX + BOLD + r"""
  _   _____ ___   __  __ _                  ___       _
 | | |_   _/ __| |  \/  (_)_ _  ___ _ _    | _ ) ___ | |_
 | |__ | || (__  | |\/| | | ' \/ -_) '_|   | _ \/ _ \|  _|
 |____||_| \___| |_|  |_|_|_||_\___|_|     |___/\___/ \__|""" + RST)
    box_top(Fore.LIGHTMAGENTA_EX)
    box_row(f"SMART ENGINE v{VERSION}  •  AUTO CLAIM TANPA NUNGGU", Fore.LIGHTMAGENTA_EX, Fore.LIGHTYELLOW_EX, True)
    box_row(f"Dibuat oleh : {CREATOR}", Fore.LIGHTMAGENTA_EX, Fore.LIGHTGREEN_EX, True)
    box_bottom(Fore.LIGHTMAGENTA_EX)


def pause(msg="Tekan Enter untuk kembali ke Menu..."):
    input(f"\n{DIM}{msg}{RST}")


def get_current_utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ==============================================================================
# DATA & KONFIGURASI
# ==============================================================================

def extract_init_data(raw_input: str) -> tuple[str, dict]:
    raw_input = raw_input.strip()
    if not raw_input:
        return "", {}

    if "<iframe" in raw_input:
        src_match = re.search(r'src=["\']([^"\']+)["\']', raw_input)
        if src_match:
            raw_input = src_match.group(1)

    raw_input = raw_input.replace("&amp;", "&")

    if "#" in raw_input:
        fragment = raw_input.split("#", 1)[1]
        params = urllib.parse.parse_qs(fragment)
        if "tgWebAppData" in params:
            raw_input = params["tgWebAppData"][0]
        elif "initData" in params:
            raw_input = params["initData"][0]
        elif "tg_init_data" in params:
            raw_input = params["tg_init_data"][0]
        elif "auth_date=" in fragment:
            raw_input = fragment
    elif "?" in raw_input and "tgWebAppData=" in raw_input:
        query = raw_input.split("?", 1)[1]
        params = urllib.parse.parse_qs(query)
        if "tgWebAppData" in params:
            raw_input = params["tgWebAppData"][0]

    if raw_input.startswith("tgWebAppData="):
        raw_input = raw_input[len("tgWebAppData="):]
        if "&tgWebApp" in raw_input:
            raw_input = raw_input.split("&tgWebApp")[0]

    if raw_input.startswith("query_id%3D") or "%26user%3D" in raw_input or "%26auth_date%3D" in raw_input:
        raw_input = urllib.parse.unquote(raw_input)

    user_info = {}
    try:
        parsed_params = urllib.parse.parse_qs(raw_input)
        if "user" in parsed_params:
            user_str = parsed_params["user"][0]
            if user_str.startswith("%7B") or "%22" in user_str:
                user_str = urllib.parse.unquote(user_str)
            user_info = json.loads(user_str)
    except Exception:
        pass

    return raw_input, user_info


def load_accounts() -> list[str]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    return lines


def save_accounts(accounts: list[str]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("# Daftar initData LTC Miner (1 baris per akun)\n")
        for acc in accounts:
            f.write(acc + "\n")


def load_config() -> dict:
    default_config = {
        "mining_interval_minutes": 10,
        "auto_mining": True,
        "auto_boost": True,
        "auto_daily_streak": True,
        "auto_ad_watch_reward": True,
        "auto_premium_ads": True,
        "auto_richads_rewarded": True,
        "richads_rewarded_count": 15,
        "auto_richads_interstitial": True,
        "richads_interstitial_count": 10,
        "auto_pop_ads": True,
        "pop_ads_count": 5,
        "auto_mega_pop_ads": True,
        "mega_pop_ads_count": 5,
        "auto_adsgram_consume": True,
        "auto_adsun": True,
        "auto_claim_daily_tasks": True,
        "auto_spin": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except Exception:
            pass
    else:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
    return default_config


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# ==============================================================================
# SMART TASK TRACKER
# ==============================================================================

class TaskTracker:
    def __init__(self, key: str, label: str, default_cd: int, is_ad: bool = True, limit: int = 0):
        self.key = key
        self.label = label
        self.default_cd = default_cd
        self.is_ad = is_ad
        self.limit = limit              # target harian (0 = tidak dibatasi / tidak diketahui)
        self.next_available_at = 0.0
        self.is_exhausted = False
        self.disabled = False
        self.success_count = 0
        self.status_text = "Siap Digarap"

    def is_ready(self) -> bool:
        if self.is_exhausted:
            return False
        return time.time() >= self.next_available_at

    def time_remaining(self) -> int:
        if self.is_exhausted:
            return 999999
        return max(0, int(self.next_available_at - time.time()))

    def set_cooldown(self, seconds: int, reason: str = "cooldown"):
        self.next_available_at = time.time() + seconds
        self.status_text = f"Cooldown ({seconds}s)"

    def set_exhausted(self, reason: str = "Limit Hari Ini Habis"):
        self.is_exhausted = True
        self.status_text = f"Selesai ({reason})"

    def set_disabled(self):
        self.disabled = True
        self.is_exhausted = True
        self.status_text = "Dimatikan di pengaturan"

    def set_success(self, cd_after: int = 5, note: str = "Sukses"):
        self.success_count += 1
        self.next_available_at = time.time() + cd_after
        self.status_text = f"Sukses ({self.success_count}x)"

    def progress_text(self) -> str:
        if self.limit:
            return f"{self.success_count}/{self.limit}"
        return f"{self.success_count}x"

    def pretty_status(self) -> str:
        """Status singkat berwarna untuk tabel dashboard."""
        if self.disabled:
            return f"{DIM}— OFF{RST}"
        if self.is_exhausted:
            return f"{Fore.LIGHTGREEN_EX}✔ Selesai{RST}"
        rem = self.time_remaining()
        if rem > 0:
            return f"{Fore.LIGHTYELLOW_EX}⏳ {fmt_time(rem)}{RST}"
        return f"{Fore.LIGHTCYAN_EX}▶ Siap{RST}"


class AccountScheduler:
    def __init__(self, init_data: str, user_info: dict, account_num: int, config: dict):
        self.init_data = init_data
        self.user_info = user_info or {}
        self.account_num = account_num
        self.config = config
        self.telegram_id = self.user_info.get("id")
        self.name = self.user_info.get("first_name") or self.user_info.get("username") or f"ID:{self.telegram_id}"
        self.session = requests.Session()
        self.session.headers.update(HEADERS_BASE)

        self.initial_balance = 0.0
        self.current_balance = 0.0
        self.active_utc_date = get_current_utc_date()

        mining_cd_secs = int(config.get("mining_interval_minutes", 10)) * 60
        self.tasks: dict[str, TaskTracker] = {
            "daily_streak": TaskTracker("daily_streak", "Daily Streak", 86400, is_ad=False),
            "mega_pop_ads": TaskTracker("mega_pop_ads", "Mega Pop Ads", 45, True, config.get("mega_pop_ads_count", 5)),
            "pop_ads": TaskTracker("pop_ads", "Pop Ads", 35, True, config.get("pop_ads_count", 5)),
            "richads_rewarded": TaskTracker("richads_rewarded", "RichAds Rewarded", 25, True, config.get("richads_rewarded_count", 15)),
            "richads_interstitial": TaskTracker("richads_interstitial", "RichAds Interstitial", 20, True, config.get("richads_interstitial_count", 10)),
            "premium_ads": TaskTracker("premium_ads", "Premium Ads (Monetag/GigaPub)", 35, True),
            "adsgram": TaskTracker("adsgram", "Adsgram Mining Reward", 45, True),
            "adsun": TaskTracker("adsun", "AdSun Claims", 25, True),
            "ad_watch": TaskTracker("ad_watch", "Ad Watch Reward", 45, True),
            "mining": TaskTracker("mining", "Mining LTC Harvest", mining_cd_secs, False),
            "lucky_spin": TaskTracker("lucky_spin", "Lucky Spin", 300, False)
        }
        self._apply_disabled()

    # tugas yang dimatikan di config ditandai selesai agar scheduler tidak looping
    TOGGLES = {
        "daily_streak": "auto_daily_streak",
        "mega_pop_ads": "auto_mega_pop_ads",
        "pop_ads": "auto_pop_ads",
        "richads_rewarded": "auto_richads_rewarded",
        "richads_interstitial": "auto_richads_interstitial",
        "premium_ads": "auto_premium_ads",
        "adsgram": "auto_adsgram_consume",
        "adsun": "auto_adsun",
        "ad_watch": "auto_ad_watch_reward",
        "mining": "auto_mining",
        "lucky_spin": "auto_spin",
    }

    def _apply_disabled(self):
        for key, cfg_key in self.TOGGLES.items():
            if not self.config.get(cfg_key, True):
                self.tasks[key].set_disabled()

    def log(self, tag, msg, level="info"):
        log(tag, msg, level, acct=self.name)

    def reset_if_new_day(self):
        today = get_current_utc_date()
        if today != self.active_utc_date:
            print()
            line("═", Fore.LIGHTCYAN_EX)
            log("SISTEM", f"Hari baru (UTC {today}) — semua kuota iklan di-reset!", "info", self.name)
            line("═", Fore.LIGHTCYAN_EX)
            self.active_utc_date = today
            for t in self.tasks.values():
                t.is_exhausted = False
                t.disabled = False
                t.next_available_at = 0.0
                t.success_count = 0
                t.status_text = "Siap Digarap"
            self._apply_disabled()

    def _make_payload(self, extra: dict = None) -> dict:
        payload = {
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        if extra:
            payload.update(extra)
        return payload

    def call_edge_function(self, function_name: str, payload_data: dict = None) -> dict:
        url = f"{SUPABASE_URL}/functions/v1/{function_name}"
        body = self._make_payload(payload_data)
        try:
            res = self.session.post(url, json=body, timeout=25)
            if res.status_code == 429:
                return {"ok": False, "status": 429, "reason": "rate_limit"}
            try:
                return res.json()
            except Exception:
                return {"ok": res.ok, "status": res.status_code, "text": res.text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def call_user_ops(self, action: str, extra: dict = None) -> dict:
        data = {"action": action, "telegram_id": self.telegram_id}
        if extra:
            data.update(extra)
        return self.call_edge_function("user-operations", data)

    def refresh_user_balance(self):
        res = self.call_user_ops("get_user")
        if res and "user" in res:
            bal = float(res["user"].get("balance", 0.0))
            if self.initial_balance == 0.0:
                self.initial_balance = bal
            self.current_balance = bal
            return self.current_balance
        return None

    @property
    def earned(self) -> float:
        return self.current_balance - self.initial_balance

    def are_all_ads_exhausted(self) -> bool:
        return all(t.is_exhausted for t in self.tasks.values() if t.is_ad)

    def get_min_cd_across_tasks(self) -> tuple[int, str]:
        """Cooldown terkecil dari semua tugas yang belum selesai/dimatikan."""
        candidates = [t for t in self.tasks.values() if not t.is_exhausted]
        if not candidates:
            return 60, "Cek hari baru"
        t = min(candidates, key=lambda x: x.time_remaining())
        return t.time_remaining(), t.label

    # ========================== EKSEKUSI TUGAS ==========================

    @staticmethod
    def _is_limit(reason: str) -> bool:
        return str(reason).lower() in ["daily_limit", "limit_reached"]

    def claim_daily_streak(self):
        tracker = self.tasks["daily_streak"]
        self.log("DAILY", "Mengklaim bonus login harian...", "start")
        res = self.call_edge_function("daily-streak-claim", {
            "action": "claim",
            "telegram_id": self.telegram_id,
            "blur_total_ms": random.randint(2500, 4500),
            "elapsed_ms": random.randint(5500, 7500),
            "ad_done": True,
            "require_click": False
        })
        if res.get("ok") or res.get("success"):
            self.log("DAILY", f"Bonus harian berhasil diklaim (+{res.get('reward', 'sukses')})", "ok")
            tracker.set_exhausted("Sudah diklaim hari ini")
        else:
            reason = res.get("reason") or "Sudah diklaim"
            self.log("DAILY", f"Bonus harian: {reason} → dilewati hari ini", "warn")
            tracker.set_exhausted(reason)

    def _pop_style_ad(self, key: str, tag: str, label: str, start_fn: str, claim_fn: str,
                      limit_key: str, limit_default: int, default_cd: int,
                      watch_range: tuple, blur_range: tuple, extra_ms: tuple,
                      default_reward: str) -> bool:
        tracker = self.tasks[key]
        limit = self.config.get(limit_key, limit_default)
        if tracker.success_count >= limit:
            tracker.set_exhausted("Target tercapai")
            self.log(tag, f"{label}: target {limit}/{limit} tercapai", "done")
            return False

        nomor = tracker.success_count + 1
        self.log(tag, f"{label} #{nomor}/{limit} → memulai sesi iklan...", "start")
        start_res = self.call_edge_function(start_fn, {"telegram_id": self.telegram_id})
        session_id = start_res.get("session_id")

        if not session_id:
            reason = start_res.get("reason") or "Limit"
            if self._is_limit(reason):
                tracker.set_exhausted("Limit Harian")
                self.log(tag, f"{label}: kuota harian habis", "done")
            else:
                cd = int(start_res.get("cooldown") or default_cd)
                tracker.set_cooldown(cd, reason)
                self.log(tag, f"{label}: belum bisa ({reason}) → tunggu {cd} detik", "wait")
            return False

        watch_dur = random.randint(*watch_range)
        self.log(tag, f"{label} #{nomor}: menonton iklan {watch_dur} detik...", "watch")
        time.sleep(watch_dur)

        claim_res = self.call_edge_function(claim_fn, {
            "telegram_id": self.telegram_id,
            "session_id": session_id,
            "blur_total_ms": random.randint(*blur_range),
            "elapsed_ms": watch_dur * 1000 + random.randint(*extra_ms),
            "ad_done": True
        })

        if claim_res.get("ok"):
            reward = claim_res.get("reward") or default_reward
            rem = claim_res.get("remaining")
            sisa = f" | sisa kuota: {rem}" if rem is not None else ""
            self.log(tag, f"{label} #{nomor} BERHASIL  +{reward} LTC{sisa}", "ok")
            tracker.set_success(cd_after=5)
            self.refresh_user_balance()
            self.check_ad_tasks()
            return True

        reason = claim_res.get("reason") or "Gagal"
        if self._is_limit(reason):
            tracker.set_exhausted("Limit Harian")
            self.log(tag, f"{label}: kuota harian habis", "done")
        else:
            tracker.set_cooldown(30, reason)
            self.log(tag, f"{label} gagal klaim ({reason}) → coba lagi 30 detik", "warn")
        return False

    def execute_mega_pop_ad(self) -> bool:
        return self._pop_style_ad(
            "mega_pop_ads", "MEGA", "Mega Pop Ad", "mega-pop-ad-start", "mega-pop-ad-claim",
            "mega_pop_ads_count", 5, 45, (16, 20), (8500, 11500), (300, 800), "3.41e-06")

    def execute_pop_ad(self) -> bool:
        return self._pop_style_ad(
            "pop_ads", "POP", "Pop Ad", "pop-ad-start", "pop-ad-claim",
            "pop_ads_count", 5, 35, (15, 18), (4500, 6500), (200, 600), "1.18e-06")

    def _richads(self, key: str, ad_type: str, label: str, limit_key: str, limit_default: int,
                 watch_range: tuple, default_cd: int, default_reward: float) -> bool:
        tracker = self.tasks[key]
        limit = self.config.get(limit_key, limit_default)
        if tracker.success_count >= limit:
            tracker.set_exhausted(f"Target {limit}/{limit} tercapai")
            self.log("RICHADS", f"{label}: target {limit}/{limit} tercapai", "done")
            return False

        watch_time = random.randint(*watch_range)
        nomor = tracker.success_count + 1
        self.log("RICHADS", f"{label} #{nomor}/{limit} → menonton {watch_time} detik...", "watch")
        time.sleep(watch_time)

        res = self.call_edge_function("richads-claim", {
            "telegram_id": self.telegram_id,
            "ad_type": ad_type
        })

        if res.get("ok"):
            reward = res.get("reward") or default_reward
            self.log("RICHADS", f"{label} #{nomor} BERHASIL  +{float(reward):.10f} LTC", "ok")
            tracker.set_success(cd_after=5)
            self.refresh_user_balance()
            self.check_ad_tasks()
            return True

        reason = res.get("reason") or res.get("error") or "Gagal"
        if reason == "daily_limit":
            tracker.set_exhausted(f"Batas {limit}x tercapai")
            self.log("RICHADS", f"{label}: kuota harian habis", "done")
        elif reason == "cooldown":
            cd = int(res.get("cooldown") or default_cd)
            tracker.set_cooldown(cd)
            self.log("RICHADS", f"{label}: masih cooldown → tunggu {cd} detik", "wait")
        else:
            tracker.set_cooldown(default_cd - 5, reason)
            self.log("RICHADS", f"{label} gagal ({reason}) → coba lagi nanti", "warn")
        return False

    def execute_richads_rewarded(self) -> bool:
        return self._richads("richads_rewarded", "rewarded", "RichAds Rewarded",
                             "richads_rewarded_count", 15, (12, 15), 25, 0.0000085)

    def execute_richads_interstitial(self) -> bool:
        return self._richads("richads_interstitial", "interstitial", "RichAds Interstitial",
                             "richads_interstitial_count", 10, (8, 12), 20, 0.0000025)

    def execute_premium_ad(self) -> bool:
        tracker = self.tasks["premium_ads"]
        for provider in ["monetag", "gigapub"]:
            self.log("PREMIUM", f"Premium Ad [{provider.upper()}] → menonton iklan...", "watch")
            time.sleep(random.randint(5, 7))
            res = self.call_user_ops("premium_ad_reward", {"provider": provider})
            if res and res.get("ok"):
                reward = res.get("reward", 0.0)
                self.log("PREMIUM", f"Premium Ad [{provider.upper()}] BERHASIL  +{float(reward):.10f} LTC", "ok")
                tracker.set_success(cd_after=5)
                self.refresh_user_balance()
                self.check_ad_tasks()
                return True
            else:
                reason = (res or {}).get("reason") or "Limit/Cooldown"
                if "limit" in str(reason).lower():
                    tracker.set_exhausted("Limit Harian")
                    self.log("PREMIUM", f"[{provider.upper()}] kuota harian habis", "done")
                else:
                    tracker.set_cooldown(35, reason)
                    self.log("PREMIUM", f"[{provider.upper()}] belum bisa ({reason})", "wait")
        return False

    def execute_adsgram(self) -> bool:
        tracker = self.tasks["adsgram"]
        self.log("ADSGRAM", "Menonton iklan Adsgram...", "watch")
        time.sleep(random.randint(5, 8))
        res = self.call_edge_function("adsgram-mining-consume", {
            "telegram_id": self.telegram_id,
            "block_id": "46507"
        })
        if res.get("ok"):
            self.log("ADSGRAM", "Adsgram Mining Reward BERHASIL", "ok")
            tracker.set_success(cd_after=60)
            self.refresh_user_balance()
            return True
        reason = res.get("reason") or "Cooldown"
        tracker.set_cooldown(45, reason)
        self.log("ADSGRAM", f"Adsgram belum bisa ({reason}) → tunggu 45 detik", "wait")
        return False

    def execute_adsun(self) -> bool:
        tracker = self.tasks["adsun"]
        self.log("ADSUN", "Memulai sesi AdSun...", "start")
        start_res = self.call_edge_function("adsun-start")
        sess = start_res.get("session_id")
        if sess:
            wait_s = random.randint(12, 15)
            self.log("ADSUN", f"Menonton iklan {wait_s} detik...", "watch")
            time.sleep(wait_s)
            claim_res = self.call_edge_function("adsun-claim", {"session_id": sess})
            if claim_res.get("ok"):
                self.log("ADSUN", "AdSun Reward BERHASIL diklaim", "ok")
                tracker.set_success(cd_after=15)
                self.call_edge_function("adsun-task-claim")
                self.refresh_user_balance()
                return True
            reason = claim_res.get("reason") or "Gagal"
            tracker.set_cooldown(20, reason)
            self.log("ADSUN", f"Klaim gagal ({reason}) → coba lagi 20 detik", "warn")
        else:
            reason = start_res.get("reason") or "Batas/Cooldown"
            if "limit" in str(reason).lower():
                tracker.set_exhausted("Limit")
                self.log("ADSUN", "AdSun: kuota harian habis", "done")
            else:
                tracker.set_cooldown(25, reason)
                self.log("ADSUN", f"AdSun belum bisa ({reason}) → tunggu 25 detik", "wait")
        return False

    def execute_ad_watch(self) -> bool:
        tracker = self.tasks["ad_watch"]
        res = self.call_user_ops("ad_watch_reward")
        if res and res.get("ok"):
            reward = res.get("reward") or "LTC"
            self.log("ADWATCH", f"Ad Watch Reward BERHASIL  +{reward}", "ok")
            tracker.set_success(cd_after=10)
            self.refresh_user_balance()
            return True
        reason = (res or {}).get("reason") or "Batas tercapai"
        if "limit" in str(reason).lower() or "tercapai" in str(reason).lower():
            tracker.set_exhausted("Batas Tercapai")
            self.log("ADWATCH", "Ad Watch: kuota harian habis", "done")
        else:
            tracker.set_cooldown(45, reason)
            self.log("ADWATCH", f"Ad Watch belum bisa ({reason}) → tunggu 45 detik", "wait")
        return False

    def execute_mining(self) -> bool:
        tracker = self.tasks["mining"]
        self.log("MINING", "Mengklaim hasil tambang & restart boost...", "start")
        claim_res = self.call_user_ops("claim_mining") or {}
        if claim_res.get("mined") is not None:
            mined = claim_res.get("mined")
            new_bal = claim_res.get("newBalance")
            self.log("MINING", f"Panen BERHASIL  +{mined:.8f} LTC  |  Saldo: {new_bal:.8f} LTC", "ok")
        else:
            self.log("MINING", f"{claim_res.get('message') or 'Mining sedang berjalan'}", "info")

        self.call_user_ops("activate_boost")
        self.call_user_ops("start_mining")

        cd_secs = int(self.config.get("mining_interval_minutes", 10)) * 60
        tracker.set_success(cd_after=cd_secs, note="Mining Aktif")
        self.log("MINING", f"Mining aktif kembali. Panen berikutnya {fmt_time(cd_secs)} lagi", "info")
        self.refresh_user_balance()
        return True

    def execute_spin(self) -> bool:
        tracker = self.tasks["lucky_spin"]
        state_res = self.call_edge_function("spin-state", {"telegram_id": self.telegram_id})
        free_spins = state_res.get("free_spins", 0) if state_res else 0
        if free_spins > 0:
            self.log("SPIN", f"Ada {free_spins} tiket spin gratis → memutar roda!", "start")
            for i in range(free_spins):
                play = self.call_edge_function("spin-play", {
                    "telegram_id": self.telegram_id,
                    "source": "free",
                    "ad_network": "none"
                })
                if play.get("ok"):
                    self.log("SPIN", f"Spin #{i + 1} → hadiah: {play.get('prize') or play.get('reward')}", "ok")
                time.sleep(2)
            tracker.set_success(cd_after=300)
            self.refresh_user_balance()
            return True
        tracker.set_cooldown(600, "Tidak ada tiket")
        return False

    def check_ad_tasks(self):
        if not self.config.get("auto_claim_daily_tasks", True):
            return
        self.call_user_ops("create_daily_ad_tasks")
        for task_type in ["ads_5", "ads_10", "ads_15", "pop_ads", "mega_ads", "watch_ads"]:
            r = self.call_user_ops("claim_daily_ad_task", {"task_type": task_type})
            if r and r.get("ok"):
                self.log("TASKS", f"Tugas harian [{task_type}] selesai & hadiah diklaim!", "done")


# ==============================================================================
# SMART SCHEDULER ENGINE
# ==============================================================================

# Urutan prioritas: (key tugas, nama method)
PRIORITY = [
    ("daily_streak", "claim_daily_streak"),
    ("mega_pop_ads", "execute_mega_pop_ad"),
    ("richads_rewarded", "execute_richads_rewarded"),
    ("pop_ads", "execute_pop_ad"),
    ("richads_interstitial", "execute_richads_interstitial"),
    ("premium_ads", "execute_premium_ad"),
    ("adsun", "execute_adsun"),
    ("adsgram", "execute_adsgram"),
    ("ad_watch", "execute_ad_watch"),
    ("lucky_spin", "execute_spin"),
    ("mining", "execute_mining"),
]


def countdown_smart(seconds: int, status_msg: str, schedulers=None, started=None):
    total = max(1, seconds)
    remaining = seconds
    while remaining > 0:
        earned = sum(s.earned for s in schedulers) if schedulers else 0.0
        elapsed = fmt_time(time.time() - started) if started else "--:--"
        pct = bar(total - remaining, total, 12)
        print(
            f"\r{DIM}⏳ Berikutnya: {C.LIGHTWHITE_EX}{status_msg} {DIM}[{C.LIGHTYELLOW_EX}{pct}{DIM}] "
            f"{C.LIGHTYELLOW_EX}{fmt_time(remaining)}{DIM} │ Profit sesi: {C.LIGHTGREEN_EX}+{earned:.8f}{DIM} │ "
            f"Jalan: {elapsed} │ Ctrl+C=Menu{RST}   ",
            end="", flush=True)
        time.sleep(1)
        remaining -= 1
    print("\r" + " " * 140 + "\r", end="", flush=True)


def print_dashboard(schedulers):
    """Tabel ringkasan semua akun & status tiap tugas."""
    print()
    line("═", Fore.LIGHTCYAN_EX)
    print(f"{BOLD}{C.LIGHTCYAN_EX}  📊 RINGKASAN  {DIM}({datetime.now().strftime('%d %b %Y %H:%M:%S')}){RST}")
    line("═", Fore.LIGHTCYAN_EX)
    for sch in schedulers:
        print(f" {BOLD}{C.LIGHTWHITE_EX}👤 {sch.name}{RST}  {DIM}(ID {sch.telegram_id}){RST}")
        print(f"    💰 Saldo : {C.LIGHTGREEN_EX}{fmt_ltc(sch.current_balance)}{RST}   "
              f"📈 Profit sesi: {C.LIGHTGREEN_EX}+{sch.earned:.8f}{RST}")
        print(f"    {DIM}{'Tugas':<30}{'Progres':<10}Status{RST}")
        for t in sch.tasks.values():
            if t.disabled:
                continue
            print(f"    {t.label:<30}{DIM}{t.progress_text():<10}{RST}{t.pretty_status()}")
        print(DIM + "  " + "┈" * (WIDTH - 4) + RST)


def run_smart_engine():
    clear_screen()
    print_banner()

    accounts_raw = load_accounts()
    if not accounts_raw:
        print(Fore.LIGHTRED_EX + "\n  ✖ File data.txt kosong! Silakan masukkan initData terlebih dahulu (Menu 2).")
        pause()
        return

    config = load_config()
    schedulers: list[AccountScheduler] = []

    section(f"MENYIAPKAN {len(accounts_raw)} AKUN")
    for idx, raw_line in enumerate(accounts_raw, start=1):
        clean_init, user_info = extract_init_data(raw_line)
        if not clean_init:
            continue
        sch = AccountScheduler(clean_init, user_info, idx, config)
        bal = sch.refresh_user_balance()
        if bal is not None:
            log("LOGIN", f"Akun #{idx} terhubung  │  Saldo: {fmt_ltc(bal)}", "ok", sch.name)
            schedulers.append(sch)
        else:
            log("LOGIN", f"Akun #{idx} GAGAL login / token expired → dilewati", "err")

    if not schedulers:
        print(Fore.LIGHTRED_EX + "\n  ✖ Tidak ada akun valid untuk dijalankan.")
        pause("Tekan Enter untuk kembali...")
        return

    print()
    box_top(Fore.LIGHTGREEN_EX)
    box_row("✔ SMART SCHEDULER AKTIF", Fore.LIGHTGREEN_EX, Fore.LIGHTGREEN_EX, True)
    box_row(f"{len(schedulers)} akun berjalan  •  cooldown tercepat digarap duluan", Fore.LIGHTGREEN_EX, Fore.WHITE, True)
    box_row("Tekan Ctrl + C kapan saja untuk kembali ke Menu Utama", Fore.LIGHTGREEN_EX, Fore.LIGHTBLACK_EX, True)
    box_bottom(Fore.LIGHTGREEN_EX)
    print()
    time.sleep(1.5)

    started = time.time()
    last_dash = 0.0
    all_done_notified = False

    try:
        while True:
            for sch in schedulers:
                sch.reset_if_new_day()

            action_executed = False
            for sch in schedulers:
                for key, method in PRIORITY:
                    task = sch.tasks[key]
                    if task.is_ready() and not task.disabled:
                        getattr(sch, method)()
                        action_executed = True
                        break
                if action_executed:
                    break

            if action_executed:
                all_done_notified = False
                time.sleep(random.uniform(2.0, 3.5))
                continue

            # Tidak ada tugas siap → tampilkan ringkasan lalu tunggu cooldown tercepat
            if time.time() - last_dash > 60:
                print_dashboard(schedulers)
                last_dash = time.time()

            all_exhausted = all(sch.are_all_ads_exhausted() for sch in schedulers)
            if all_exhausted and not all_done_notified:
                print()
                box_top(Fore.LIGHTGREEN_EX)
                box_row("★ SEMUA KUOTA IKLAN HARI INI SELESAI", Fore.LIGHTGREEN_EX, Fore.LIGHTGREEN_EX, True)
                box_row("Beralih ke mode MINING HARVEST (panen otomatis)", Fore.LIGHTGREEN_EX, Fore.WHITE, True)
                box_bottom(Fore.LIGHTGREEN_EX)
                all_done_notified = True

            best_wait, best_label = 999999, "Tugas"
            for sch in schedulers:
                rem, lbl = sch.get_min_cd_across_tasks()
                if rem < best_wait:
                    best_wait, best_label = rem, f"{lbl} ({sch.name})"

            countdown_smart(max(1, best_wait), best_label, schedulers, started)

    except KeyboardInterrupt:
        print()
        print_dashboard(schedulers)
        print(Fore.LIGHTYELLOW_EX + "\n  ⚠ Smart Bot dihentikan. Kembali ke Menu Utama...")
        time.sleep(1.5)


# ==============================================================================
# MENU PANEL
# ==============================================================================

def validate_token_online(init_data_str: str, user_info: dict) -> tuple[bool, dict, str]:
    tg_id = user_info.get("id")
    body = {
        "action": "get_user",
        "telegram_id": tg_id,
        "_init_data": init_data_str,
        "_ts": int(time.time() * 1000)
    }
    url = f"{SUPABASE_URL}/functions/v1/user-operations"
    try:
        res = requests.post(url, headers=HEADERS_BASE, json=body, timeout=15)
        data = res.json()
        if res.status_code == 200 and ("user" in data or data.get("ok")):
            return True, data.get("user") or {}, "Valid"
        reason = data.get("reason") or data.get("error") or f"HTTP {res.status_code}"
        return False, {}, str(reason)
    except Exception as e:
        return False, {}, str(e)


def menu_input_init_data():
    clear_screen()
    print_banner()
    box_top()
    box_row("INPUT / GANTI INITDATA TELEGRAM", Fore.CYAN, Fore.LIGHTYELLOW_EX, True)
    box_bottom()
    print(Fore.WHITE + "\n Cara mendapatkan initData yang fresh:")
    print(Fore.LIGHTYELLOW_EX + "  1. Buka https://web.telegram.org lalu buka LTC Miner.")
    print(Fore.LIGHTYELLOW_EX + "  2. Tekan F12 (DevTools) > tab Console.")
    print(Fore.LIGHTYELLOW_EX + "  3. Ketik: " + Fore.LIGHTGREEN_EX + "copy(Telegram.WebApp.initData)" + Fore.LIGHTYELLOW_EX + " lalu Enter.")
    line("─")

    existing = load_accounts()
    print(f" Jumlah akun saat ini: {Fore.LIGHTGREEN_EX}{len(existing)}{RST} akun\n")
    print(f"  {Fore.LIGHTCYAN_EX}[1]{RST} ➕ Tambah akun baru (Append)")
    print(f"  {Fore.LIGHTCYAN_EX}[2]{RST} ♻️  Ganti / timpa semua akun")
    print(f"  {Fore.LIGHTCYAN_EX}[3]{RST} ↩️  Batal / kembali")

    mode = input(f"\n{BOLD}Pilih [1/2/3]: {RST}").strip()
    if mode not in ("1", "2"):
        return

    print(Fore.LIGHTCYAN_EX + "\n Tempelkan (paste) initData Anda di bawah ini:")
    raw_val = input("> ").strip()
    if not raw_val:
        print(Fore.LIGHTRED_EX + " ✖ Input kosong.")
        time.sleep(1.5)
        return

    clean_init, user_info = extract_init_data(raw_val)
    if not clean_init:
        print(Fore.LIGHTRED_EX + " ✖ Format tidak valid.")
        time.sleep(1.5)
        return

    print(DIM + " Memeriksa token ke server...")
    is_valid, user_data, err_reason = validate_token_online(clean_init, user_info)
    name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or user_info.get("username", "Pengguna")
    if is_valid:
        bal = user_data.get("balance", 0.0)
        print(Fore.LIGHTGREEN_EX + f" ✔ TOKEN VALID!  Nama: {name}  |  Saldo: {fmt_ltc(bal)}")
    else:
        print(Fore.LIGHTYELLOW_EX + f" ⚠ Peringatan server: {err_reason}")

    save_confirm = input(f"\n{BOLD}Simpan ke data.txt? (y/n): {RST}").strip().lower()
    if save_confirm == "y":
        if mode == "1":
            existing.append(clean_init)
            save_accounts(existing)
        else:
            save_accounts([clean_init])
        print(Fore.LIGHTGREEN_EX + " ✔ Berhasil disimpan!")
    time.sleep(1.5)


def menu_list_accounts():
    clear_screen()
    print_banner()
    accounts = load_accounts()
    section(f"DAFTAR AKUN TERDAFTAR (Total: {len(accounts)})")
    if not accounts:
        print(Fore.LIGHTYELLOW_EX + "\n  Belum ada akun di data.txt.")
    else:
        print(f"\n  {DIM}{'No':<4}{'Telegram ID':<16}{'Nama'}{RST}")
        for idx, acc in enumerate(accounts, start=1):
            _, u = extract_init_data(acc)
            name = u.get("first_name") or u.get("username") or "-"
            print(f"  {Fore.LIGHTCYAN_EX}{idx:<4}{RST}{str(u.get('id', '-')):<16}{name}")
    pause()


def menu_check_accounts():
    clear_screen()
    print_banner()
    accounts = load_accounts()
    section("CEK VALIDASI & SALDO AKUN (LIVE)")
    if not accounts:
        print(Fore.LIGHTYELLOW_EX + "\n  Belum ada akun.")
    else:
        print()
        for idx, acc in enumerate(accounts, start=1):
            clean_init, u = extract_init_data(acc)
            is_valid, data, reason = validate_token_online(clean_init, u)
            name = u.get("first_name") or u.get("username") or "-"
            if is_valid:
                print(f"  {Fore.LIGHTCYAN_EX}[{idx}]{RST} {name:<20} {Fore.LIGHTGREEN_EX}✔ AKTIF{RST}   Saldo: {Fore.LIGHTGREEN_EX}{fmt_ltc(data.get('balance', 0.0))}{RST}")
            else:
                print(f"  {Fore.LIGHTCYAN_EX}[{idx}]{RST} {name:<20} {Fore.LIGHTRED_EX}✖ EXPIRED{RST} {DIM}({reason}){RST}")
    pause()


def menu_delete_account():
    clear_screen()
    print_banner()
    accounts = load_accounts()
    section("HAPUS AKUN")
    if not accounts:
        print(Fore.LIGHTYELLOW_EX + "\n  data.txt kosong.")
        pause("Tekan Enter...")
        return
    print()
    for idx, acc in enumerate(accounts, start=1):
        _, u = extract_init_data(acc)
        print(f"  {Fore.LIGHTCYAN_EX}[{idx}]{RST} ID: {u.get('id', '-')} - {u.get('first_name', 'User')}")
    print(f"\n  {Fore.LIGHTRED_EX}[A]{RST} Hapus SEMUA   {Fore.LIGHTCYAN_EX}[0]{RST} Kembali")
    p = input(f"\n{BOLD}Pilih nomor: {RST}").strip()
    if p == "0":
        return
    elif p.upper() == "A":
        save_accounts([])
        print(Fore.LIGHTGREEN_EX + " ✔ Semua akun dihapus.")
    else:
        try:
            t_idx = int(p) - 1
            if 0 <= t_idx < len(accounts):
                accounts.pop(t_idx)
                save_accounts(accounts)
                print(Fore.LIGHTGREEN_EX + f" ✔ Akun #{p} dihapus.")
        except Exception:
            pass
    time.sleep(1.5)


def _onoff(v: bool) -> str:
    return f"{Fore.LIGHTGREEN_EX}● ON {RST}" if v else f"{Fore.LIGHTRED_EX}○ OFF{RST}"


def menu_settings():
    cfg = load_config()
    while True:
        clear_screen()
        print_banner()
        box_top()
        box_row("PENGATURAN BOT", Fore.CYAN, Fore.LIGHTYELLOW_EX, True)
        box_bottom()
        print(f"  {Fore.LIGHTCYAN_EX}[1]{RST} Interval Panen Mining     : {Fore.LIGHTYELLOW_EX}{cfg.get('mining_interval_minutes', 10)} menit{RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[2]{RST} Auto Mega Pop Ads         : {_onoff(cfg.get('auto_mega_pop_ads'))} {DIM}target {cfg.get('mega_pop_ads_count', 5)}x{RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[3]{RST} Auto RichAds Rewarded     : {_onoff(cfg.get('auto_richads_rewarded'))} {DIM}target {cfg.get('richads_rewarded_count', 15)}x{RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[4]{RST} Auto Pop Ads              : {_onoff(cfg.get('auto_pop_ads'))} {DIM}target {cfg.get('pop_ads_count', 5)}x{RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[5]{RST} Auto RichAds Interstitial : {_onoff(cfg.get('auto_richads_interstitial'))} {DIM}target {cfg.get('richads_interstitial_count', 10)}x{RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[6]{RST} Auto Premium Ads          : {_onoff(cfg.get('auto_premium_ads'))}")
        print(f"  {Fore.LIGHTCYAN_EX}[7]{RST} Auto AdSun                : {_onoff(cfg.get('auto_adsun'))}")
        print(f"  {Fore.LIGHTCYAN_EX}[8]{RST} Auto Mining Harvest       : {_onoff(cfg.get('auto_mining'))}")
        print(f"  {Fore.LIGHTCYAN_EX}[0]{RST} ↩️  Kembali ke Menu Utama")

        p = input(f"\n{BOLD}Pilih nomor pengaturan [0-8]: {RST}").strip()
        if p == "0":
            break
        elif p == "1":
            v = input(" Masukkan interval menit panen mining (contoh: 10): ").strip()
            if v.isdigit() and int(v) > 0:
                cfg["mining_interval_minutes"] = int(v)
                save_config(cfg)
        else:
            toggles = {
                "2": "auto_mega_pop_ads", "3": "auto_richads_rewarded", "4": "auto_pop_ads",
                "5": "auto_richads_interstitial", "6": "auto_premium_ads",
                "7": "auto_adsun", "8": "auto_mining",
            }
            if p in toggles:
                cfg[toggles[p]] = not cfg.get(toggles[p], True)
                save_config(cfg)


def main():
    while True:
        clear_screen()
        print_banner()
        accounts = load_accounts()
        if accounts:
            status_txt, status_col = f"{len(accounts)} akun terdaftar", Fore.LIGHTGREEN_EX
        else:
            status_txt, status_col = "0 akun (belum diatur)", Fore.LIGHTRED_EX

        print()
        box_top()
        box_row("PANEL KONTROL SMART BOT", Fore.CYAN, Fore.LIGHTYELLOW_EX, True)
        box_row(f"Status: {status_txt}", Fore.CYAN, status_col, True)
        box_bottom()
        print(f"  {Fore.LIGHTCYAN_EX}[1]{RST} 🧠 Jalankan Smart Bot {DIM}(auto gas iklan tanpa cooldown kaku){RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[2]{RST} 🔑 Input / Ganti initData {DIM}(tambah / perbarui akun){RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[3]{RST} 📋 Lihat Daftar Akun")
        print(f"  {Fore.LIGHTCYAN_EX}[4]{RST} 🔍 Cek Validasi & Saldo Akun {DIM}(live check){RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[5]{RST} 🗑️  Hapus Akun")
        print(f"  {Fore.LIGHTCYAN_EX}[6]{RST} ⚙️  Pengaturan Bot {DIM}(config.json){RST}")
        print(f"  {Fore.LIGHTCYAN_EX}[7]{RST} ❌ Keluar")
        line("─")
        print(f"{DIM}  Dibuat oleh {CREATOR}{RST}")

        pilihan = input(f"\n{BOLD}Pilih menu [1-7]: {RST}").strip()

        if pilihan == "1":
            run_smart_engine()
        elif pilihan == "2":
            menu_input_init_data()
        elif pilihan == "3":
            menu_list_accounts()
        elif pilihan == "4":
            menu_check_accounts()
        elif pilihan == "5":
            menu_delete_account()
        elif pilihan == "6":
            menu_settings()
        elif pilihan == "7":
            print(Fore.LIGHTGREEN_EX + f"\n  Terima kasih telah menggunakan bot ini. Sampai jumpa!\n  — {CREATOR}\n")
            sys.exit(0)
        else:
            print(Fore.LIGHTRED_EX + " ✖ Pilihan tidak valid.")
            time.sleep(1)


if __name__ == "__main__":
    main()
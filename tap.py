#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  TAP-COIN AUTOMATION FRAMEWORK (Guru Edition v4.5 - PROVIDER EDITION)║
║  Login/Bypass : Direct-IP + Cookie Login (tanpa Seledroid)           ║
║  Feature      : Multi-Provider Captcha (Waryono / Vernuable)         ║
║  Feature      : Coin Faucet + SurfAds + Future-Tycoon (Play & Earn)  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import re
import socket
import random
from dataclasses import dataclass, asdict, fields
from datetime import datetime

try:
    import requests
except ImportError:
    sys.exit("\n[!] Fatal: 'requests' module missing. Run: pip install requests\n")


# ==============================================================================
# 1. TERMINAL UI & LOGGER
# ==============================================================================
class TerminalUI:
    RESET = "\033[0m"
    @staticmethod
    def _rgb(r, g, b, bold=False) -> str: return f"\033[{1 if bold else 0};38;2;{r};{g};{b}m"
    CYAN, PURPLE, PINK, WHITE, GREY = (0,229,255), (150,80,255), (255,90,200), (235,240,255), (120,130,150)
    GREEN, YELLOW, RED, NEON_YELLOW = (80,255,170), (255,210,90), (255,95,95), (255, 255, 0)
    BRIGHT_BLUE, BRIGHT_ORANGE = (0,191,255), (255,140,0)

    @classmethod
    def clear(cls): os.system('clear' if os.name == 'posix' else 'cls')

    @classmethod
    def show_banner(cls):
        print()
        lines = [
            "███████ █████  ██████     ██████  ██████  ██ ███    ██",
            "   ██   ██  ██ ██  ██    ██      ██    ██ ██ ████   ██",
            "   ██   ██████ ██████    ██      ██    ██ ██ ██ ██  ██",
            "   ██   ██  ██ ██        ██      ██    ██ ██ ██  ██ ██",
            "   ██   ██  ██ ██         ██████  ██████  ██ ██   ████"
        ]
        for ln in lines: print(f"{cls._rgb(0, 191, 255, True)}{ln.center(60)}{cls.RESET}")
        print(f"\n{cls._rgb(255,140,0, True)}" + "Framework by Jendela Semesta REBORN".center(60) + f"{cls.RESET}\n")

    @classmethod
    def log(cls, tag: str, msg: str, extra: str = ""):
        colors = {"INFO": cls.CYAN, " OK ": cls.GREEN, "WARN": cls.YELLOW, "FAIL": cls.RED, "SYS ": cls.PINK}
        color = colors.get(tag, cls.WHITE)
        bar = f"{cls._rgb(*color, True)}▐{cls.RESET}"
        clean_tag = tag.strip()
        print(f"{bar}  {cls._rgb(*color, True)}{clean_tag}{cls.RESET}{bar}  {cls._rgb(*cls.WHITE)}{msg}{cls.RESET} {cls._rgb(*cls.GREY)}{extra}{cls.RESET}")

    @classmethod
    def draw_menu(cls, title: str, items: list):
        BLUE = cls._rgb(*cls.BRIGHT_BLUE, True)
        ORANGE = cls._rgb(*cls.BRIGHT_ORANGE, True)
        max_len = max(len(f"{num}. {text}") for num, text in items)
        inside_width = max_len + 4
        top_text = f"─ {title} "
        right_dashes = "─" * (inside_width - len(top_text))
        print(f"\n{BLUE}  ╭{top_text}{right_dashes}╮{cls.RESET}")
        for num, text in items:
            item_text = f"{num}. {text}"
            padding_right = " " * (max_len - len(item_text) + 2)
            print(f"{BLUE}  │{cls.RESET}  {ORANGE}{item_text}{cls.RESET}{padding_right}{BLUE}│{cls.RESET}")
        print(f"{BLUE}  ╰{'─' * inside_width}╯{cls.RESET}")


# ==============================================================================
# 2. CONFIGURATION MANAGER
# ==============================================================================
@dataclass
class BotConfig:
    cookie: str = ""
    user_agent: str = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36")
    captcha_provider: str = "waryono"    # "waryono" / "vernuable"
    waryono_apikey: str = ""
    vernuable_apikey: str = ""


class Configurator:
    FILE = "tapcoin_core.json"

    @classmethod
    def load(cls) -> BotConfig:
        if os.path.exists(cls.FILE):
            try:
                with open(cls.FILE, "r") as f:
                    raw = json.load(f)
                known = {fl.name for fl in fields(BotConfig)}
                return BotConfig(**{k: v for k, v in raw.items() if k in known})
            except Exception:
                pass
        return BotConfig()

    @classmethod
    def save(cls, cfg: BotConfig):
        with open(cls.FILE, "w") as f:
            json.dump(asdict(cfg), f, indent=4)

    # --- MENU PILIH PROVIDER ---
    @classmethod
    def _prompt_provider(cls, cfg: BotConfig) -> BotConfig:
        current = cfg.captcha_provider or "waryono"
        TerminalUI.draw_menu("PILIH PROVIDER CAPTCHA", [
            ("1", f"Waryono   (api.waryono.my.id){'  ← aktif' if current == 'waryono' else ''}"),
            ("2", f"Vernuable (vernuable.my.id){'  ← aktif' if current == 'vernuable' else ''}"),
        ])
        choice = input(f"  {TerminalUI._rgb(*TerminalUI.YELLOW)}Pilihan › {TerminalUI.RESET}").strip()

        if choice == "2":
            cfg.captcha_provider = "vernuable"
            existing = cfg.vernuable_apikey
            hint = f" [{existing[:8]}…]" if existing else ""
            new_key = input(
                f"  {TerminalUI._rgb(*TerminalUI.YELLOW)}API Key Vernuable{hint} : {TerminalUI.RESET}"
            ).strip()
            if new_key:
                cfg.vernuable_apikey = new_key
        else:
            cfg.captcha_provider = "waryono"
            existing = cfg.waryono_apikey
            hint = f" [{existing[:8]}…]" if existing else ""
            new_key = input(
                f"  {TerminalUI._rgb(*TerminalUI.YELLOW)}API Key Waryono{hint} : {TerminalUI.RESET}"
            ).strip()
            if new_key:
                cfg.waryono_apikey = new_key

        cls.save(cfg)
        return cfg

    # --- LOGIN: INPUT COOKIE ---
    @classmethod
    def _prompt_cookie(cls, cfg: BotConfig) -> BotConfig:
        print(f"\n  {TerminalUI._rgb(*TerminalUI.CYAN)}Paste Cookie dari browser:{TerminalUI.RESET}")
        raw = input(f"  {TerminalUI._rgb(*TerminalUI.YELLOW)}Cookie: {TerminalUI.RESET}").strip()
        # dukung paste cURL (ambil bagian cookie saja)
        m_cookie = re.search(r"cookie:\s*([^'\"]+)", raw.replace("\\", ""), re.I)
        cfg.cookie = m_cookie.group(1).strip() if m_cookie else raw
        if cfg.cookie:
            cls.save(cfg)
        return cfg

    @classmethod
    def setup_interactive(cls) -> BotConfig:
        cfg = cls.load()

        if cfg.cookie:
            print(f"  {TerminalUI._rgb(*TerminalUI.GREY)}Cookie tersimpan (ujungnya: ...{cfg.cookie[-20:]}){TerminalUI.RESET}")
            ans = input(f"  {TerminalUI._rgb(*TerminalUI.WHITE)}Pakai cookie ini? (y/n) [y]: {TerminalUI.RESET}").strip().lower()
            if ans == "n":
                cfg.cookie = ""

        if not cfg.cookie:
            TerminalUI.log("SYS ", "Inisialisasi Login Baru")
            cfg = cls._prompt_cookie(cfg)
            if not cfg.cookie:
                return cfg
            cfg = cls._prompt_provider(cfg)

        return cfg

    @classmethod
    def change_provider(cls, cfg: BotConfig) -> BotConfig:
        TerminalUI.clear(); TerminalUI.show_banner()
        TerminalUI.log("SYS ", f"Provider saat ini: {cfg.captcha_provider.upper()}")
        return cls._prompt_provider(cfg)


# ==============================================================================
# 3. DIRECT-IP BYPASS (menggantikan Stealth Layer / Seledroid)
# ==============================================================================
HOST = "tap-coin.de"

def is_cf_blocked(html: str) -> bool:
    if not html: return False
    markers = ["Just a moment...", "cf-chl", "challenge-platform",
               "Enable JavaScript and cookies to continue", "_cf_chl_opt"]
    return any(m in html for m in markers)


class DirectIP:
    ORIGIN_IP = "185.30.32.143"
    ENABLED = True
    FAIL_LIMIT = 3

    active = False
    fails = 0

    @classmethod
    def _probe(cls):
        try:
            s = socket.create_connection((cls.ORIGIN_IP, 80), timeout=6)
            req = f"HEAD / HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n"
            s.sendall(req.encode())
            s.settimeout(6)
            data = s.recv(1024)
            s.close()
            if not data.startswith(b"HTTP/"): return False, "response bukan HTTP"
            line = data.split(b"\r\n", 1)[0].decode(errors="ignore")
            parts = line.split()
            if len(parts) >= 2:
                code = int(parts[1])
                if code in (200, 201, 301, 302, 303, 403): return True, f"HTTP {code}"
                if code >= 500: return False, f"origin error {code}"
                return True, f"HTTP {code}"
            return True, "HTTP ok"
        except socket.timeout:
            return False, "timeout"
        except Exception as e:
            return False, str(e)

    @classmethod
    def activate(cls):
        if not cls.ENABLED: return
        TerminalUI.log("SYS ", f"Probing origin {cls.ORIGIN_IP}:80...")
        ok, reason = cls._probe()
        if not ok:
            TerminalUI.log("WARN", f"Origin unreachable ({reason}) — Direct-IP off, pakai HTTPS + CF")
            return
        TerminalUI.log(" OK ", f"Origin OK ({reason})")

        import urllib3
        from urllib3.util import connection as _u3_conn
        _orig_create = _u3_conn.create_connection
        origin_ip = cls.ORIGIN_IP

        def _patched_create(address, *args, **kwargs):
            try:
                h, p = address
                if h == HOST and int(p) == 80:
                    return _orig_create((origin_ip, 80), *args, **kwargs)
            except Exception:
                pass
            return _orig_create(address, *args, **kwargs)

        _u3_conn.create_connection = _patched_create
        urllib3.disable_warnings()
        cls.active = True
        TerminalUI.log(" OK ", "⚡ DIRECT-IP ACTIVE")

    @classmethod
    def disable(cls, reason=""):
        if not cls.active: return
        cls.active = False
        cls.fails = 0
        TerminalUI.log("WARN", f"Direct-IP dimatikan ({reason})")


# ==============================================================================
# 4. CAPTCHA SERVICE (MULTI-PROVIDER)
# ==============================================================================
class CaptchaBreaker:
    PROVIDERS = {
        "waryono": {
            "name": "Waryono",
            "base": "https://api.waryono.my.id",
            "in":   "/in.php",
            "res":  "/res.php",
        },
        "vernuable": {
            "name": "Vernuable",
            "base": "https://vernuable.my.id",
            "in":   "/in.php",
            "res":  "/res.php",
        },
    }

    def __init__(self, provider: str, apikey: str):
        provider = (provider or "waryono").lower()
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        if not apikey:
            raise ValueError(f"API Key {provider} kosong. Silakan set via menu 'Ganti Captcha Provider'.")
        self.provider = provider
        self.apikey = apikey
        self.http = requests.Session()

    # --- ROUTER ---
    def solve(self, page_url: str, sitekey: str, method: str) -> str:
        if self.provider == "waryono":
            return self._solve_waryono(page_url, sitekey, method)
        elif self.provider == "vernuable":
            return self._solve_vernuable(page_url, sitekey, method)
        raise Exception(f"Unknown provider: {self.provider}")

    def _spin(self, method, elapsed):
        p = self.PROVIDERS[self.provider]
        sys.stdout.write(
            f"\r  {TerminalUI._rgb(*TerminalUI.GREY)}🔎 {method.upper()} via {p['name']}... ({elapsed}s){TerminalUI.RESET}"
        )
        sys.stdout.flush()

    # --- WARYONO ---
    def _solve_waryono(self, page_url, sitekey, method):
        p = self.PROVIDERS["waryono"]
        try:
            payload = {
                "apikey": self.apikey,
                "methods": method,
                "domain": page_url,
                "sitekey": sitekey,
                "json": 1,
            }
            res = self.http.post(f"{p['base']}{p['in']}", json=payload, timeout=15).json()
            if res.get("status") != 1:
                raise Exception(f"Submit Error: {res}")
            req_id = str(res["request"])

            for elapsed in range(300):
                self._spin(method, elapsed)
                time.sleep(1)
                poll = self.http.get(
                    f"{p['base']}{p['res']}",
                    params={"apikey": self.apikey, "id": req_id, "action": "get", "json": 1},
                    timeout=15,
                ).json()
                if poll.get("status") == 1:
                    sys.stdout.write("\r\033[K")
                    return str(poll["request"])
                if poll.get("request") != "CAPCHA_NOT_READY":
                    raise Exception(f"Unsovable: {poll}")
            raise Exception("Timeout")
        except Exception as e:
            sys.stdout.write("\r\033[K"); raise Exception(str(e))

    # --- VERNUABLE ---
    def _solve_vernuable(self, page_url, sitekey, method):
        p = self.PROVIDERS["vernuable"]
        try:
            payload = {
                "key": self.apikey,
                "method": method,
                "sitekey": sitekey,
                "pageurl": page_url,
                "json": "1",
            }
            res = self.http.post(f"{p['base']}{p['in']}", json=payload, timeout=15).json()
            if res.get("status") != 1:
                raise Exception(f"Submit Error: {res}")
            req_id = str(res["request"])

            for elapsed in range(0, 300, 2):
                self._spin(method, elapsed)
                time.sleep(2)
                poll = self.http.post(
                    f"{p['base']}{p['res']}",
                    data={"key": self.apikey, "action": "get", "id": req_id, "json": "1"},
                    timeout=15,
                ).json()
                if poll.get("status") == 1:
                    sys.stdout.write("\r\033[K")
                    return str(poll.get("request") or poll.get("token"))
                if poll.get("request") != "CAPCHA_NOT_READY":
                    raise Exception(f"Unsovable: {poll}")
            raise Exception("Timeout")
        except Exception as e:
            sys.stdout.write("\r\033[K"); raise Exception(str(e))


# ==============================================================================
# 5. CORE NETWORK CLIENT (COOKIE LOGIN + DIRECT-IP AWARE)
# ==============================================================================
class SessionManager:
    BASE_URL = "https://tap-coin.de"

    def __init__(self, cfg: BotConfig):
        self.cfg = cfg
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": cfg.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        for part in cfg.cookie.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                self.s.cookies.set(k, v, domain=HOST)

    # --- URL / header helpers (direct-IP aware) ---
    def _url(self, path):
        if DirectIP.active:
            return f"http://{HOST}{path}"
        return f"{self.BASE_URL}{path}"

    def _origin(self):
        return f"http://{HOST}" if DirectIP.active else self.BASE_URL

    def _prep_headers(self, method, extra=None):
        h = {"Origin": self._origin(), "Referer": self._origin() + "/user/faucet"}
        h.update(extra or {})
        if DirectIP.active:
            for k in ("Origin", "Referer"):
                if isinstance(h.get(k), str) and h[k].startswith("https://"):
                    h[k] = "http://" + h[k][8:]
            if method.upper() == "POST":
                h.setdefault("X-Requested-With", "XMLHttpRequest")
        return h

    def _force_cookies_insecure(self):
        if not DirectIP.active: return
        for c in list(self.s.cookies):
            try: c.secure = False
            except Exception: pass

    def _strip_cf_cookies_temp(self):
        if not DirectIP.active: return {}
        cf_prefixes = ("cf_clearance", "__cf", "_cf", "cf_chl")
        saved = {}
        for c in list(self.s.cookies):
            try:
                if any(c.name.startswith(p) for p in cf_prefixes):
                    saved[c.name] = (c.value, c.domain, c.path)
                    self.s.cookies.clear(domain=c.domain, path=c.path, name=c.name)
            except Exception: pass
        return saved

    def _restore_cf_cookies(self, saved):
        for name, (val, dom, pth) in (saved or {}).items():
            try: self.s.cookies.set(name, val, domain=dom, path=pth, secure=False)
            except Exception: pass

    # --- Universal request (GET / POST) ---
    def request(self, method: str, path: str, **kwargs):
        headers = self._prep_headers(method, kwargs.pop("headers", None))
        max_retries = 3
        r = None

        for attempt in range(max_retries):
            cf_saved = self._strip_cf_cookies_temp()
            try:
                r = self.s.request(method, self._url(path), headers=headers, timeout=30, **kwargs)
                self._restore_cf_cookies(cf_saved)
                break
            except Exception as e:
                self._restore_cf_cookies(cf_saved)
                if attempt == max_retries - 1:
                    TerminalUI.log("FAIL", f"{method} [{path}] gagal: {e}")
                    return None
                TerminalUI.log("WARN", f"Koneksi putus. Mengulang ({attempt+1}/{max_retries})...")
                time.sleep(3)

        self._force_cookies_insecure()

        if DirectIP.active:
            if r.status_code >= 500 or r.status_code == 403:
                DirectIP.fails += 1
                TerminalUI.log("WARN", f"Origin {r.status_code} [{path}] ({DirectIP.fails}/{DirectIP.FAIL_LIMIT})")
                if DirectIP.fails >= DirectIP.FAIL_LIMIT:
                    DirectIP.disable(f"{DirectIP.FAIL_LIMIT}x {r.status_code}")
            else:
                DirectIP.fails = 0
        return r

    # --- LOGIN CHECK ---
    def check_login(self):
        """Return {'ok': True, 'main': balance} atau {'error': ...}"""
        r = self.request("GET", "/user/dashboard")
        if r is None: return {"error": "fetch_fail"}
        html = r.text
        if is_cf_blocked(html): return {"error": "cf_block"}
        if "Logout" not in html: return {"error": "invalid_cookie"}

        m = re.search(r'Main Balance.*?<h5[^>]*>\s*([\d.,]+)', html, re.DOTALL | re.IGNORECASE)
        return {"ok": True, "main": m.group(1) if m else "0.00"}


# ==============================================================================
# 6. MAIN APPLICATION LOGIC
# ==============================================================================
class TapCoinAutomator:
    def __init__(self, client: SessionManager, solver: CaptchaBreaker):
        self.client = client
        self.solver = solver
        self._tried_boxes = set()
        self._ft_free_day = ""

    def _parse_time(self, t_str: str) -> int:
        try:
            if not t_str or t_str == "00:00": return 0
            p = t_str.split(":")
            return int(p[0]) * 60 + int(p[1])
        except: return 0

    def _csrf(self, html: str):
        m = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)', html)
        if m: return m.group(1)
        for c in self.client.s.cookies:
            if c.name == "csrf_cookie": return c.value
        return None

    def _fetch_live_status(self):
        r = self.client.request("GET", "/user/faucet")
        if r is None: return {"error": "fetch_fail"}
        html = r.text
        if is_cf_blocked(html): return {"error": "cf_block"}
        if "Logout" not in html: return {"error": "invalid_cookie"}

        coin_ready = bool(re.search(r'getfreecoins/claim"[^>]*>\s*<span>\s*Ready To Claim!', html))
        coin_cd = "00:00"
        if not coin_ready:
            m = re.search(r'id=["\']timer1["\']>([\d:]+)<', html)
            if m: coin_cd = m.group(1)

        adcoin_ready = bool(re.search(r'getfreeadcoins/claim"[^>]*>\s*<span>\s*Ready To Claim!', html))
        adcoin_cd = "00:00"
        if not adcoin_ready:
            m = re.search(r'id=["\']timer2["\']>([\d:]+)<', html)
            if m: adcoin_cd = m.group(1)
            else:
                m = re.search(r'getfreeadcoins/claim.*?Claim again in.*?([\d:]+)', html, re.DOTALL)
                if m: adcoin_cd = m.group(1)

        return {"coin_ready": coin_ready, "coin_cd": coin_cd,
                "adcoin_ready": adcoin_ready, "adcoin_cd": adcoin_cd}

    def _execute_claim(self, action: str, method_name: str):
        TerminalUI.log("SYS ", f"Memulai klaim {method_name}...")

        claim_url = f"/user/{action}/claim"
        page = self.client.request("GET", claim_url)
        if page is None or page.status_code != 200:
            TerminalUI.log("FAIL", f"Gagal buka halaman klaim {method_name}")
            return False
        if is_cf_blocked(page.text):
            TerminalUI.log("FAIL", "Terblok Cloudflare saat buka halaman klaim")
            return False

        sitekey = re.search(r'data-sitekey=["\']([^"\']+)', page.text)
        csrf = self._csrf(page.text)
        if not sitekey or not csrf:
            TerminalUI.log("FAIL", "HTML berubah / Cookie mati")
            return False

        sitekey = sitekey.group(1)
        cap_method = "turnstile" if sitekey.startswith("0x4AAAA") else "hcaptcha"

        full_page_url = f"{self.client.BASE_URL}{claim_url}"
        try:
            token = self.solver.solve(full_page_url, sitekey, cap_method)
        except Exception as e:
            TerminalUI.log("FAIL", f"Captcha Gagal: {e}")
            return False

        payload = {
            "csrf_token": csrf,
            "g-recaptcha-response": token,
            "h-captcha-response": token,
            "cf-turnstile-response": token if cap_method == "turnstile" else "",
        }

        claims_before = self.client.s.cookies.get("claims")
        res = self.client.request(
            "POST", f"/user/{action}/verify", data=payload,
            headers={"Referer": full_page_url},
        )
        if res is None:
            TerminalUI.log("FAIL", f"POST klaim {method_name} gagal")
            return False

        claims_after = self.client.s.cookies.get("claims")
        by_cookie = bool(claims_after) and claims_after != claims_before

        is_success = False
        if res.url.endswith("/user/faucet"): is_success = True
        elif "Successful" in res.text or "claims=" in str(res.headers.get("set-cookie", "")): is_success = True
        elif by_cookie: is_success = True

        if is_success:
            TerminalUI.log(" OK ", f"Klaim {method_name} Sukses!")
            return True
        else:
            TerminalUI.log("FAIL", f"Klaim {method_name} Ditolak Server (Cek Log)")
            return False

    # --- SURFADS ---
    def get_surfads(self):
        r = self.client.request("GET", "/user/surfads")
        if r is None: return None
        html = r.text
        if is_cf_blocked(html) or "Logout" not in html: return None

        ads = [{"id": m.group(1), "duration": int(m.group(2))}
               for m in re.finditer(r'openAd\((\d+),\s*(\d+),', html)]
        csrf = self._csrf(html)
        if not ads or not csrf:
            return {"ads": [], "csrf": csrf}
        return {"ads": ads, "csrf": csrf}

    def watch_surfad(self, ad_id, duration, csrf):
        TerminalUI.log("SYS ", f"SurfAds #{ad_id} — {duration}s")
        for i in range(duration, 0, -1):
            sys.stdout.write(
                f"\r  {TerminalUI._rgb(*TerminalUI.CYAN, True)}📺 Ad #{ad_id} — {i}s...{TerminalUI.RESET}   "
            )
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\r\033[K")

        r = self.client.request("POST", f"/user/surfads/claim/{ad_id}", data={"csrf_token": csrf})
        if r is None:
            TerminalUI.log("FAIL", "SurfAds claim POST gagal")
            return None
        try:
            j = r.json()
            if isinstance(j, dict) and j.get("success"):
                return j.get("coins", "?")
            msg = j.get("message") if isinstance(j, dict) else r.text[:120]
            TerminalUI.log("FAIL", f"SurfAds ditolak: {msg}")
            return None
        except Exception as e:
            TerminalUI.log("FAIL", f"SurfAds claim err: {e}")
            return None

    # --- PLAY & EARN ---
    DAILY_NAMES = {"cfreward": "Claim Faucet", "sareward": "Surf Ads"}

    def _swal_text(self, r):
        if r is None: return "tanpa respon"
        m = re.search(r'Swal\.fire\((.{0,200}?)\)', r.text, re.S)
        if m: return re.sub(r"\s+", " ", m.group(1)).strip()
        return f"HTTP {r.status_code}"

    def play_and_earn(self, verbose=False):
        """Claim Daily Rewards + Reward Box yang sudah terbuka di /user/games."""
        path = "/user/games"
        if verbose: TerminalUI.log("SYS ", "Play & Earn: cek reward...")
        r = self.client.request("GET", path)
        if r is None or is_cf_blocked(r.text) or "Logout" not in r.text:
            TerminalUI.log("FAIL", "Gagal buka halaman Play & Earn")
            return 0
        html = r.text
        csrf = self._csrf(html)
        if not csrf:
            TerminalUI.log("FAIL", "CSRF Play & Earn tidak ketemu")
            return 0

        if verbose:
            pts = re.search(r"<span>\s*(\d+)\s*/\s*(\d+)\s*</span>", html)
            if pts: TerminalUI.log("INFO", f"Points: {pts.group(1)}/{pts.group(2)}")

        referer = {"Referer": f"{self.client._origin()}{path}"}
        attempted = 0

        # Daily rewards (form hanya muncul kalau sudah bisa diklaim)
        for key in dict.fromkeys(re.findall(r'name="reward"\s+value="(\w+)"', html)):
            name = self.DAILY_NAMES.get(key, key)
            res = self.client.request("POST", "/user/games/claimDailyReward",
                                      data={"csrf_token": csrf, "reward": key}, headers=referer)
            TerminalUI.log(" OK ", f"Daily reward {name}", self._swal_text(res))
            attempted += 1
            time.sleep(1)

        # Reward box (yang tidak berlabel locked)
        week = datetime.now().isocalendar()[:2]
        pattern = (r'rewarbox_(\d+)"[^>]*>(.*?)'
                   r'(?=<div class="rewardbox rewarbox_|<p><b id="countdown")')
        for m in re.finditer(pattern, html, re.S):
            num, block = m.group(1), m.group(2)
            if "locked.png" in block or 'name="number"' not in block:
                continue
            key = (week, num)
            if key in self._tried_boxes:
                continue
            self._tried_boxes.add(key)
            res = self.client.request("POST", "/user/games/claimReward",
                                      data={"csrf_token": csrf, "number": num}, headers=referer)
            TerminalUI.log(" OK ", f"Reward box #{num}", self._swal_text(res))
            attempted += 1
            time.sleep(1)

        if verbose and attempted == 0:
            TerminalUI.log("INFO", "Belum ada reward yang bisa diklaim")
        return attempted

    # --- FUTURE-TYCOON (Play) ---
    FT = "/user/futuretycoon"
    FT_UPGRADE = True        # upgrade house otomatis kalau tersedia
    FT_BUY_ITEM = 1          # beli di Store pakai money: 1=Coin, 2=Ad-Coin, 0=nonaktif
    FT_STORE_PRICE = 100
    FT_MILESTONES = set(range(10, 101, 10)) | set(range(120, 261, 20)) | {300}

    @staticmethod
    def _to_int(txt, default=0):
        try: return int(float(str(txt).replace(",", "").strip()))
        except Exception: return default

    def _ft_state(self, html):
        def grab(pat):
            m = re.search(pat, html)
            return self._to_int(m.group(1)) if m else 0
        return {
            "dice":   grab(r'id="dicebalance"[^>]*>\s*([\d.,]+)'),
            "money":  grab(r'id="balance"[^>]*>\s*([\d.,]+)'),
            "rounds": grab(r'id="completedrounds">\s*([\d.,]+)'),
            "pos":    grab(r'id="player"[^>]*data-position="(\d+)"'),
            "level":  grab(r'class="b1level">\s*([\d.,]+)'),
        }

    def _ft_open(self):
        r = self.client.request("GET", self.FT)
        if r is None or is_cf_blocked(r.text) or "Logout" not in r.text:
            return None, None
        return r.text, self._csrf(r.text)

    def _ft_json(self, path, params=None):
        r = self.client.request(
            "GET", path, params=params,
            headers={"X-Requested-With": "XMLHttpRequest",
                     "Accept": "application/json, text/javascript, */*; q=0.01",
                     "Referer": f"{self.client._origin()}{self.FT}"},
        )
        if r is None: return None
        try: return r.json()
        except Exception:
            TerminalUI.log("FAIL", f"Respon bukan JSON: {r.text[:80]!r}")
            return None

    def _ft_post(self, action, csrf, extra=None):
        data = {"csrf_token": csrf}
        data.update(extra or {})
        return self.client.request(
            "POST", f"{self.FT}/{action}", data=data,
            headers={"Referer": f"{self.client._origin()}{self.FT}"},
        )

    def _ft_gamebox(self):
        choice = random.choice(["1", "2", "3"])   # 1=batu 2=gunting 3=kertas
        j = self._ft_json(f"{self.FT}/gameBox", params={"choice": choice})
        if not j: return
        res = {0: "Seri", 1: "Menang", 2: "Kalah"}.get(j.get("result"), "?")
        TerminalUI.log("INFO", f"Gamebox (Batu-Gunting-Kertas): {res}", f"reward {j.get('reward')} | money {j.get('balance')}")

    def play_future_tycoon(self, max_rolls=500):
        """Masuk ke /user/futuretycoon lalu roll dadu sampai habis."""
        TerminalUI.log("SYS ", "Masuk Future-Tycoon...")
        html, csrf = self._ft_open()
        if not html or not csrf:
            TerminalUI.log("FAIL", "Gagal buka Future-Tycoon (cookie / CF / CSRF)")
            return
        st = self._ft_state(html)
        TerminalUI.log("INFO", f"Dice {st['dice']} | Money {st['money']} | Rounds {st['rounds']} | House LVL {st['level']}")

        # Dadu gratis harian (x10)
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if self._ft_free_day != today:
            res = self._ft_post("buydice", csrf, {"itemnumber[]": "1"})
            self._ft_free_day = today
            TerminalUI.log("INFO", "Free dice harian", self._swal_text(res))
            html2, csrf2 = self._ft_open()
            if html2:
                st = self._ft_state(html2); csrf = csrf2 or csrf
                TerminalUI.log("INFO", f"Dice sekarang: {st['dice']}")

        dice, pos, rounds = st["dice"], st["pos"], st["rounds"]
        if dice <= 0:
            TerminalUI.log("WARN", "Dice habis. Coba lagi nanti (refresh harian 00:00 UTC).")
            return

        rolls = 0
        while dice > 0 and rolls < max_rolls:
            j = self._ft_json(f"{self.FT}/generateRandomNumber")
            if not j or "randomNumber" not in j:
                TerminalUI.log("FAIL", "Roll gagal / dice habis", str(j)[:80] if j else "")
                break
            rolls += 1
            n = self._to_int(j.get("randomNumber"))
            currency = j.get("currency")
            reward = j.get("reward")
            money = self._to_int(j.get("balance"))
            dice = self._to_int(j.get("dice"), dice - 1)
            if currency == "dice":
                dice += self._to_int(reward)

            wrapped = pos + n > 18
            pos = self._to_int(j.get("newposition"), (pos + n - 1) % 18 + 1)

            TerminalUI.log(" OK ", f"🎲 {n} → {currency} +{reward}", f"| money {money} | dice {dice}")

            if currency == "gamebox":
                self._ft_gamebox()

            if wrapped:
                rounds = self._to_int(j.get("round"), rounds) + 1
                TerminalUI.log("INFO", f"Round selesai: {rounds} (+1 point)")
                if rounds in self.FT_MILESTONES:
                    res = self._ft_post("roundreward", csrf)
                    TerminalUI.log(" OK ", f"Round reward {rounds}", self._swal_text(res))

            spent = False
            if self.FT_UPGRADE and j.get("upgrade") == 1:
                res = self._ft_post("upgrade", csrf)
                TerminalUI.log(" OK ", "Upgrade house", self._swal_text(res))
                spent = True
            if not spent and self.FT_BUY_ITEM and money >= self.FT_STORE_PRICE:
                res = self._ft_post("store", csrf, {"itemnumber[]": str(self.FT_BUY_ITEM)})
                TerminalUI.log(" OK ", f"Store item #{self.FT_BUY_ITEM}", self._swal_text(res))

            time.sleep(2.5)

        TerminalUI.log("INFO", f"Selesai: {rolls} roll | sisa dice {dice}")

    def _get_balance(self):
        try:
            r = self.client.request("GET", "/user/dashboard")
            html = r.text
            c = re.search(r'Main Balance</h4>\s*<h5[^>]*>([^<]+)</h5>', html)
            a = re.search(r'Purchase Balance</h4>\s*<h4[^>]*>([^<]+)<', html)
            p = re.search(r'alt="Power"\s*/>\s*([^<]+)</h4>', html)
            return (c.group(1).strip() if c else "?"), (a.group(1).strip() if a else "?"), (p.group(1).strip() if p else "?")
        except: return "?", "?", "?"

    def execute_loop(self, mode="both"):
        is_just_claimed = False

        while True:
            st = self._fetch_live_status()
            if "error" in st:
                err = st["error"]
                if err == "invalid_cookie":
                    TerminalUI.log("FAIL", "Cookie invalid / expired. Berhenti.")
                    return
                TerminalUI.log("WARN", f"{'Cloudflare block' if err == 'cf_block' else 'Fetch gagal'}. Retry 30 detik...")
                time.sleep(30)
                continue

            c_ready, c_cd = st["coin_ready"], st["coin_cd"]
            a_ready, a_cd = st["adcoin_ready"], st["adcoin_cd"]
            c_bal, a_bal, p_bal = self._get_balance()

            if is_just_claimed:
                color_bal = TerminalUI.GREEN
                color_timer = TerminalUI.GREEN
                is_just_claimed = False
            else:
                color_bal = TerminalUI.NEON_YELLOW
                color_timer = TerminalUI.YELLOW

            print(f"\n {TerminalUI._rgb(*color_bal, True)}Balance: {c_bal} Coin {TerminalUI.RESET}")
            print(f" {TerminalUI._rgb(*color_bal, True)}Ad Coin {a_bal}{TerminalUI.RESET}")
            print(f" {TerminalUI._rgb(*color_bal, True)}Power {p_bal}{TerminalUI.RESET}")

            print(f" {TerminalUI._rgb(*TerminalUI.BRIGHT_ORANGE, True)}---------------------------------------------{TerminalUI.RESET}")

            if mode in ["both", "coin"]:
                if c_ready:
                    c_stat = f"{TerminalUI._rgb(*TerminalUI.GREEN, True)}READY{TerminalUI.RESET}"
                else:
                    c_stat = f"{TerminalUI._rgb(*color_timer, True)}{c_cd}{TerminalUI.RESET}"
                print(f" Timer Coin   : [{c_stat}]")

            if mode in ["both", "adcoin"]:
                if a_ready:
                    a_stat = f"{TerminalUI._rgb(*TerminalUI.GREEN, True)}READY{TerminalUI.RESET}"
                else:
                    a_stat = f"{TerminalUI._rgb(*color_timer, True)}{a_cd}{TerminalUI.RESET}"
                print(f" Timer AdCoin : [{a_stat}]")
            print()

            claimed = False

            if mode in ["both", "coin"] and c_ready:
                self._execute_claim("getfreecoins", "Coin")
                time.sleep(3); claimed = True
            if mode in ["both", "adcoin"] and a_ready:
                self._execute_claim("getfreeadcoins", "AdCoin")
                time.sleep(3); claimed = True

            if claimed:
                is_just_claimed = True
                continue

            # Cooldown: manfaatkan waktu dengan SurfAds
            surf = self.get_surfads()
            if surf and surf.get("ads"):
                ad = surf["ads"][0]
                reward = self.watch_surfad(ad["id"], ad["duration"], surf["csrf"])
                if reward:
                    TerminalUI.log(" OK ", f"SurfAds +{reward} coins (#{ad['id']})")
                    is_just_claimed = True
                    time.sleep(2)
                    continue

            c_sec = self._parse_time(c_cd) if mode in ["both", "coin"] else 999999
            a_sec = self._parse_time(a_cd) if mode in ["both", "adcoin"] else 999999

            wait_time = min(c_sec, a_sec) + 5
            if wait_time >= 999999: wait_time = 60

            TerminalUI.log("WARN", f"Menunggu timer: {wait_time} detik")
            for i in range(wait_time, 0, -1):
                sys.stdout.write(f"\r  {TerminalUI._rgb(*TerminalUI.CYAN, True)}⏱  Cooldown: {i//60:02d}:{i%60:02d}{TerminalUI.RESET} ")
                sys.stdout.flush()
                time.sleep(1)
            print()


# ==============================================================================
# ENTRY POINT
# ==============================================================================
def _active_apikey(cfg: BotConfig) -> str:
    if cfg.captcha_provider == "vernuable":
        return cfg.vernuable_apikey
    return cfg.waryono_apikey


def main():
    TerminalUI.clear()
    TerminalUI.show_banner()

    DirectIP.activate()

    cfg = Configurator.setup_interactive()
    if not cfg.cookie:
        TerminalUI.log("FAIL", "Cookie kosong.")
        return

    # Validasi API key provider aktif
    if not _active_apikey(cfg):
        TerminalUI.log("WARN", f"API Key {cfg.captcha_provider.upper()} belum diisi. Silakan isi sekarang.")
        cfg = Configurator.change_provider(cfg)

    client = SessionManager(cfg)

    # ─── LOGIN (wajib) ───
    res = client.check_login()
    if res.get("ok"):
        TerminalUI.log(" OK ", f"Login berhasil | Balance: {res['main']} Coin")
    elif res["error"] == "invalid_cookie":
        TerminalUI.log("FAIL", "Cookie invalid / expired (pilih Reset Konfigurasi lalu jalankan ulang)")
        return
    elif res["error"] == "cf_block":
        TerminalUI.log("FAIL", "Diblok Cloudflare")
        return
    else:
        TerminalUI.log("FAIL", "Gagal fetch (koneksi)")
        return

    TerminalUI.log("SYS ", f"Captcha Provider aktif: {cfg.captcha_provider.upper()}")

    solver = CaptchaBreaker(cfg.captcha_provider, _active_apikey(cfg))
    bot = TapCoinAutomator(client, solver)

    menu_items = [
        ("1", "Auto Claim (Coin Faucet + SurfAds)"),
        ("2", "Play & Earn (Future-Tycoon)"),
        ("3", "Ganti Captcha Provider"),
        ("4", "Reset Konfigurasi"),
        ("5", "Keluar"),
    ]

    while True:
        TerminalUI.draw_menu("CONTROL PANEL", menu_items)

        try: ch = input("  Pilihan › ").strip()
        except (KeyboardInterrupt, EOFError): print(); return

        if ch == "1":
            try: bot.execute_loop(mode="coin")
            except KeyboardInterrupt: print("\n"); TerminalUI.log("INFO", "Dihentikan.")
        elif ch == "2":
            try: bot.play_future_tycoon()
            except KeyboardInterrupt: print("\n"); TerminalUI.log("INFO", "Dihentikan.")
        elif ch == "3":
            cfg = Configurator.change_provider(cfg)
            if not _active_apikey(cfg):
                TerminalUI.log("FAIL", "API key kosong, provider tidak bisa dipakai.")
                continue
            solver = CaptchaBreaker(cfg.captcha_provider, _active_apikey(cfg))
            bot = TapCoinAutomator(client, solver)
            TerminalUI.log(" OK ", f"Provider diganti ke {cfg.captcha_provider.upper()}")
        elif ch == "4":
            if os.path.exists(Configurator.FILE): os.remove(Configurator.FILE)
            TerminalUI.log("INFO", "Konfigurasi dihapus. Silakan jalankan ulang.")
            return
        elif ch == "5":
            return


if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: sys.exit(0)
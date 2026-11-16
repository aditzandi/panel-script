#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   NOTBUX AUTO WATCH — MULTI-ACCOUNT SOUU EDITION             ║
║   - Login via Nomor HP Telegram (Telethon OTP)               ║
║   - Auto-Generate & Auto-Refresh initData via MTProto        ║
║   - Multi-Account Support (Tambah & Kelola Akun)             ║
║   - Multi-Threading (Semua Akun Jalan Serentak)              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import random
import urllib.parse
import threading
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import init, Fore, Style

from telethon import TelegramClient
from telethon import functions

init(autoreset=True)
urllib3.disable_warnings()

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
API_ID = 38677940
API_HASH = "a9a854cf64e92ccb34512a95cdd35279"
BOT_USERNAME = "notbux_bot"
BOT_URL = "https://notbux.click/"

HOST = "https://notbux.click"
API = f"{HOST}/api"
CONFIG_FILE = "accounts_config.json"
SESSIONS_DIR = "sessions"

AVISO_API = "https://aviso.bz/api/v1"
AVISO_ORIGIN = "https://notbux.click"
AVISO_PLATFORM = "Linux aarch64"

TELEGRAM_UA = (
    "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
    "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"
)

HTTP_MAX_RETRY = 5
HTTP_BACKOFF_BASE = 3
REQUEST_TIMEOUT = 30
AD_WATCH_MIN = 30
AD_WATCH_MAX = 35
HUMAN_PAUSE_MIN = 2
HUMAN_PAUSE_MAX = 5
MAX_EMPTY_CYCLES = 3
MAX_REAUTH = 3

AVISO_FALLBACK_WATCH = 35
AVISO_CD_NO_TASK = 60
AVISO_CD_AUTH_FAIL = 120
AVISO_CD_START_FAIL = 45
AVISO_CD_COMPLETE_FAIL = 30

# Lock for terminal printing
PRINT_LOCK = threading.Lock()

class InitDataExpired(Exception):
    pass

def log(tag, account_label, msg, color=Fore.WHITE):
    ts = datetime.now().strftime("%H:%M:%S")
    with PRINT_LOCK:
        print(f"{Fore.BLACK}{Style.BRIGHT}[{ts}] {Fore.CYAN}[{account_label}] {Style.BRIGHT}{color}[{tag}] {Style.RESET_ALL}{msg}")

def ensure_dirs():
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR, exist_ok=True)

def load_accounts():
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_accounts(accounts):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────
# TELETHON AUTH & INIT_DATA EXTRACTOR
# ─────────────────────────────────────────────────────────────
def get_init_data_for_account(phone):
    """
    Menghubungkan ke session Telethon dan mengambil initData terbaru secara otomatis.
    """
    ensure_dirs()
    session_path = os.path.join(SESSIONS_DIR, f"{phone}.session")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _fetch():
        client = TelegramClient(os.path.join(SESSIONS_DIR, str(phone)), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise Exception("Akun belum login / session tidak valid.")

        bot_entity = await client.get_input_entity(BOT_USERNAME)
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot_entity,
            bot=bot_entity,
            url=BOT_URL,
            platform="android"
        ))
        await client.disconnect()

        full_url = res.url
        parsed = urllib.parse.urlparse(full_url)
        params = urllib.parse.parse_qs(parsed.fragment)
        tg_web_app_data = params.get("tgWebAppData", [None])[0]

        if not tg_web_app_data:
            # Fallback parse query
            params_q = urllib.parse.parse_qs(parsed.query)
            tg_web_app_data = params_q.get("tgWebAppData", [None])[0]

        if not tg_web_app_data:
            # Ambil fragment utuh jika formatnya langsung raw params
            tg_web_app_data = parsed.fragment

        return tg_web_app_data

    try:
        init_data = loop.run_until_complete(_fetch())
        return init_data
    finally:
        loop.close()

def login_new_account():
    ensure_dirs()
    print(f"\n{Fore.CYAN}═══ TAMBAH AKUN TELEGRAM BARU ═══{Style.RESET_ALL}")
    phone = input(f"{Fore.YELLOW}Masukkan Nomor HP (Contoh: +628123456789): {Style.RESET_ALL}").strip()
    if not phone:
        print(f"{Fore.RED}Nomor HP tidak boleh kosong.{Style.RESET_ALL}")
        return

    name = input(f"{Fore.YELLOW}Beri Nama/Label Akun (Contoh: Akun 1): {Style.RESET_ALL}").strip() or phone

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _login():
        client = TelegramClient(os.path.join(SESSIONS_DIR, str(phone)), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input(f"{Fore.GREEN}Masukkan Kode OTP yang dikirim Telegram: {Style.RESET_ALL}").strip()
            try:
                await client.sign_in(phone, code)
            except Exception as e:
                # Cek jika butuh 2FA password
                from telethon.errors import SessionPasswordNeededError
                if isinstance(e, SessionPasswordNeededError):
                    pwd = input(f"{Fore.GREEN}Akun memiliki 2-Step Verification. Masukkan Password: {Style.RESET_ALL}").strip()
                    await client.sign_in(password=pwd)
                else:
                    raise e

        me = await client.get_me()
        user_name = me.first_name or ""
        if me.last_name:
            user_name += f" {me.last_name}"
        if me.username:
            user_name += f" (@{me.username})"

        await client.disconnect()
        return user_name

    try:
        user_name = loop.run_until_complete(_login())
        print(f"{Fore.GREEN}✓ Berhasil Login Telegram: {user_name}{Style.RESET_ALL}")

        # Simpan ke config
        accounts = load_accounts()
        # Periksa duplikasi
        for acc in accounts:
            if acc["phone"] == phone:
                acc["name"] = name
                save_accounts(accounts)
                print(f"{Fore.GREEN}✓ Data akun diperbarui.{Style.RESET_ALL}")
                return

        accounts.append({
            "phone": phone,
            "name": name,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_accounts(accounts)
        print(f"{Fore.GREEN}✓ Akun {name} berhasil disimpan!{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}✖ Gagal login: {e}{Style.RESET_ALL}")
    finally:
        loop.close()
    
    input("\nTekan Enter untuk kembali ke menu...")

# ─────────────────────────────────────────────────────────────
# NOTBUX BOT ENGINE PER ACCOUNT
# ─────────────────────────────────────────────────────────────
def make_session():
    s = requests.Session()
    retry = Retry(total=0, connect=0, read=0, redirect=0, status=0, backoff_factor=0)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

class AccountWorker:
    AD_ORDER = ["adsgram", "monetag", "taskgram", "onclicka", "adexium"]

    def __init__(self, account_info, include_aviso=False, aviso_only=False):
        self.phone = account_info["phone"]
        self.label = account_info.get("name", self.phone)
        self.include_aviso = include_aviso
        self.aviso_only = aviso_only
        
        self.session = make_session()
        self.init_data = None
        self.user_id = "-"
        self.username = "-"
        self.balance = 0
        self.start_balance = 0
        self.session_reward = 0
        self.session_ads = 0
        self.ads = []
        
        self._aviso_keys = None
        self._aviso_identified = False
        self._aviso_session = None
        self.aviso_cooldown = 0.0

    def refresh_init_data(self):
        log("AUTH", self.label, "Mengambil init_data baru via Telethon...", Fore.YELLOW)
        try:
            self.init_data = get_init_data_for_account(self.phone)
            log("AUTH", self.label, "✓ init_data berhasil diperbarui otomatis", Fore.GREEN)
            return True
        except Exception as e:
            log("AUTH", self.label, f"✖ Gagal refresh init_data: {e}", Fore.RED)
            return False

    def _headers(self):
        return {
            "authorization": self.init_data,
            "user-agent": TELEGRAM_UA,
            "accept": "*/*",
            "content-type": "application/json",
            "origin": HOST,
            "referer": f"{HOST}/",
            "x-requested-with": "org.telegram.messenger.web",
            "sec-ch-ua-platform": '"Android"',
            "sec-ch-ua": '"Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            "sec-ch-ua-mobile": "?1",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept-language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _is_transient(self, exc):
        msg = str(exc).lower()
        keys = ['connection aborted', 'connection reset', 'connection refused',
                'read timed out', 'timed out', 'timeout', 'ssl error', 'sslerror',
                'temporary failure', 'remote end closed', 'connection broken',
                'protocolerror', 'protocol error', 'badstatusline', 'bad gateway',
                'service unavailable', 'server disconnected', 'incompleteread']
        return any(k in msg for k in keys)

    def _request_with_retry(self, method, url, headers, body=None):
        last_exc = None
        for attempt in range(1, HTTP_MAX_RETRY + 1):
            try:
                if method == "GET":
                    r = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                else:
                    r = self.session.post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
                return r, None
            except Exception as e:
                last_exc = e
                if not self._is_transient(e):
                    return None, e
                if attempt < HTTP_MAX_RETRY:
                    wait = HTTP_BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 2)
                    log("RETRY", self.label, f"Net retry ({attempt}/{HTTP_MAX_RETRY}) - tunggu {int(wait)}s", Fore.YELLOW)
                    time.sleep(wait)
                else:
                    return None, e
        return None, last_exc

    def _is_auth_error(self, code, body_text):
        if code in (401, 403):
            return True
        if not body_text:
            return False
        low = body_text.lower()
        hints = ['unauthorized', 'invalid init', 'expired', 'forbidden']
        return code != 200 and any(h in low for h in hints)

    def api_get(self, path):
        url = f"{API}{path}"
        r, err = self._request_with_retry("GET", url, self._headers())
        if r is None:
            log("HTTP", self.label, f"GET Err: {str(err)[:40]}", Fore.RED)
            return 0, None, str(err)
        if self._is_auth_error(r.status_code, r.text):
            raise InitDataExpired(f"HTTP {r.status_code}")
        try:
            return r.status_code, r.json(), r.text
        except Exception:
            return r.status_code, {"_raw": r.text[:200]}, r.text

    def api_post(self, path, body=None):
        url = f"{API}{path}"
        data = json.dumps(body) if body is not None else ""
        r, err = self._request_with_retry("POST", url, self._headers(), data)
        if r is None:
            log("HTTP", self.label, f"POST Err: {str(err)[:40]}", Fore.RED)
            return 0, None, str(err)
        if self._is_auth_error(r.status_code, r.text):
            raise InitDataExpired(f"HTTP {r.status_code}")
        try:
            return r.status_code, r.json(), r.text
        except Exception:
            return r.status_code, {"_raw": r.text[:200]}, r.text

    def fetch_user(self):
        code, j, txt = self.api_get("/user/me")
        if code != 200 or not isinstance(j, dict) or j.get("status") != "success":
            return False
        self.user_id = j.get("telegram_id", "-")
        self.username = j.get("username") or j.get("first_name") or "?"
        self.balance = int(j.get("balance", 0))
        log("USER", self.label, f"{self.username} (ID: {self.user_id}) | Saldo: {self.balance} coins", Fore.GREEN)
        return True

    def _normalize_ad(self, a, source):
        aid = a.get("id") or "?"
        name = a.get("name") or a.get("title") or aid
        mx = a.get("maxViews") if a.get("maxViews") is not None else (a.get("max_views") or 0)
        views = a.get("views", 0)
        cd = a.get("cooldown", 0)
        return {
            "id": aid,
            "name": name,
            "reward": a.get("reward", 0),
            "views": int(views) if views is not None else 0,
            "maxViews": int(mx) if mx else 0,
            "cooldown": int(cd) if cd else 0,
            "isWatching": bool(a.get("isWatching", False)),
            "canClaim": bool(a.get("canClaim", False)),
            "source": source,
        }

    def fetch_ads(self):
        merged = {}
        code, j, _ = self.api_get("/earn/data")
        if code == 200 and isinstance(j, dict):
            for a in (j.get("ads", []) or []):
                n = self._normalize_ad(a, "earn")
                merged[n["id"]] = n

        code, j, _ = self.api_get("/tasks/available")
        if code == 200 and isinstance(j, dict):
            for a in (j.get("ads", []) or []):
                n = self._normalize_ad(a, "tasks")
                if n["id"] not in merged:
                    merged[n["id"]] = n

        self.ads = list(merged.values())
        return True

    def watch_ad(self, ad):
        aid = ad.get("id")
        name = ad.get("name") or aid
        reward = ad.get("reward", 0)

        cd = ad.get("cooldown", 0)
        if cd > 0:
            log("CD", self.label, f"{name}: Cooldown {cd}s", Fore.YELLOW)
            time.sleep(min(int(cd), 30))
            return "RETRY"

        log("START", self.label, f"Mulai iklan: {name}...", Fore.CYAN)
        code, j, txt = self.api_post(f"/tasks/ads/{aid}/start", None)
        if code != 200:
            log("START", self.label, f"{name}: Gagal start HTTP {code}", Fore.RED)
            return "FAIL"

        server_duration = 0
        if isinstance(j, dict):
            try:
                server_duration = int(j.get("duration") or 0)
            except Exception:
                server_duration = 0

        duration = (server_duration + 2) if server_duration > 0 else random.randint(AD_WATCH_MIN, AD_WATCH_MAX)
        log("WATCH", self.label, f"Menonton {name} selama {duration}s (+{reward} coins)...", Fore.YELLOW)
        time.sleep(duration)

        log("CLAIM", self.label, f"Claim reward {name}...", Fore.CYAN)
        code, j, txt = self.api_post(f"/tasks/ads/{aid}/claim", None)
        if code != 200:
            log("CLAIM", self.label, f"{name}: Claim gagal HTTP {code}", Fore.RED)
            return "FAIL"

        new_bal = None
        got_reward = reward
        if isinstance(j, dict):
            if "balance" in j:
                new_bal = int(j["balance"])
                got_reward = new_bal - self.balance
                if got_reward < 0: got_reward = reward
            elif j.get("status") == "success":
                new_bal = j.get("balance", self.balance + (reward if isinstance(reward, int) else 0))
                got_reward = j.get("reward", reward)

        if new_bal is not None:
            self.balance = new_bal

        try:
            got_reward_int = int(got_reward)
        except Exception:
            got_reward_int = 0

        self.session_reward += got_reward_int
        self.session_ads += 1
        log("DONE", self.label, f"✓ {name}: +{got_reward_int} coins | Total Saldo: {self.balance}", Fore.GREEN)
        return got_reward_int

    def run(self):
        log("INIT", self.label, "Memulai worker akun...", Fore.CYAN)
        if not self.refresh_init_data():
            log("FAIL", self.label, "Worker batal karena gagal autentikasi.", Fore.RED)
            return

        reauth_attempts = 0
        while reauth_attempts < MAX_REAUTH:
            try:
                if self.fetch_user():
                    break
                else:
                    log("AUTH", self.label, "Fetch user gagal, coba refresh init_data...", Fore.YELLOW)
                    self.refresh_init_data()
                    reauth_attempts += 1
            except InitDataExpired:
                self.refresh_init_data()
                reauth_attempts += 1

        if reauth_attempts >= MAX_REAUTH:
            log("FATAL", self.label, "Gagal konek ke Notbux setelah beberapa percobaan reauth.", Fore.RED)
            return

        self.start_balance = self.balance
        cycle = 0
        empty_cycles = 0

        while True:
            cycle += 1
            log("CYCLE", self.label, f"=== Siklus #{cycle} ===", Fore.MAGENTA)

            try:
                self.fetch_ads()
            except InitDataExpired:
                log("CYCLE", self.label, "init_data expired, auto refreshing...", Fore.YELLOW)
                self.refresh_init_data()
                continue

            ready = []
            for a in self.ads:
                if a.get("id") == "aviso_youtube" and not self.include_aviso:
                    continue
                if a.get("cooldown", 0) > 0:
                    continue
                if a.get("maxViews", 0) and a.get("views", 0) >= a.get("maxViews", 0):
                    continue
                if a.get("isWatching", False):
                    continue
                ready.append(a)

            def sort_key(a):
                try:
                    return self.AD_ORDER.index(a.get("id", ""))
                except ValueError:
                    return 999
            ready.sort(key=sort_key)

            if not ready:
                has_cd = any(
                    a.get("cooldown", 0) > 0
                    for a in self.ads
                    if (a.get("maxViews", 0) == 0 or a.get("views", 0) < a.get("maxViews", 0))
                )
                if has_cd:
                    min_cd = min(
                        (a.get("cooldown", 0) for a in self.ads if a.get("cooldown", 0) > 0),
                        default=60
                    )
                    wait_s = min(int(min_cd) + 2, 90)
                    log("IDLE", self.label, f"Semua iklan cooldown, tunggu {wait_s}s...", Fore.YELLOW)
                    time.sleep(wait_s)
                    continue
                else:
                    empty_cycles += 1
                    if empty_cycles >= MAX_EMPTY_CYCLES:
                        log("DONE", self.label, f"Semua iklan selesai habis. Selesai! (+{self.session_reward} coins)", Fore.GREEN)
                        break
                    log("IDLE", self.label, f"Iklan kosong ({empty_cycles}/{MAX_EMPTY_CYCLES}), menunggu 30s...", Fore.YELLOW)
                    time.sleep(30)
                    continue

            empty_cycles = 0
            for ad in ready:
                try:
                    self.watch_ad(ad)
                except InitDataExpired:
                    log("WATCH", self.label, "Token expired saat nonton, auto refresh...", Fore.YELLOW)
                    self.refresh_init_data()
                    break
                except Exception as e:
                    log("ERR", self.label, f"Error watch ad: {e}", Fore.RED)

                pause = random.randint(HUMAN_PAUSE_MIN, HUMAN_PAUSE_MAX)
                time.sleep(pause)

# ─────────────────────────────────────────────────────────────
# MULTI-THREAD RUNNER
# ─────────────────────────────────────────────────────────────
def run_all_accounts():
    accounts = load_accounts()
    if not accounts:
        print(f"\n{Fore.RED}Belum ada akun yang terdaftar. Tambahkan akun terlebih dahulu di Menu [1]!{Style.RESET_ALL}")
        time.sleep(2)
        return

    print(f"\n{Fore.CYAN}═══ MENJALANKAN {len(accounts)} AKUN SECARA SERENTAK ═══{Style.RESET_ALL}\n")
    
    threads = []
    for acc in accounts:
        worker = AccountWorker(acc, include_aviso=False)
        t = threading.Thread(target=worker.run, daemon=True)
        threads.append(t)
        t.start()
        time.sleep(1) # Delay 1 detik per akun saat start agar tidak menabrak connection limit

    for t in threads:
        t.join()

    print(f"\n{Fore.GREEN}✓ Semua akun telah selesai bekerja.{Style.RESET_ALL}")
    input("\nTekan Enter untuk kembali ke menu...")

def list_accounts():
    accounts = load_accounts()
    print(f"\n{Fore.CYAN}═══ DAFTAR AKUN TELEGRAM ═══{Style.RESET_ALL}")
    if not accounts:
        print(f"{Fore.YELLOW}Belum ada akun yang terdaftar.{Style.RESET_ALL}")
    else:
        for idx, acc in enumerate(accounts, 1):
            sess_file = os.path.join(SESSIONS_DIR, f"{acc['phone']}.session")
            status = f"{Fore.GREEN}Ready" if os.path.exists(sess_file) else f"{Fore.RED}No Session"
            print(f"[{idx}] {acc['name']} ({acc['phone']}) - Status: {status}{Style.RESET_ALL}")
    print()
    input("Tekan Enter untuk kembali ke menu...")

# ─────────────────────────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────────────────────────
def main_menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.CYAN}╔════════════════════════════════════════════════════════════╗")
        print(f"║     {Fore.GREEN}{Style.BRIGHT}NOTBUX AUTO WATCH — MULTI-ACCOUNT SOUU EDITION{Fore.CYAN}         ║")
        print(f"║     {Style.DIM}Auto-Login Telethon • Auto-Generate initData • Parallel{Fore.CYAN}║")
        print(f"╠════════════════════════════════════════════════════════════╣")
        print(f"║  {Fore.GREEN}[1]{Fore.WHITE} Tambah Akun Baru (Login via Nomor HP & OTP)          ║")
        print(f"║  {Fore.GREEN}[2]{Fore.WHITE} Jalankan SEMUA Akun Serentak (Parallel)               ║")
        print(f"║  {Fore.GREEN}[3]{Fore.WHITE} Lihat Daftar Akun Terdaftar                           ║")
        print(f"║  {Fore.RED}[0]{Fore.WHITE} Keluar                                                ║")
        print(f"╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
        
        choice = input(f"{Fore.CYAN}Pilih menu (0-3): {Style.RESET_ALL}").strip()
        if choice == "1":
            login_new_account()
        elif choice == "2":
            run_all_accounts()
        elif choice == "3":
            list_accounts()
        elif choice == "0":
            print(f"\n{Fore.YELLOW}Sampai jumpa!{Style.RESET_ALL}\n")
            sys.exit(0)

if __name__ == "__main__":
    main_menu()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   DIATON AUTO FARMER — MULTI-ACCOUNT 24/7 EDITION            ║
║   - Login via Nomor HP Telegram (Telethon OTP)               ║
║   - Auto-Generate & Auto-Refresh initData via MTProto        ║
║   - Multi-Account Support (Tambah & Kelola Akun)             ║
║   - Multi-Threading (Semua Akun Jalan Serentak / Parallel)   ║
║   - Auto 24 Jam Loop (Smart Cooldown & Auto Reset Harian)    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import random
import re
import urllib.parse
import threading
import asyncio
from datetime import datetime

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
BOT_USERNAME = "diaton_bot"
BOT_URL = "https://diaton.biz/"

BASE_HOST = "https://diaton.biz"
UA = (
    "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
    "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"
)

PROVIDERS = [
    "adsgram", "monetag", "adexium", "onclicka",
    "gigapub", "tads_fullscreen", "tads_static",
]

AD_DELAY_MIN = 2.5
AD_DELAY_MAX = 5.0
MAX_ROUNDS   = 40
DEFAULT_CD   = 60
MAX_WAIT     = 3600
MAX_REAUTH   = 3

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE  = os.path.join(SCRIPT_DIR, "accounts_config.json")
SESSIONS_DIR = os.path.join(SCRIPT_DIR, "sessions")

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
            params_q = urllib.parse.parse_qs(parsed.query)
            tg_web_app_data = params_q.get("tgWebAppData", [None])[0]

        if not tg_web_app_data:
            tg_web_app_data = parsed.fragment

        return tg_web_app_data

    try:
        return loop.run_until_complete(_fetch())
    finally:
        loop.close()

def login_new_account():
    ensure_dirs()
    print(f"\n{Fore.CYAN}═══ TAMBAH AKUN TELEGRAM BARU (DIATON) ═══{Style.RESET_ALL}")
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

        accounts = load_accounts()
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
# COOLDOWN DETECTION
# ─────────────────────────────────────────────────────────────
def detect_cd(response):
    if not response or not isinstance(response, dict):
        return None

    for key in ('retry_after', 'cooldown', 'cooldown_seconds', 'wait', 'wait_seconds',
                'reset_in', 'reset_after', 'next_in'):
        v = response.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return int(v)

    for key in ('next_at', 'next_available', 'reset_at'):
        v = response.get(key)
        if isinstance(v, (int, float)) and v > time.time():
            return int(v - time.time())
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                delta = dt.timestamp() - time.time()
                if delta > 0:
                    return int(delta)
            except Exception:
                pass

    for sub in ('data', 'error', 'detail'):
        if isinstance(response.get(sub), dict):
            r = detect_cd(response[sub])
            if r:
                return r

    msg = str(response.get('message') or response.get('detail')
              or response.get('error') or '')
    if msg:
        m = re.search(r'(\d+)\s*(?:sec|second|s\b)', msg.lower())
        if m:
            return int(m.group(1))
        m = re.search(r'(\d+)\s*(?:minute|min\b)', msg.lower())
        if m:
            return int(m.group(1)) * 60

    return None

def classify_err(err_low):
    if any(k in err_low for k in ('cooldown', 'wait', 'rate', 'too soon', 'too_soon')):
        return 'cooldown'
    if any(k in err_low for k in ('limit', 'daily', 'exceeded', 'max', 'quota')):
        return 'limit'
    if any(k in err_low for k in ('invalid ad provider', 'webhook', 'not found', 'unknown provider')):
        return 'invalid'
    return 'generic'

# ─────────────────────────────────────────────────────────────
# DIATON WORKER PER ACCOUNT
# ─────────────────────────────────────────────────────────────
def make_session():
    s = requests.Session()
    retry = Retry(total=0, connect=0, read=0, redirect=0, status=0, backoff_factor=0)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

class DiaTonWorker:
    def __init__(self, account_info):
        self.phone = account_info["phone"]
        self.label = account_info.get("name", self.phone)
        self.session = make_session()
        self.init_data = None
        
        self.tg_id = 0
        self.name = "-"
        self.username = "-"
        self.balance_dton = 0
        self.balance_gram = 0.0
        self.session_earned = 0
        self.ads_done = 0
        self.ads_failed = 0

    def refresh_init_data(self):
        log("AUTH", self.label, "Mengambil initData baru via Telethon...", Fore.YELLOW)
        try:
            self.init_data = get_init_data_for_account(self.phone)
            log("AUTH", self.label, "✓ initData berhasil diperbarui otomatis", Fore.GREEN)
            return True
        except Exception as e:
            log("AUTH", self.label, f"✖ Gagal refresh initData: {e}", Fore.RED)
            return False

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.init_data}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE_HOST,
            "Referer": f"{BASE_HOST}/",
            "X-Requested-With": "org.telegram.messenger.web",
            "User-Agent": UA,
            "Accept-Language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _req(self, method, path, payload=None, timeout=30):
        url = f"{BASE_HOST}{path}"
        for attempt in range(3):
            try:
                if method == "GET":
                    r = self.session.get(url, headers=self._headers(), timeout=timeout, verify=False)
                else:
                    r = self.session.post(url, json=payload or {}, headers=self._headers(),
                                          timeout=timeout, verify=False)

                if r.status_code in (401, 403):
                    raise InitDataExpired(f"HTTP {r.status_code}")

                try:
                    return r.json()
                except Exception:
                    return {"_raw": r.text, "_status": r.status_code}
            except InitDataExpired:
                raise
            except requests.RequestException as e:
                if attempt == 2:
                    log("HTTP", self.label, f"Request error {path}: {e}", Fore.RED)
                    return None
                time.sleep(1.5 * (attempt + 1))
        return None

    def api_me(self):
        return self._req("GET", "/api/user/me")

    def api_earn_info(self):
        return self._req("GET", "/api/earn/info")

    def api_ad_view(self, prov):
        return self._req("POST", "/api/earn/ad-view", {"provider": prov})

    def fetch_user(self):
        me = self.api_me()
        if not me or not isinstance(me, dict) or 'id' not in me:
            return False
        self.tg_id = int(me['id'])
        self.name = me.get('first_name', '?')
        self.username = me.get('username', '') or '-'
        self.balance_dton = int(me.get('balance_dton', 0))
        self.balance_gram = float(me.get('ad_balance_gram', 0.0))
        log("USER", self.label, f"{self.name} (@{self.username}) | Saldo: {self.balance_dton} DTON ({self.balance_gram:.4f} GRAM)", Fore.GREEN)
        return True

    def run_one_round(self):
        ei = self.api_earn_info() or {}
        ads_left_raw = ei.get('ads_left', {}) or {}
        reward = int(ei.get('config', {}).get('ad_reward', 10))

        ads_left = {p: int(ads_left_raw.get(p, 0)) for p in PROVIDERS if p in ads_left_raw}
        total_left = sum(ads_left.values())
        log("INFO", self.label, f"Tersedia {total_left} iklan (Reward: {reward} DTON/ad)", Fore.CYAN)

        if total_left == 0:
            return {'all_limit': True, 'cd_seconds': 0}

        skipped = set()
        round_num = 0
        max_cd = 0

        while round_num < MAX_ROUNDS:
            round_num += 1
            active = [p for p, left in ads_left.items() if left > 0 and p not in skipped]
            if not active:
                break

            random.shuffle(active)
            anyone_progress = False

            for prov in active:
                left = ads_left.get(prov, 0)
                if left <= 0 or prov in skipped:
                    continue

                r = self.api_ad_view(prov)

                if r and r.get('status') == 'success':
                    got = int(r.get('reward', reward))
                    left = int(r.get('left', left - 1))
                    ads_left[prov] = left
                    self.ads_done += 1
                    self.session_earned += got
                    self.balance_dton += got
                    log("AD", self.label, f"✓ {prov}: +{got} DTON (sisa {left}) | Saldo: {self.balance_dton} DTON", Fore.GREEN)
                    anyone_progress = True
                else:
                    err = ((r or {}).get('message')
                           or (r or {}).get('detail')
                           or (r or {}).get('error')
                           or str(r))
                    err_low = str(err).lower()
                    cat = classify_err(err_low)

                    if cat == 'cooldown':
                        cd = detect_cd(r) or DEFAULT_CD
                        if cd > max_cd:
                            max_cd = cd
                        log("CD", self.label, f"{prov} Cooldown {cd}s — lewati sementara", Fore.YELLOW)
                        self.ads_failed += 1
                        continue

                    if cat == 'limit':
                        log("LIMIT", self.label, f"{prov} Kuota harian habis — lewati", Fore.BLUE)
                        ads_left[prov] = 0
                        skipped.add(prov)
                        continue

                    if cat == 'invalid':
                        log("WARN", self.label, f"{prov} Provider tidak valid/nonaktif", Fore.MAGENTA)
                        ads_left[prov] = 0
                        skipped.add(prov)
                        continue

                    self.ads_failed += 1
                    log("ERR", self.label, f"{prov} Gagal: {str(err)[:40]}", Fore.RED)

                delay = random.uniform(AD_DELAY_MIN, AD_DELAY_MAX)
                time.sleep(delay)

            if not anyone_progress:
                break

        # Refresh saldo terbaru
        try:
            self.fetch_user()
        except Exception:
            pass

        remaining = sum(v for k, v in ads_left.items() if k not in skipped)
        return {
            'all_limit': (remaining == 0 and total_left > 0),
            'cd_seconds': max_cd
        }

    def run_24h(self):
        log("INIT", self.label, "Memulai worker 24 Jam...", Fore.CYAN)
        if not self.refresh_init_data():
            log("FAIL", self.label, "Worker batal karena gagal autentikasi.", Fore.RED)
            return

        reauth_attempts = 0
        while reauth_attempts < MAX_REAUTH:
            try:
                if self.fetch_user():
                    break
                else:
                    log("AUTH", self.label, "Fetch user gagal, coba refresh...", Fore.YELLOW)
                    self.refresh_init_data()
                    reauth_attempts += 1
            except InitDataExpired:
                self.refresh_init_data()
                reauth_attempts += 1

        if reauth_attempts >= MAX_REAUTH:
            log("FATAL", self.label, "Gagal konek ke DiaTON setelah beberapa percobaan reauth.", Fore.RED)
            return

        cycle = 0
        while True:
            cycle += 1
            log("CYCLE", self.label, f"=== Siklus Farming #{cycle} ===", Fore.MAGENTA)

            try:
                res = self.run_one_round()
            except InitDataExpired:
                log("CYCLE", self.label, "initData expired mid-run, auto refreshing...", Fore.YELLOW)
                self.refresh_init_data()
                continue
            except Exception as e:
                log("ERR", self.label, f"Error dalam siklus: {e}", Fore.RED)
                time.sleep(10)
                continue

            # Jika semua kuota provider iklan habis untuk hari ini
            if res.get('all_limit'):
                # Tidur 1 jam (3600 detik) lalu cek lagi, agar bekerja 24 jam non-stop
                log("SLEEP", self.label, "Semua provider iklan limit harian. Standby 1 jam sebelum cek reset...", Fore.YELLOW)
                time.sleep(3600)
                continue

            # Jika terdeteksi cooldown provider
            cd = res.get('cd_seconds') or 0
            if cd > 0:
                wait_s = min(cd, MAX_WAIT)
                log("WAIT", self.label, f"Menunggu cooldown terdeteksi: {wait_s}s...", Fore.YELLOW)
                time.sleep(wait_s)
                continue

            # Jika tidak ada CD spesifik, jeda normal 60 detik sebelum siklus berikutnya
            log("WAIT", self.label, f"Siklus selesai. Standby {DEFAULT_CD}s...", Fore.CYAN)
            time.sleep(DEFAULT_CD)

# ─────────────────────────────────────────────────────────────
# MULTI-THREAD RUNNER
# ─────────────────────────────────────────────────────────────
def run_all_accounts():
    accounts = load_accounts()
    if not accounts:
        print(f"\n{Fore.RED}Belum ada akun yang terdaftar. Tambahkan akun di Menu [1]!{Style.RESET_ALL}")
        time.sleep(2)
        return

    print(f"\n{Fore.CYAN}═══ MENJALANKAN {len(accounts)} AKUN DIATON 24 JAM SERENTAK ═══{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}Semua akun akan berjalan di background multi-threading.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Tekan Ctrl+C kapan saja untuk menghentikan program.{Style.RESET_ALL}\n")

    threads = []
    for acc in accounts:
        worker = DiaTonWorker(acc)
        t = threading.Thread(target=worker.run_24h, daemon=True)
        threads.append(t)
        t.start()
        time.sleep(1.5) # Delay saat start agar request initial tidak bentrok

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}! Bot dihentikan oleh pengguna.{Style.RESET_ALL}\n")

def list_accounts():
    accounts = load_accounts()
    print(f"\n{Fore.CYAN}═══ DAFTAR AKUN TELEGRAM DIATON ═══{Style.RESET_ALL}")
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
        print(f"║     {Fore.GREEN}{Style.BRIGHT}DIATON AUTO FARMER — MULTI-ACCOUNT 24/7 EDITION{Fore.CYAN}        ║")
        print(f"║     {Style.DIM}Auto-Login Telethon • Auto initData • 24H Nonstop Loop {Fore.CYAN}║")
        print(f"╠════════════════════════════════════════════════════════════╣")
        print(f"║  {Fore.GREEN}[1]{Fore.WHITE} Tambah Akun Baru (Login via Nomor HP & OTP)          ║")
        print(f"║  {Fore.GREEN}[2]{Fore.WHITE} Jalankan SEMUA Akun Serentak 24 Jam (Parallel)        ║")
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

import os
import sys
import json
import time
import base64
import asyncio
import urllib.parse
from datetime import datetime
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = BLUE = WHITE = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

try:
    from telethon import TelegramClient, functions
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.errors import (
        SessionPasswordNeededError,
        PhoneCodeInvalidError,
        FloodWaitError,
    )
except ImportError:
    print("[ERROR] Telethon belum terinstall. Jalankan: pip install telethon")
    sys.exit(1)

# ==================== KONFIGURASI ====================
API_ID = 38677940
API_HASH = "a9a854cf64e92ccb34512a95cdd35279"
BOT_USERNAME = "TonEdge_play_bot"
BOT_URL = "https://t.me/TonEdge_play_bot/playearn?startapp=TEP81345MGK"
API_BASE = "https://gram-edge-farm.onrender.com/api"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "active_account.json")
SESSION_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

SHARED_SESSION_DIR = r"C:\Users\bismillah\.gemini\antigravity\scratch\notbux_multi\sessions"

def get_session_path(phone: str) -> str:
    shared_path = os.path.join(SHARED_SESSION_DIR, phone)
    if os.path.exists(shared_path + ".session"):
        return shared_path
    return os.path.join(SESSION_DIR, phone)

def log(tag, msg, color=Fore.WHITE):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{tag}] {color}{msg}{Style.RESET_ALL}")

def load_active_account():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    old_cfg = r"C:\Users\bismillah\.gemini\antigravity\scratch\notbux_multi\accounts_config.json"
    if os.path.exists(old_cfg):
        try:
            with open(old_cfg, "r") as f:
                accs = json.load(f)
                if accs:
                    return accs[0]
        except Exception:
            pass
    return None

def save_active_account(account):
    with open(CONFIG_FILE, "w") as f:
        json.dump(account, f, indent=2)

def extract_tgWebAppData(raw_url: str) -> str:
    parsed = urllib.parse.urlparse(raw_url)
    fragment = parsed.fragment
    params = urllib.parse.parse_qs(fragment)
    return params.get("tgWebAppData", [""])[0]

async def fetch_init_data(phone: str) -> tuple:
    session_file = get_session_path(phone)
    client = TelegramClient(session_file, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return None, None

    me = await client.get_me()
    telegram_id = me.id

    try:
        bot_entity = await client.get_input_entity(BOT_USERNAME)
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot_entity,
            bot=bot_entity,
            url=BOT_URL,
            platform="android"
        ))
        init_data = extract_tgWebAppData(res.url)
        await client.disconnect()
        return init_data, telegram_id
    except Exception as e:
        await client.disconnect()
        return None, None

async def join_telegram_channel(phone: str, link: str) -> bool:
    if not link or "t.me/" not in link:
        return False
    channel_name = link.split("t.me/")[-1].split("?")[0].replace("+", "").strip("/")
    if not channel_name or "bot" in channel_name.lower():
        return False
    session_file = get_session_path(phone)
    client = TelegramClient(session_file, API_ID, API_HASH)
    await client.connect()
    try:
        await client(JoinChannelRequest(channel_name))
        await client.disconnect()
        return True
    except Exception:
        await client.disconnect()
        return False

class GramEdgeBot:
    def __init__(self, account: dict):
        self.phone = account.get("phone", "")
        self.name = account.get("name", self.phone)
        self.init_data = account.get("init_data", "")
        self.telegram_id = None
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Origin": "https://ton-edge-play.vercel.app",
            "Referer": "https://ton-edge-play.vercel.app/"
        }
        self.running = True

    def refresh_auth(self):
        log("AUTH", "Mengambil initData baru via Telethon...", Fore.CYAN)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        new_data, tg_id = loop.run_until_complete(fetch_init_data(self.phone))
        loop.close()
        if new_data:
            self.init_data = new_data
            self.telegram_id = tg_id
            log("AUTH", f"✓ initData berhasil diperbarui (ID: {tg_id})", Fore.GREEN)
            return True
        else:
            log("AUTH", "✖ Gagal memperbarui initData via Telethon", Fore.RED)
            return False

    def solve_captcha(self) -> bool:
        """Menyelesaikan Human Check Captcha secara otomatis."""
        try:
            log("CAPTCHA", "Mendeteksi Human Check! Mengambil challenge...", Fore.YELLOW)
            r = requests.get(
                f"{API_BASE}/human?telegramId={self.telegram_id}&initData={urllib.parse.quote(self.init_data)}",
                headers=self.headers, verify=False, timeout=20
            )
            d = r.json()
            if not d.get("ok") and not d.get("challenge"):
                log("CAPTCHA", f"Gagal get challenge: {d.get('error')}", Fore.RED)
                return False

            challenge = d.get("challenge", {})
            token = challenge.get("token")
            question = challenge.get("question", "")
            options = challenge.get("options", [])

            if not token:
                log("CAPTCHA", "Token challenge tidak ditemukan.", Fore.RED)
                return False

            # Ekstrak jawaban dari payload token JWT
            part = token.split(".")[0]
            decoded = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)).decode("utf-8")
            token_info = json.loads(decoded)
            answer = token_info.get("e")

            log("CAPTCHA", f"Pertanyaan: '{question}' -> Jawaban otomatis: {answer}", Fore.CYAN)
            time.sleep(2.5)  # Delay agar tidak kena 'too_fast'

            r_ver = requests.post(f"{API_BASE}/human", json={
                "telegramId": self.telegram_id,
                "initData": self.init_data,
                "action": "verify",
                "token": token,
                "answer": answer
            }, headers=self.headers, verify=False, timeout=20)
            dv = r_ver.json()
            if dv.get("ok"):
                log("CAPTCHA", "✓ Captcha Berhasil Dipecahkan Secara Otomatis!", Fore.GREEN)
                return True
            else:
                log("CAPTCHA", f"Gagal verifikasi captcha: {dv.get('error')}", Fore.RED)
                return False
        except Exception as e:
            log("CAPTCHA", f"Error solving captcha: {e}", Fore.RED)
            return False

    def register_or_load(self):
        try:
            body = {
                "telegramId": self.telegram_id,
                "username": self.name,
                "firstName": self.name,
                "referCode": "",
                "initData": self.init_data,
                "fp": f"fp_{self.telegram_id}"
            }
            r = requests.post(f"{API_BASE}/user", json=body, headers=self.headers, verify=False, timeout=30)
            d = r.json()
            if d.get("success"):
                u = d.get("user", {})
                bal = u.get("egBalance", 0)
                log("USER", f"User: @{u.get('username')} | Saldo: {bal} MM$", Fore.GREEN)
                return u
        except Exception as e:
            log("USER", f"Error load user: {e}", Fore.RED)
        return None

    def claim_daily_login(self):
        try:
            r = requests.post(f"{API_BASE}/daily", json={
                "telegramId": self.telegram_id,
                "initData": self.init_data,
                "action": "login"
            }, headers=self.headers, verify=False, timeout=25)
            d = r.json()
            if d.get("success"):
                log("LOGIN", f"✓ Bonus Login: +{d.get('reward', 0)} MM$ | Saldo: {d.get('balance')} MM$", Fore.GREEN)
            elif "Already claimed" in d.get("error", ""):
                log("LOGIN", "Bonus login hari ini sudah diambil.", Fore.YELLOW)
            else:
                log("LOGIN", f"Login bonus: {d.get('error')}", Fore.YELLOW)
        except Exception as e:
            log("LOGIN", f"Error claim login: {e}", Fore.RED)

    def check_and_claim_farm(self):
        try:
            r = requests.get(f"{API_BASE}/farm?telegramId={self.telegram_id}&initData={urllib.parse.quote(self.init_data)}", headers=self.headers, verify=False, timeout=25)
            d = r.json()
            if not d.get("success"):
                return

            farm_data = d.get("farm", {})
            now_ms = farm_data.get("now", int(time.time() * 1000))
            farms = farm_data.get("farms", [])

            for f in farms:
                fid = f.get("id")
                name = f.get("name")
                unlocked = f.get("unlocked", False)
                ready_at = f.get("readyAt", 0)

                if unlocked:
                    if now_ms >= ready_at:
                        log("FARM", f"Farm {fid+1} ({name}) siap panen! Memulai claim...", Fore.CYAN)
                        self._do_farm_claim(fid, name)
                    else:
                        s_left = int((ready_at - now_ms) / 1000)
                        log("FARM", f"{name}: Cooldown panen {s_left}s lagi", Fore.YELLOW)
        except Exception as e:
            log("FARM", f"Error check farm: {e}", Fore.RED)

    def _do_farm_claim(self, slot_id, name):
        networks = ["gigapub", "adsgram_init"]
        for net in networks:
            try:
                r = requests.post(f"{API_BASE}/farm", json={
                    "telegramId": self.telegram_id,
                    "initData": self.init_data,
                    "action": "start",
                    "slot": slot_id,
                    "network": net
                }, headers=self.headers, verify=False, timeout=25)
                d = r.json()

                if d.get("error") == "human_check_required":
                    if self.solve_captcha():
                        return self._do_farm_claim(slot_id, name)
                    return

                if not d.get("success"):
                    continue

                start_time = d.get("startTime")
                sig = d.get("signature")
                log("FARM", f"[{name}] Nonton video sponsor ({net})... (15s)", Fore.MAGENTA)
                time.sleep(15)

                for attempt in range(4):
                    r2 = requests.post(f"{API_BASE}/farm", json={
                        "telegramId": self.telegram_id,
                        "initData": self.init_data,
                        "action": "claim",
                        "slot": slot_id,
                        "network": net,
                        "startTime": start_time,
                        "signature": sig,
                        "viewMs": 15200
                    }, headers=self.headers, verify=False, timeout=25)
                    d2 = r2.json()

                    if d2.get("error") == "human_check_required":
                        if self.solve_captcha():
                            break

                    if d2.get("success"):
                        log("FARM", f"✓ [{name}] Panen berhasil! +{d2.get('reward')} MM$ | Saldo: {d2.get('balance')} MM$", Fore.GREEN)
                        return
                    elif d2.get("error") == "s2s_pending":
                        time.sleep(3)
                    else:
                        break
            except Exception as e:
                log("FARM", f"Error farm claim {slot_id}: {e}", Fore.RED)

    def claim_all_tasks(self):
        try:
            # 1. Pinned Promo Channel Task
            try:
                r_pin = requests.post(f"{API_BASE}/tasks", json={
                    "telegramId": self.telegram_id,
                    "initData": self.init_data,
                    "taskId": "pinned_promo_channel",
                    "action": "complete"
                }, headers=self.headers, verify=False, timeout=20)
                dp = r_pin.json()
                if dp.get("success"):
                    log("TASK", f"✓ Pinned Task Selesai: +{dp.get('reward')} MM$ | Saldo: {dp.get('balance')} MM$", Fore.GREEN)
            except Exception:
                pass

            # 2. All Tasks (Link + Channel)
            r = requests.get(f"{API_BASE}/tasks?telegramId={self.telegram_id}&initData={urllib.parse.quote(self.init_data)}&cat=all", headers=self.headers, verify=False, timeout=25)
            d = r.json()
            if not d.get("success"):
                return

            tasks = d.get("tasks", [])
            for t in tasks:
                if t.get("completed"):
                    continue
                tid = t.get("id")
                title = t.get("title")
                reward = t.get("reward", 10)
                vtype = t.get("verifyType")
                link = t.get("link", "")

                if vtype == "link":
                    log("TASK", f"Mengerjakan task: {title} (+{reward} MM$)...", Fore.CYAN)
                    try:
                        r_start = requests.post(f"{API_BASE}/tasks", json={
                            "telegramId": self.telegram_id,
                            "initData": self.init_data,
                            "taskId": tid,
                            "action": "start"
                        }, headers=self.headers, verify=False, timeout=25)
                        ds = r_start.json()
                        if ds.get("success"):
                            st = ds.get("startTime")
                            sig = ds.get("signature")
                            time.sleep(9)
                            r_ver = requests.post(f"{API_BASE}/tasks", json={
                                "telegramId": self.telegram_id,
                                "initData": self.init_data,
                                "taskId": tid,
                                "action": "complete",
                                "startTime": st,
                                "signature": sig
                            }, headers=self.headers, verify=False, timeout=25)
                            dv = r_ver.json()
                            if dv.get("success"):
                                log("TASK", f"✓ Task Selesai: {title} (+{dv.get('reward')} MM$) | Saldo: {dv.get('balance')} MM$", Fore.GREEN)
                            else:
                                log("TASK", f"✖ Task gagal verify: {dv.get('error')}", Fore.YELLOW)
                    except Exception as ex:
                        log("TASK", f"Task error {tid}: {ex}", Fore.RED)
                    time.sleep(2)

                elif vtype == "api" and link:
                    log("TASK", f"[Join Task] Bergabung channel {title}...", Fore.CYAN)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(join_telegram_channel(self.phone, link))
                    loop.close()
                    time.sleep(3)

                    try:
                        r_ver = requests.post(f"{API_BASE}/tasks", json={
                            "telegramId": self.telegram_id,
                            "initData": self.init_data,
                            "taskId": tid,
                            "action": "complete"
                        }, headers=self.headers, verify=False, timeout=25)
                        dv = r_ver.json()
                        if dv.get("success"):
                            log("TASK", f"✓ Join Channel Selesai: {title} (+{dv.get('reward')} MM$) | Saldo: {dv.get('balance')} MM$", Fore.GREEN)
                    except Exception as ex:
                        log("TASK", f"Task verify error {tid}: {ex}", Fore.RED)
                    time.sleep(2)

        except Exception as e:
            log("TASK", f"Error load tasks: {e}", Fore.RED)

    def watch_daily_ads(self):
        """Nonton semua iklan harian sampai habis limit masing-masing."""
        try:
            r = requests.get(
                f"{API_BASE}/ads?telegramId={self.telegram_id}&initData={urllib.parse.quote(self.init_data)}",
                headers=self.headers, verify=False, timeout=25
            )
            d = r.json()
            if not d.get("success"):
                return

            networks = d.get("networks", [])
            # Daftar pending yang akan dicoba ulang di akhir
            pending_nets = []

            for net_info in networks:
                net_key = net_info.get("network")
                watched = net_info.get("watched", 0)
                limit = net_info.get("limit", 5)

                if watched >= limit:
                    log("ADS", f"[{net_key}] Sudah selesai hari ini ({watched}/{limit})", Fore.YELLOW)
                    continue

                log("ADS", f"=== Mulai klaim [{net_key}] | Progress: {watched}/{limit} ===", Fore.CYAN)
                net_pending = False

                # Loop sampai limit tercapai atau terjadi error fatal
                while watched < limit and self.running:
                    try:
                        log("ADS", f"Nonton Video Ad [{net_key}] ({watched+1}/{limit})...", Fore.MAGENTA)

                        # --- START ---
                        r_start = requests.post(f"{API_BASE}/ads", json={
                            "telegramId": self.telegram_id,
                            "initData": self.init_data,
                            "network": net_key,
                            "action": "start"
                        }, headers=self.headers, verify=False, timeout=25)
                        ds = r_start.json()

                        if ds.get("error") == "human_check_required":
                            if self.solve_captcha():
                                time.sleep(2)
                                continue
                            else:
                                log("ADS", f"[{net_key}] Captcha gagal, skip.", Fore.RED)
                                break

                        if ds.get("error") == "s2s_pending":
                            log("ADS", f"[{net_key}] s2s_pending saat start, tandai pending...", Fore.YELLOW)
                            net_pending = True
                            break

                        if ds.get("error") == "ad_cooldown":
                            log("ADS", f"[{net_key}] Cooldown antar-iklan, tunggu 10s...", Fore.YELLOW)
                            time.sleep(10)
                            continue

                        if not ds.get("success"):
                            log("ADS", f"[{net_key}] Start gagal: {ds.get('error')} — skip network ini.", Fore.RED)
                            break

                        st = ds.get("startTime")
                        sig = ds.get("signature")

                        # Tonton iklan 15 detik
                        time.sleep(15)

                        # --- CLAIM (retry s2s_pending max 5x) ---
                        claimed = False
                        for attempt in range(1, 6):
                            r_claim = requests.post(f"{API_BASE}/ads", json={
                                "telegramId": self.telegram_id,
                                "initData": self.init_data,
                                "network": net_key,
                                "action": "claim",
                                "startTime": st,
                                "signature": sig,
                                "viewMs": 15200
                            }, headers=self.headers, verify=False, timeout=25)
                            dc = r_claim.json()

                            if dc.get("error") == "human_check_required":
                                if self.solve_captcha():
                                    time.sleep(2)
                                    continue
                                else:
                                    break

                            if dc.get("error") == "s2s_pending":
                                log("ADS", f"[{net_key}] s2s_pending ({attempt}/5), coba lagi 4s...", Fore.YELLOW)
                                time.sleep(4)
                                continue

                            if dc.get("success"):
                                watched = dc.get("watched", watched + 1)
                                reward = dc.get("reward", 0)
                                balance = dc.get("balance", "?")
                                log("ADS", f"✓ [{net_key}] +{reward} MM$ ({watched}/{limit}) | Saldo: {balance} MM$", Fore.GREEN)
                                claimed = True
                                break
                            else:
                                log("ADS", f"[{net_key}] Claim error: {dc.get('error')} — skip.", Fore.RED)
                                break

                        if not claimed:
                            # s2s mungkin perlu waktu dari sisi server, tandai pending
                            log("ADS", f"[{net_key}] Gagal diklaim, tandai pending dan lanjut ke network lain.", Fore.YELLOW)
                            net_pending = True
                            break

                        time.sleep(3)  # Jeda antar iklan

                    except Exception as ex:
                        log("ADS", f"[{net_key}] Exception: {ex}", Fore.RED)
                        break

                if net_pending:
                    pending_nets.append(net_key)
                elif watched >= limit:
                    log("ADS", f"✓ [{net_key}] Semua iklan selesai! ({watched}/{limit})", Fore.GREEN)

            # Coba ulang network yang pending satu kali di akhir
            if pending_nets:
                log("ADS", f"Mencoba ulang {len(pending_nets)} network pending: {pending_nets}", Fore.CYAN)
                time.sleep(15)
                for net_key in pending_nets:
                    # Ambil info terkini
                    try:
                        r2 = requests.get(
                            f"{API_BASE}/ads?telegramId={self.telegram_id}&initData={urllib.parse.quote(self.init_data)}",
                            headers=self.headers, verify=False, timeout=25
                        )
                        d2 = r2.json()
                        net_info2 = next((n for n in d2.get("networks", []) if n.get("network") == net_key), None)
                        if not net_info2:
                            continue
                        watched2 = net_info2.get("watched", 0)
                        limit2 = net_info2.get("limit", 5)
                        if watched2 >= limit2:
                            log("ADS", f"[{net_key}] Sudah selesai setelah retry ({watched2}/{limit2})", Fore.GREEN)
                            continue

                        log("ADS", f"[Retry Pending] Nonton [{net_key}] ({watched2+1}/{limit2})...", Fore.MAGENTA)
                        r_s = requests.post(f"{API_BASE}/ads", json={
                            "telegramId": self.telegram_id,
                            "initData": self.init_data,
                            "network": net_key,
                            "action": "start"
                        }, headers=self.headers, verify=False, timeout=25)
                        ds2 = r_s.json()
                        if not ds2.get("success"):
                            log("ADS", f"[{net_key}] Retry start gagal: {ds2.get('error')}", Fore.RED)
                            continue

                        st2 = ds2.get("startTime")
                        sig2 = ds2.get("signature")
                        time.sleep(15)

                        for attempt in range(1, 6):
                            r_c2 = requests.post(f"{API_BASE}/ads", json={
                                "telegramId": self.telegram_id,
                                "initData": self.init_data,
                                "network": net_key,
                                "action": "claim",
                                "startTime": st2,
                                "signature": sig2,
                                "viewMs": 15200
                            }, headers=self.headers, verify=False, timeout=25)
                            dc2 = r_c2.json()
                            if dc2.get("success"):
                                log("ADS", f"✓ [Retry OK] [{net_key}] +{dc2.get('reward')} MM$", Fore.GREEN)
                                break
                            elif dc2.get("error") == "s2s_pending":
                                time.sleep(4)
                            else:
                                log("ADS", f"[{net_key}] Retry claim: {dc2.get('error')}", Fore.YELLOW)
                                break
                    except Exception as ex:
                        log("ADS", f"[{net_key}] Retry exception: {ex}", Fore.RED)

        except Exception as e:
            log("ADS", f"Error daily ads: {e}", Fore.RED)

    def run_cycle(self):
        if not self.init_data or not self.telegram_id:
            if not self.refresh_auth():
                return
        self.register_or_load()
        self.claim_daily_login()
        self.claim_all_tasks()
        self.watch_daily_ads()
        self.check_and_claim_farm()

    def run_24h(self):
        print(f"\n{Fore.GREEN}═══ MENJALANKAN GRAM EDGE FARM 24 JAM NON-STOP ═══{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Akun Aktif: {self.name} ({self.phone})")
        print(f"Tekan Ctrl+C kapan saja untuk menghentikan program.{Style.RESET_ALL}\n")

        cycle_count = 0
        last_refresh = time.time()

        while self.running:
            cycle_count += 1
            log("CYCLE", f"=== Siklus #{cycle_count} ===", Fore.BLUE)

            # Auto-refresh initData setiap 2 jam via Telethon
            if time.time() - last_refresh > 7200 or not self.init_data:
                self.refresh_auth()
                last_refresh = time.time()

            try:
                self.run_cycle()
            except Exception as e:
                log("CYCLE", f"Error di siklus: {e}", Fore.RED)

            log("CYCLE", "Selesai 1 siklus. Istirahat 3 menit sebelum cek berikutnya...", Fore.CYAN)
            for _ in range(180):
                if not self.running:
                    break
                time.sleep(1)

def menu_login():
    print(f"\n{Fore.CYAN}═══ LOGIN NOMOR TELEGRAM (TELETHON) ═══{Style.RESET_ALL}")
    phone = input("Masukkan Nomor HP Telegram (format: +628xxx): ").strip()
    if not phone:
        return None
    name = input("Masukkan Nama/Label Akun: ").strip() or phone

    session_file = get_session_path(phone)
    client = TelegramClient(session_file, API_ID, API_HASH)

    async def _do():
        await client.connect()
        if not await client.is_user_authorized():
            try:
                await client.send_code_request(phone)
                code = input(f"{Fore.YELLOW}Masukkan OTP Telegram untuk {phone}: {Style.RESET_ALL}").strip()
                try:
                    await client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    pwd = input(f"{Fore.YELLOW}Akun ini pakai 2FA Password. Masukkan: {Style.RESET_ALL}").strip()
                    await client.sign_in(password=pwd)
            except Exception as e:
                print(f"{Fore.RED}Gagal login: {e}{Style.RESET_ALL}")
                await client.disconnect()
                return False

        me = await client.get_me()
        print(f"{Fore.GREEN}✓ Login Berhasil! Nama: {me.first_name} (@{me.username}){Style.RESET_ALL}")
        await client.disconnect()
        return True

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ok = loop.run_until_complete(_do())
    loop.close()

    if ok:
        account = {"phone": phone, "name": name}
        save_active_account(account)
        return account
    return None

def main():
    while True:
        acc = load_active_account()
        status_acc = f"{acc.get('name')} ({acc.get('phone')})" if acc else "Belum Ada"

        print(f"""
{Fore.GREEN}╔════════════════════════════════════════════════════════════╗
║             GRAM EDGE FARM — SMART AUTO BOT                ║
║   Auto-Login Telethon • Auto Captcha Solver • Auto Harvest ║
╠════════════════════════════════════════════════════════════╣
║  Akun Aktif : {status_acc.ljust(44)}║
╠════════════════════════════════════════════════════════════╣
║  [1] Login / Ganti Nomor HP Telegram (OTP)                 ║
║  [2] Start Bot 24 Jam Non-Stop                             ║
║  [0] Keluar                                                ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}""")
        pilih = input("Pilih menu (0-2): ").strip()
        if pilih == "1":
            menu_login()
        elif pilih == "2":
            if not acc:
                print(f"{Fore.YELLOW}Silakan login nomor HP terlebih dahulu.{Style.RESET_ALL}")
                acc = menu_login()
            if acc:
                bot = GramEdgeBot(acc)
                try:
                    bot.run_24h()
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}[SHUTDOWN] Bot dihentikan.{Style.RESET_ALL}")
        elif pilih == "0":
            break

if __name__ == "__main__":
    main()

import asyncio
import json
import time
import requests
import os
import sys
import random
import hashlib
from urllib.parse import unquote, parse_qs
from telethon import TelegramClient, functions

os.system('cls' if os.name == 'nt' else 'clear')

# ==================== KONFIG ====================
API_ID = 39586930
API_HASH = 'acedf357c5085e652a78b69f33660e8a'
BOT_USERNAME = 'coinfree_appbot'
APP_URL = 'https://coinfree.app/'
API_ENDPOINT = 'https://coinfree.app/api.php'

WARYONO_SOLVER = 'https://api.waryono.my.id/in.php'
WARYONO_RESULT = 'https://api.waryono.my.id/res.php'
SITEKEY = '0x4AAAAAAB6mAUIH75NUE5fq'

MODES = ['drop', 'coinflip', 'claw', 'plinko', 'target', 'box', 'card', 'wheel', 'koi']
MODE_LABELS = {
    'drop': 'DROP', 'coinflip': 'COINFLIP', 'claw': 'CLAW', 'plinko': 'VAULT BREAKER',
    'target': 'ROCKET LAUNCH', 'box': 'COIN REACTOR', 'card': 'MYSTERY BOX',
    'wheel': 'LUCKY WHEEL', 'koi': 'KOI POND'
}
ASSET = 'PEPE'

# ==================== WARNA NEON ====================
NC  = '\033[38;5;51m';  NG  = '\033[38;5;46m'
NP  = '\033[38;5;201m'; NY  = '\033[38;5;226m'
NR  = '\033[38;5;196m'; NO  = '\033[38;5;208m'
NPR = '\033[38;5;135m'; NW  = '\033[38;5;231m'
B   = '\033[1m';        R   = '\033[0m'

START_SENT_FLAG = False

# ==================== CONFIG FILES ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'coinfree_config.json')
DEVICE_FILE = os.path.join(BASE_DIR, 'coinfree_devices.json')
SESSION_NAME = os.path.join(BASE_DIR, 'coinfree_session')

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"waryono_key": "", "device_id": ""}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    except: pass

CONFIG = load_config()

# ==================== HTTP SESSION ====================
USER_AGENT = "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.8103.50 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"

http_session = requests.Session()
http_session.headers.update({
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://coinfree.app",
    "referer": "https://coinfree.app/",
    "x-requested-with": "org.telegram.messenger.web",
    "sec-ch-ua": '"Not-A.Brand";v="99", "Android WebView";v="157", "Chromium";v="157"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "user-agent": USER_AGENT,
})

def get_client_info():
    return {
        "user_agent": USER_AGENT,
        "platform": "android",
        "timezone": "Asia/Jakarta"
    }

# ==================== DEVICE ID ====================
def load_devices():
    if os.path.exists(DEVICE_FILE):
        try:
            with open(DEVICE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {}

def save_devices(db):
    try:
        with open(DEVICE_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2)
    except: pass

def get_device_id(user_id):
    if CONFIG.get("device_id"):
        return CONFIG["device_id"]
    db = load_devices()
    k = str(user_id)
    if k in db:
        return db[k]
    seed = f"{USER_AGENT}|Android|id-ID|Asia/Jakarta|{user_id}"
    new_id = hashlib.sha256(seed.encode()).hexdigest()
    db[k] = new_id
    save_devices(db)
    return new_id

# ==================== UTIL ====================
def clear_screen():
    sys.stdout.write("\033[H\033[2J\033[3J")
    sys.stdout.flush()

def countdown_timer(seconds, prefix="⏳"):
    if seconds <= 0: return
    for i in range(int(seconds), 0, -1):
        print(f"\r    {NC}{prefix} {i:2d}s {R}", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 35 + "\r", end="", flush=True)

def format_time(seconds):
    s = int(seconds); h = s // 3600; m = (s % 3600) // 60; sc = s % 60
    return f"{h}j {m}m {sc}s" if h > 0 else f"{m}m {sc}s"

def parse_init_data(raw):
    try:
        p = parse_qs(raw)
        u_str = p.get('user', ['{}'])[0]
        return {'user': json.loads(u_str)}
    except:
        return None

def mask(s):
    if not s: return "(belum diisi)"
    return s[:6] + "*" * max(0, len(s)-10) + s[-4:] if len(s) > 10 else s

# ==================== SOLVER WARYONO ====================
def solve_captcha(action="faucet_claim", step="1", cdata=""):
    key = CONFIG.get("waryono_key", "")
    if not key:
        print(f"\r  [+] Captcha #{step}... {NR}NO KEY{R}", end="", flush=True)
        return None
    print(f"  [+] Captcha #{step}... ", end="", flush=True)
    payload = {
        "apikey": key,
        "methods": "turnstile",
        "domain": "https://coinfree.app",
        "sitekey": SITEKEY,
        "action": action,
        "cdata": cdata,
        "json": 1
    }
    try:
        r = requests.post(WARYONO_SOLVER, json=payload, headers={"Content-Type": "application/json"}, timeout=60).json()
    except Exception as e:
        print(f"\r  [+] Captcha #{step}... {NR}REQ FAIL: {e}{R}")
        return None

    if r.get("status") != 1:
        err = r.get("request") or r.get("error") or "NO TASKID"
        print(f"\r  [+] Captcha #{step}... {NR}{err}{R}          ")
        return None

    task_id = r["request"]
    for attempt in range(60):
        print(f"\r  [+] Captcha #{step}... {NC}⏳{attempt*3}s{R} ", end="", flush=True)
        time.sleep(3)
        try:
            p = requests.get(f"{WARYONO_RESULT}?apikey={key}&action=get&id={task_id}&json=1", timeout=30).json()
            if p.get("status") == 1 and p.get("request"):
                tok = str(p["request"])
                if len(tok) > 50 and "." in tok:
                    print(f"\r  [+] Captcha #{step}... {NG}✅ Solved ({attempt*3}s){R}          ")
                    return tok
            err = str(p.get("request", ""))
            if "CAPCHA_NOT_READY" in err or "PENDING" in err:
                continue
            print(f"\r  [+] Captcha #{step}... {NR}{err}{R}          ")
            return None
        except:
            continue
    print(f"\r  [+] Captcha #{step}... {NR}TIMEOUT{R}          ")
    return None

# ==================== API CALL ====================
async def call_api(action, init_data, device_id, payload=None):
    body = {
        "action": action,
        "initData": init_data,
        "deviceId": device_id,
        "clientInfo": get_client_info(),
    }
    if payload:
        body.update(payload)
    try:
        res = await asyncio.to_thread(http_session.post, API_ENDPOINT, json=body, timeout=30)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== TELETHON LOGIN ====================
async def get_init_data(skip_start=False, retry=0):
    global START_SENT_FLAG
    print(f"Mengambil data login WebApp... ", end="", flush=True)

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    try:
        await client.start()
    except Exception as e:
        print(f"\r{NR}Telethon Connection error: {e}{R}")
        return None

    try:
        bot = await client.get_input_entity(BOT_USERNAME)
        if not skip_start and not START_SENT_FLAG:
            await client.send_message(bot, "/start")
            START_SENT_FLAG = True
            await asyncio.sleep(2)

        wv = await client(functions.messages.RequestWebViewRequest(
            peer=bot, bot=bot, platform='android', from_bot_menu=False, url=APP_URL))
        raw = wv.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
        await client.disconnect()
        print(f"\r{NG}✅ WebApp Login OK{R}          ")
        return unquote(raw)
    except Exception as e:
        try:
            await client.disconnect()
        except: pass
        print(f"\r{NR}FAIL: {e}{R}")
        if retry < 3:
            countdown_timer(5 * (retry + 1))
            return await get_init_data(skip_start, retry + 1)
        return None

async def login_telethon_interactive():
    clear_screen()
    print(f"{NC}{B}── LOGIN TELEGRAM (NO HP / OTP) ──{R}\n")
    print(f"{NW}Session file: {SESSION_NAME}.session{R}")
    print(f"{NY}Masukkan No HP (+62...) dan kode OTP Telegram jika diminta:{R}\n")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    try:
        await client.start()
        me = await client.get_me()
        user_name = me.first_name if me else "User"
        user_phone = me.phone if me else "-"
        print(f"\n{NG}✅ Login berhasil! Terhubung sebagai: {user_name} (+{user_phone}){R}")
        await client.disconnect()
    except Exception as e:
        print(f"\n{NR}❌ Gagal login: {e}{R}")
        try: await client.disconnect()
        except: pass

async def get_user_data(init_data, device_id):
    r = await call_api("get_user_data", init_data, device_id)
    return r.get("data") if r.get("status") == "success" else None

# ==================== CLAIM DAILY STREAK ====================
async def check_and_claim_daily_streak(init_data, device_id):
    try:
        res = await call_api("claim_daily_streak", init_data, device_id)
        if res.get("status") == "success":
            day = res.get("data", {}).get("checkin_day", 1)
            print(f"  {NG}🎁 Daily Streak Day {day} BERHASIL DIKLAIM!{R}")
    except Exception:
        pass

# ==================== GAME SELECTION (OPTIMAL GACOR) ====================
def find_ready_game(ud, blocked_modes=None):
    if blocked_modes is None:
        blocked_modes = set()
    g = int(ud.get("faucet_global_cooldown_remaining", 0))
    mw, best = 999999, None

    for gt in MODES:
        if gt in blocked_modes:
            continue
        if ud.get(f'faucet_daily_limit_reached_{gt}', False):
            continue
        rem = int(ud.get(f'faucet_cooldown_remaining_{gt}', 0))
        if rem == 0 and g == 0:
            return gt, 0
        eff = max(rem, g)
        if eff < mw:
            mw, best = eff, gt

    return None, mw

# ==================== PROCESS GAME ====================
async def process_game(init_data, device_id, game_type):
    print(f"\n{B}{NPR}▶ MODE: {MODE_LABELS.get(game_type, game_type.upper())}{R}")

    prep = await call_api("prepare_claim_challenge", init_data, device_id,
                          {"claimAction": "claim_faucet", "mode": game_type})
    if prep.get("status") != "success":
        err = str(prep.get("message", ""))
        print(f"  [+] Prepare challenge... {NR}FAIL: {err}{R}")
        if "invalid" in err.lower() or "expired" in err.lower():
            return "session_invalid"
        return False

    challenge = prep.get("challenge")
    cdata = prep.get("cdata", "")
    action = prep.get("action", "faucet_claim")

    # 2. Spin Reward
    spin = await call_api("get_faucet_spin_reward", init_data, device_id, {"mode": game_type})
    if spin.get("status") != "success":
        msg = spin.get("message", "")
        if "daily ip claim limit" in msg.lower():
            print(f"  [+] Get reward... {NR}LIMIT: {msg}{R}")
            return "mode_ip_limited"
        elif "cooldown" in msg.lower():
            print(f"  [+] Get reward... {NY}Cooldown {spin.get('cooldown_remaining',0)}s{R}")
        else:
            print(f"  [+] Get reward... {NR}FAIL: {msg}{R}")
        return False

    base = float(spin.get("baseRewardAmount", 0))
    mult = float(spin.get("double_reward_multiplier", 3))
    print(f"  Reward: {NG}{base:.2f}{R} {NP}{ASSET}{R} {NO}(x{mult:.0f} Gacor Booster){R}")

    # Khusus Mode KOI POND: Wajib memberi makan koi 5 kali sebelum klaim
    if game_type == 'koi':
        print(f"  [+] Memberi makan Koi (5x taps)... ", end="", flush=True)
        koi_round = await call_api("get_koi_round", init_data, device_id)
        if koi_round.get("status") == "success":
            koi_info = koi_round.get("koi", {})
            r_token = koi_info.get("roundToken")
            cur_taps = koi_info.get("taps", 0)
            for seq in range(cur_taps + 1, 6):
                await asyncio.sleep(0.5)
                f_res = await call_api("feed_koi", init_data, device_id,
                                       {"roundToken": r_token, "sequence": seq})
                if f_res.get("status") != "success":
                    print(f"\r  [+] Feed koi #{seq}... {NR}FAIL: {f_res.get('message')}{R}")
                    break
            else:
                print(f"\r  [+] Feed koi... {NG}✅ Selesai 5/5{R}          ")
        else:
            print(f"\r  [+] Feed koi... {NY}Gagal ambil putaran koi ({koi_round.get('message')}){R}")

    # 3. Bind Claim Challenge
    bind_res = await call_api("bind_claim_challenge", init_data, device_id,
                              {"claimChallenge": challenge})
    if bind_res.get("status") != "success":
        print(f"  [+] Bind challenge... {NR}FAIL: {bind_res.get('message')}{R}")

    # 4. Double Reward Ad (Mengaktifkan pengali x3 reward)
    print(f"  [+] Double ad... ", end="", flush=True)
    chosen, req = None, None
    for prov in ["richads_video", "giga", "tads"]:
        res = await call_api("request_double_reward_ad", init_data, device_id,
                             {"mode": game_type, "provider": prov})
        if res.get("status") == "success":
            req, chosen = res, prov
            break

    require_double = False
    if req:
        ticket = req.get("ticket", "")
        wait_s = int(req.get("min_wait_seconds", 10))
        for i in range(wait_s, 0, -1):
            print(f"\r  [+] Double ad... {NC}⏳{i:2d}s {R}", end="", flush=True)
            await asyncio.sleep(1)
        c = await call_api("complete_double_reward_ad", init_data, device_id,
                           {"mode": game_type, "ticket": ticket, "provider": chosen})
        if c.get("status") == "success":
            print(f"\r  [+] Double ad... {NG}✅ SUKSES (x{mult:.0f}){R}          ")
            require_double = True
        else:
            print(f"\r  [+] Double ad... {NY}⚠ Ad Skipped{R}          ")
            await call_api("cancel_reward_ad", init_data, device_id,
                           {"mode": game_type, "ticket": ticket, "provider": chosen, "outcome": "no_fill"})
    else:
        print(f"\r  [+] Double ad... {NY}SKIP{R}")

    # 5. Selesaikan Captcha Cloudflare Turnstile via Waryono
    tok = await asyncio.to_thread(solve_captcha, action, "1", cdata)
    if not tok:
        print(f"  {NR}❌ Captcha gagal dipecahkan, skip.{R}")
        return False

    # 6. Claim Faucet
    print(f"  [+] Submit Claim... ", end="", flush=True)
    claim = await call_api("claim_faucet", init_data, device_id, {
        "captchaToken": tok,
        "requireDouble": require_double,
        "mode": game_type,
        "claimChallenge": challenge,
        "stepupToken": ""
    })

    if claim.get("status") == "success":
        amt = float(claim.get("claimed_amount", 0))
        coin = claim.get("coin", ASSET)
        dbl = f" {NP}(x{mult:.0f} GACOR!){R}" if claim.get("double_applied") else ""
        print(f"\r  [+] Claim... {NG}✅ +{amt:.8f} {NP}{coin}{R}{dbl}")
        cd = claim.get("faucet_global_cooldown_remaining", 60)
        if cd > 0:
            print(f"  [+] Global Cooldown {NY}{format_time(cd)}{R}...")
            countdown_timer(cd)
        return True

    print(f"\r  [+] Claim... {NR}FAIL: {claim.get('message')}{R}")
    return False

# ==================== MENU UTAMA ====================
async def main_menu():
    while True:
        clear_screen()
        print(f"{NC}{B}╔══════════════════════════════════════════════════════════════╗{R}")
        print(f"{NC}{B}║{NP}           COINFREE AUTO FARMER — SINGLE ACCOUNT              {NC}║{R}")
        print(f"{NC}{B}║{NY}                 Fast & Gacor Edition                         {NC}║{R}")
        print(f"{NC}{B}╚══════════════════════════════════════════════════════════════╝{R}\n")

        sess_exists = os.path.exists(f"{SESSION_NAME}.session")
        status_sess = f"{NG}✅ Terhubung ({SESSION_NAME}.session){R}" if sess_exists else f"{NR}❌ Belum Login{R}"
        key_status = f"{NG}✅ {mask(CONFIG.get('waryono_key'))}{R}" if CONFIG.get("waryono_key") else f"{NR}❌ Belum diisi{R}"

        print(f"  Status Sesi Telegram : {status_sess}")
        print(f"  API Key Waryono      : {key_status}\n")

        print(f"{NC}Pilihan Menu:{R}")
        print(f"  {NW}[1]{R} {NG}🔑 Login / Ganti Akun Telegram (No HP / OTP){R}")
        print(f"  {NW}[2]{R} {NY}⚙ Masukkan API Key Waryono{R}")
        print(f"  {NW}[3]{R} {NG}{B}▶ Start Bot (Mulai Farming){R}")
        print(f"  {NW}[4]{R} {NR}🗑 Hapus Sesi Akun Telegram{R}")
        print(f"  {NW}[0]{R} Keluar\n")

        choice = input(f"{NC}➜ Pilih (1-4 / 0): {R}").strip()

        # [1] Login / Ganti Akun Telegram
        if choice == '1':
            await login_telethon_interactive()
            input(f"\n{NW}Enter untuk kembali ke menu...{R}")

        # [2] Masukkan API Key Waryono
        elif choice == '2':
            clear_screen()
            print(f"{NC}{B}── MASUKKAN WARYONO API KEY ──{R}\n")
            cur = CONFIG.get("waryono_key", "")
            print(f"API Key saat ini: {NC}{cur or '(belum diisi)'}{R}\n")
            key = input(f"{NG}Masukkan API Key baru: {R}").strip()
            if key:
                CONFIG["waryono_key"] = key
                save_config(CONFIG)
                print(f"\n{NG}✅ API Key berhasil disimpan!{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        # [3] Start Bot
        elif choice == '3':
            if not CONFIG.get("waryono_key"):
                print(f"\n{NR}⚠ API Key Waryono belum diisi! Silakan isi di menu [2].{R}")
                input(f"\n{NW}Enter untuk kembali...{R}")
                continue
            return True

        # [4] Hapus Sesi Akun
        elif choice == '4':
            clear_screen()
            print(f"{NR}{B}── HAPUS SESI AKUN ──{R}\n")
            sess_file = f"{SESSION_NAME}.session"
            if os.path.exists(sess_file):
                ans = input(f"{NR}Yakin ingin menghapus sesi login ({sess_file})? (y/n): {R}").strip().lower()
                if ans == 'y':
                    try:
                        os.remove(sess_file)
                        print(f"\n{NG}✅ Sesi berhasil dihapus. Silakan login kembali di menu [1].{R}")
                    except Exception as e:
                        print(f"\n{NR}Gagal menghapus file: {e}{R}")
            else:
                print(f"{NY}Tidak ada sesi tersimpan.{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        # [0] Keluar
        elif choice == '0':
            sys.exit(0)

# ==================== MAIN ====================
async def main():
    if not await main_menu():
        return

    clear_screen()
    print(f"{NC}{B}╔══════════════════════════════════════════════════════════════╗{R}")
    print(f"{NC}{B}║{NP}           COINFREE AUTO FARMER — RUNNING                     {NC}║{R}")
    print(f"{NC}{B}╚══════════════════════════════════════════════════════════════╝{R}\n")

    init_data = await get_init_data()
    if not init_data:
        print(f"{NR}Gagal mendapatkan data login Telegram WebApp.{R}")
        return

    parsed = parse_init_data(init_data)
    if not parsed or 'user' not in parsed:
        print(f"{NR}Gagal parse data pengguna.{R}")
        return

    user_info = parsed['user']
    user_id = user_info.get('id', 0)
    username = user_info.get('username') or user_info.get('first_name', 'User')

    device_id = get_device_id(user_id)
    print(f"User ID   : {NW}{user_id}{R} | Username: {NG}@{username}{R}")
    print(f"Device ID : {NC}{device_id[:16]}...{R}")

    # Check user data
    ud = await get_user_data(init_data, device_id)
    if not ud:
        print(f"{NR}Gagal mengambil data user dari server.{R}")
        return

    bal = float(ud.get("balance", 0))
    pref = ud.get("preferred_coin", ASSET)
    print(f"Saldo Awal: {NY}{B}{bal:.8f} {NP}{pref}{R}")

    # Auto klaim daily streak
    await check_and_claim_daily_streak(init_data, device_id)

    # Farming loop
    blocked_modes = set()
    while True:
        ud = await get_user_data(init_data, device_id)
        if not ud:
            print(f"\n{NY}Refresh session...{R}")
            init_data = await get_init_data(skip_start=True)
            if not init_data: break
            continue

        mode, wait = find_ready_game(ud, blocked_modes=blocked_modes)
        if mode is None:
            if len(blocked_modes) >= len(MODES):
                print(f"\n{NY}Semua mode game terkena Daily Limit IP hari ini.{R}")
                print(f"{NC}Istirahat 10 menit sebelum mencoba kembali...{R}")
                blocked_modes.clear()
                countdown_timer(600)
                continue
            elif wait >= 999999:
                print(f"\n{NY}Semua game sudah mencapai daily limit hari ini!{R}")
                print(f"{NC}Tunggu reset harian (20 menit)...{R}")
                countdown_timer(1200)
                continue
            else:
                print(f"\n{NC}⏳ Cooldown game terdekat: {NY}{int(wait)}s{NC}...{R}")
                countdown_timer(wait)
                continue

        res = await process_game(init_data, device_id, mode)
        if res == "mode_ip_limited":
            blocked_modes.add(mode)
            print(f"{NY}Mode '{MODE_LABELS.get(mode, mode)}' kena limit IP. Beralih ke game lain...{R}")
            await asyncio.sleep(1)
            continue
        elif res == "session_invalid":
            print(f"\n{NY}Session kedaluwarsa, refresh session...{R}")
            init_data = await get_init_data(skip_start=True)
            if not init_data: break
            continue
        elif not res:
            blocked_modes.add(mode)
            print(f"{NY}Claim gagal. Melewati ke game lainnya...{R}")
            await asyncio.sleep(2)

        await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{NY}Bot dihentikan oleh user.{R}")
    except Exception as e:
        print(f"\n{NR}Error: {e}{R}")

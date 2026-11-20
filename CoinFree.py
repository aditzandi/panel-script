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

START_SENT_FLAG = set()

# ==================== CONFIG FILES ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'coinfree_config.json')
DEVICE_FILE = os.path.join(BASE_DIR, 'coinfree_devices.json')
ACCOUNTS_FILE = os.path.join(BASE_DIR, 'coinfree_accounts.json')

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"waryono_key": "f7457613bf1330fe8086b923de6dbccd", "device_id": "", "auto_streak": True}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    except: pass

CONFIG = load_config()

# ==================== MULTI-ACCOUNT STORAGE ====================
def load_accounts():
    """
    Format accounts:
    [
        {
            "id": 1,
            "name": "Akun 1",
            "type": "telethon",         # 'telethon' atau 'init_data'
            "session_name": "session_1", # untuk telethon
            "init_data": ""             # untuk direct init_data
        }
    ]
    """
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    # Default jika belum ada akun:
    return [
        {
            "id": 1,
            "name": "Akun Utama",
            "type": "telethon",
            "session_name": "coinfree_session",
            "init_data": ""
        }
    ]

def save_accounts(accs):
    try:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accs, f, indent=2)
    except: pass

ACCOUNTS = load_accounts()

# ==================== HTTP SESSION FACTORY ====================
USER_AGENT = "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.8103.50 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"

def create_session():
    s = requests.Session()
    s.headers.update({
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
    return s

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
    # Gacor & konsisten: generate SHA256 device fingerprint konsisten per user_id
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
    if not s: return "(kosong)"
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
async def call_api(http_sess, action, init_data, device_id, payload=None):
    body = {
        "action": action,
        "initData": init_data,
        "deviceId": device_id,
        "clientInfo": get_client_info(),
    }
    if payload:
        body.update(payload)
    try:
        res = await asyncio.to_thread(http_sess.post, API_ENDPOINT, json=body, timeout=30)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== LOGIN ====================
async def get_init_data(account, skip_start=False, retry=0):
    """Mendapatkan initData baik dari Telethon session maupun Direct Init Data"""
    global START_SENT_FLAG
    acc_name = account.get("name", "Akun")
    acc_type = account.get("type", "telethon")

    if acc_type == "init_data":
        data = account.get("init_data", "").strip()
        if data:
            print(f"[{acc_name}] {NG}✅ Direct initData ready{R}")
            return data
        print(f"[{acc_name}] {NR}❌ initData kosong!{R}")
        return None

    # Telethon Session
    sess_name = account.get("session_name", "coinfree_session")
    sess_path = os.path.join(BASE_DIR, sess_name) if not os.path.isabs(sess_name) else sess_name
    print(f"[{acc_name}] Telethon login ({sess_name})... ", end="", flush=True)

    client = TelegramClient(sess_path, API_ID, API_HASH)
    try:
        await client.start()
    except Exception as e:
        print(f"\r[{acc_name}] {NR}Telethon Connection error: {e}{R}")
        return None

    try:
        bot = await client.get_input_entity(BOT_USERNAME)
        if not skip_start and sess_name not in START_SENT_FLAG:
            await client.send_message(bot, "/start")
            START_SENT_FLAG.add(sess_name)
            await asyncio.sleep(2)

        wv = await client(functions.messages.RequestWebViewRequest(
            peer=bot, bot=bot, platform='android', from_bot_menu=False, url=APP_URL))
        raw = wv.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
        await client.disconnect()
        print(f"\r[{acc_name}] {NG}✅ Telethon WebApp OK{R}          ")
        return unquote(raw)
    except Exception as e:
        try:
            await client.disconnect()
        except: pass
        print(f"\r[{acc_name}] {NR}FAIL: {e}{R}")
        if retry < 3:
            countdown_timer(5 * (retry + 1))
            return await get_init_data(account, skip_start, retry + 1)
        return None

async def get_user_data(http_sess, init_data, device_id):
    r = await call_api(http_sess, "get_user_data", init_data, device_id)
    return r.get("data") if r.get("status") == "success" else None

# ==================== CLAIM DAILY STREAK ====================
async def check_and_claim_daily_streak(http_sess, init_data, device_id):
    """Auto klaim daily check-in streak jika belum klaim hari ini"""
    try:
        res = await call_api(http_sess, "claim_daily_streak", init_data, device_id)
        if res.get("status") == "success":
            day = res.get("data", {}).get("checkin_day", 1)
            print(f"  {NG}🎁 Daily Streak Day {day} BERHASIL DIKLAIM!{R}")
        elif "already checked in" in str(res.get("message", "")).lower():
            pass
    except Exception:
        pass

# ==================== GAME SELECTION (OPTIMAL GACOR) ====================
def find_ready_game(ud):
    """
    Pilih game terbaik yang cooldown = 0.
    Jika cooldown global > 0, kembalikan remaining time.
    """
    g = int(ud.get("faucet_global_cooldown_remaining", 0))
    mw, best = 999999, None

    # Prioritaskan mode yang belum limit dan cooldown = 0
    for gt in MODES:
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
async def process_game(http_sess, init_data, device_id, game_type):
    print(f"\n{B}{NPR}▶ MODE: {MODE_LABELS.get(game_type, game_type.upper())}{R}")

    # 1. Prepare Claim Challenge (Dapatkan challenge & cdata)
    prep = await call_api(http_sess, "prepare_claim_challenge", init_data, device_id,
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
    spin = await call_api(http_sess, "get_faucet_spin_reward", init_data, device_id, {"mode": game_type})
    if spin.get("status") != "success":
        msg = spin.get("message", "")
        if "cooldown" in msg.lower():
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
        koi_round = await call_api(http_sess, "get_koi_round", init_data, device_id)
        if koi_round.get("status") == "success":
            koi_info = koi_round.get("koi", {})
            r_token = koi_info.get("roundToken")
            cur_taps = koi_info.get("taps", 0)
            for seq in range(cur_taps + 1, 6):
                await asyncio.sleep(0.5)
                f_res = await call_api(http_sess, "feed_koi", init_data, device_id,
                                       {"roundToken": r_token, "sequence": seq})
                if f_res.get("status") != "success":
                    print(f"\r  [+] Feed koi #{seq}... {NR}FAIL: {f_res.get('message')}{R}")
                    break
            else:
                print(f"\r  [+] Feed koi... {NG}✅ Selesai 5/5{R}          ")
        else:
            print(f"\r  [+] Feed koi... {NY}Gagal ambil putaran koi ({koi_round.get('message')}){R}")

    # 3. Bind Claim Challenge (Wajib memakai cookie session yang sama)
    bind_res = await call_api(http_sess, "bind_claim_challenge", init_data, device_id,
                              {"claimChallenge": challenge})
    if bind_res.get("status") != "success":
        print(f"  [+] Bind challenge... {NR}FAIL: {bind_res.get('message')}{R}")

    # 4. Double Reward Ad (Mengaktifkan pengali x3 reward)
    print(f"  [+] Double ad... ", end="", flush=True)
    chosen, req = None, None
    for prov in ["richads_video", "giga", "tads"]:
        res = await call_api(http_sess, "request_double_reward_ad", init_data, device_id,
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
        c = await call_api(http_sess, "complete_double_reward_ad", init_data, device_id,
                           {"mode": game_type, "ticket": ticket, "provider": chosen})
        if c.get("status") == "success":
            print(f"\r  [+] Double ad... {NG}✅ SUKSES (x{mult:.0f}){R}          ")
            require_double = True
        else:
            # Fallback jika gagal complete: tetep set true atau false sesuai respon
            print(f"\r  [+] Double ad... {NY}⚠ Ad Skipped{R}          ")
            await call_api(http_sess, "cancel_reward_ad", init_data, device_id,
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
    claim = await call_api(http_sess, "claim_faucet", init_data, device_id, {
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

# ==================== PANEL KELOLA AKUN ====================
def menu_accounts():
    """Panel Tambah Akun, Hapus Akun, dan Lihat Akun"""
    global ACCOUNTS
    while True:
        clear_screen()
        print(f"{NC}{B}╔══════════════════════════════════════════════════════════════╗{R}")
        print(f"{NC}{B}║{NP}               👥  PANEL KELOLA AKUN TELEGRAM                {NC}║{R}")
        print(f"{NC}{B}╚══════════════════════════════════════════════════════════════╝{R}\n")

        print(f"{NW}Daftar Akun Terdaftar ({len(ACCOUNTS)}):{R}")
        for i, acc in enumerate(ACCOUNTS):
            t_str = f"{NG}[Telethon: {acc.get('session_name', 'session')}]{R}" if acc.get("type") == "telethon" else f"{NY}[Direct InitData]{R}"
            print(f"  {NW}[{i+1}]{R} {B}{acc.get('name', 'Akun')}{R}  {t_str}")

        print(f"\n{NC}Pilihan Menu:{R}")
        print(f"  {NW}[1]{R} {NG}➕ Tambah Akun Baru (Telethon Login){R}")
        print(f"  {NW}[2]{R} {NY}➕ Tambah Akun Baru (Direct InitData){R}")
        print(f"  {NW}[3]{R} {NR}🗑  Hapus Akun{R}")
        print(f"  {NW}[4]{R} ✏  Ubah / Edit Akun{R}")
        print(f"  {NW}[0]{R} Kembali ke Menu Utama")
        print()

        c = input(f"{NC}➜ Pilih: {R}").strip()

        if c == '1':
            clear_screen()
            print(f"{NC}{B}── TAMBAH AKUN VIA TELETHON ──{R}\n")
            name = input(f"{NW}Nama Akun (contoh: Akun 2): {R}").strip()
            if not name:
                name = f"Akun {len(ACCOUNTS) + 1}"
            sess = input(f"{NW}Nama File Session (contoh: akun_rizka): {R}").strip()
            if not sess:
                sess = f"coinfree_session_{len(ACCOUNTS) + 1}"

            new_acc = {
                "id": int(time.time()),
                "name": name,
                "type": "telethon",
                "session_name": sess,
                "init_data": ""
            }
            ACCOUNTS.append(new_acc)
            save_accounts(ACCOUNTS)
            print(f"\n{NG}✅ Akun '{name}' berhasil ditambahkan!{R}")
            print(f"{NY}Saat farming dimulai pertama kali, Telethon akan meminta nomor HP & kode OTP.{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        elif c == '2':
            clear_screen()
            print(f"{NC}{B}── TAMBAH AKUN VIA DIRECT INITDATA ──{R}\n")
            name = input(f"{NW}Nama Akun (contoh: Akun Bot): {R}").strip()
            if not name:
                name = f"Akun {len(ACCOUNTS) + 1}"
            print(f"\n{NY}Paste query_id=... / user=... di bawah ini:{R}")
            raw = input(f"{NG}InitData: {R}").strip()
            if not raw:
                print(f"{NR}InitData kosong. Dibatalkan.{R}")
            else:
                new_acc = {
                    "id": int(time.time()),
                    "name": name,
                    "type": "init_data",
                    "session_name": "",
                    "init_data": raw
                }
                ACCOUNTS.append(new_acc)
                save_accounts(ACCOUNTS)
                print(f"\n{NG}✅ Akun '{name}' dengan Direct initData berhasil ditambahkan!{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        elif c == '3':
            clear_screen()
            print(f"{NR}{B}── HAPUS AKUN ──{R}\n")
            if not ACCOUNTS:
                print(f"{NY}Tidak ada akun untuk dihapus.{R}")
            else:
                for i, acc in enumerate(ACCOUNTS):
                    print(f"  {NW}[{i+1}]{R} {acc.get('name')}")
                del_c = input(f"\n{NR}Pilih nomor akun yang ingin dihapus (Enter=Batal): {R}").strip()
                if del_c.isdigit() and 1 <= int(del_c) <= len(ACCOUNTS):
                    idx = int(del_c) - 1
                    removed = ACCOUNTS.pop(idx)
                    save_accounts(ACCOUNTS)
                    print(f"\n{NG}✅ Akun '{removed.get('name')}' berhasil dihapus!{R}")
                else:
                    print(f"\n{NY}Dibatalkan.{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        elif c == '4':
            clear_screen()
            print(f"{NC}{B}── EDIT AKUN ──{R}\n")
            for i, acc in enumerate(ACCOUNTS):
                print(f"  {NW}[{i+1}]{R} {acc.get('name')} ({acc.get('type')})")
            ed_c = input(f"\n{NC}Pilih nomor akun yang ingin diedit: {R}").strip()
            if ed_c.isdigit() and 1 <= int(ed_c) <= len(ACCOUNTS):
                cur = ACCOUNTS[int(ed_c) - 1]
                print(f"\nNama saat ini: {cur.get('name')}")
                nn = input(f"Nama baru (Enter=tetap): ").strip()
                if nn: cur['name'] = nn
                if cur.get('type') == 'telethon':
                    print(f"Session saat ini: {cur.get('session_name')}")
                    ns = input(f"Session baru (Enter=tetap): ").strip()
                    if ns: cur['session_name'] = ns
                else:
                    print(f"InitData saat ini: {mask(cur.get('init_data'))}")
                    ni = input(f"InitData baru (Enter=tetap): ").strip()
                    if ni: cur['init_data'] = ni
                save_accounts(ACCOUNTS)
                print(f"\n{NG}✅ Data akun diperbarui!{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        elif c == '0':
            break

# ==================== MENU UTAMA SETUP ====================
def menu_setup():
    while True:
        clear_screen()
        print(f"{NC}{B}╔══════════════════════════════════════════════════════════════╗{R}")
        print(f"{NC}{B}║{NP}            ⚙  COINFREE GACOR — SETUP & PANEL                {NC}║{R}")
        print(f"{NC}{B}╚══════════════════════════════════════════════════════════════╝{R}\n")

        key_status = f"{NG}✅ {mask(CONFIG['waryono_key'])}{R}" if CONFIG.get("waryono_key") else f"{NR}❌ Belum diisi{R}"
        dev_status = f"{NG}{mask(CONFIG['device_id'])}{R}" if CONFIG.get("device_id") else f"{NY}Auto-generate per user (Gacor){R}"
        acc_status = f"{NG}{len(ACCOUNTS)} Akun Terdaftar{R}"

        print(f"  {NW}[1]{R} {NP}👥 Panel Akun (Tambah / Hapus Akun){R} → {acc_status}")
        print(f"  {NW}[2]{R} Isi / Ubah Waryono API Key         → {key_status}")
        print(f"  {NW}[3]{R} Set Custom Device ID               → {dev_status}")
        print(f"  {NW}[4]{R} Test Waryono API Key")
        print(f"  {NW}[5]{R} Reset Semua Konfigurasi")
        print(f"  {NW}[0]{R} {NG}{B}Mulai Multi-Akun Auto Farming ▶{R}")
        print()

        choice = input(f"{NC}➜ Pilih: {R}").strip()

        if choice == '1':
            menu_accounts()

        elif choice == '2':
            clear_screen()
            print(f"{NC}{B}── INPUT WARYONO API KEY ──{R}\n")
            print(f"Current: {NC}{CONFIG.get('waryono_key')}{R}\n")
            key = input(f"{NG}API Key baru (Enter=batal): {R}").strip()
            if key:
                CONFIG["waryono_key"] = key
                save_config(CONFIG)
                print(f"\n{NG}✅ Key disimpan ke {CONFIG_FILE}{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        elif choice == '3':
            clear_screen()
            print(f"{NC}{B}── SET DEVICE ID (OPSIONAL) ──{R}\n")
            cur = CONFIG.get("device_id") or "(auto)"
            print(f"Current: {NC}{cur}{R}\n")
            dev = input(f"{NG}Device ID baru (Enter=auto): {R}").strip()
            CONFIG["device_id"] = dev
            save_config(CONFIG)
            print(f"\n{NG}✅ Device ID disimpan: {dev or '(auto)'}{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        elif choice == '4':
            clear_screen()
            print(f"{NC}{B}── TEST WARYONO API KEY ──{R}\n")
            if not CONFIG.get("waryono_key"):
                print(f"{NR}❌ Key belum diisi.{R}")
            else:
                print(f"Testing key: {NC}{mask(CONFIG['waryono_key'])}{R}...")
                try:
                    r = requests.post(WARYONO_SOLVER, json={
                        "apikey": CONFIG["waryono_key"], "methods": "turnstile",
                        "domain": "https://coinfree.app", "sitekey": SITEKEY,
                        "action": "faucet_claim", "json": 1
                    }, timeout=20).json()
                    if r.get("status") == 1:
                        print(f"\n{NG}✅ API KEY AKTIF & VALID — Task ID: {r.get('request')}{R}")
                    else:
                        print(f"\n{NR}❌ Error: {r}{R}")
                except Exception as e:
                    print(f"\n{NR}❌ Request Error: {e}{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        elif choice == '5':
            clear_screen()
            print(f"{NR}{B}── RESET CONFIG ──{R}\n")
            confirm = input(f"{NR}Ketik 'ya' untuk konfirmasi reset: {R}").strip().lower()
            if confirm == 'ya':
                CONFIG["waryono_key"] = ""
                CONFIG["device_id"] = ""
                save_config(CONFIG)
                print(f"\n{NG}✅ Konfigurasi direset.{R}")
            input(f"\n{NW}Enter untuk kembali...{R}")

        elif choice == '0':
            if not CONFIG.get("waryono_key"):
                print(f"\n{NR}⚠ API key Waryono belum diisi! Set di menu [2].{R}")
                input(f"{NW}Enter untuk kembali...{R}")
                continue
            if not ACCOUNTS:
                print(f"\n{NR}⚠ Belum ada akun terdaftar! Tambah di menu [1].{R}")
                input(f"{NW}Enter untuk kembali...{R}")
                continue
            return True

# ==================== RUN SINGLE ACCOUNT CYCLE ====================
async def run_account(account):
    acc_name = account.get("name", "Akun")
    print(f"\n{NC}{B}===================================================={R}")
    print(f"{NP}{B}▶ MENJALANKAN AKUN: {acc_name}{R}")
    print(f"{NC}{B}===================================================={R}")

    http_sess = create_session()

    init_data = await get_init_data(account)
    if not init_data:
        print(f"[{acc_name}] {NR}Lewati akun ini karena gagal login.{R}")
        return

    parsed = parse_init_data(init_data)
    if not parsed or 'user' not in parsed:
        print(f"[{acc_name}] {NR}Gagal parse initData.{R}")
        return

    user_info = parsed['user']
    user_id = user_info.get('id', 0)
    username = user_info.get('username') or user_info.get('first_name', 'User')

    device_id = get_device_id(user_id)
    print(f"[{acc_name}] ID: {NW}{user_id}{R} | User: {NG}@{username}{R}")
    print(f"[{acc_name}] DeviceId: {NC}{device_id[:16]}...{R}")

    # Check user data
    ud = await get_user_data(http_sess, init_data, device_id)
    if not ud:
        print(f"[{acc_name}] {NR}Gagal mengambil user data.{R}")
        return

    bal = float(ud.get("balance", 0))
    print(f"[{acc_name}] Saldo Saat Ini: {NY}{B}{bal:.8f} {NP}{ASSET}{R}")

    # Auto klaim daily streak
    await check_and_claim_daily_streak(http_sess, init_data, device_id)

    # Farming loop per akun hingga semua game limit atau sedang cooldown
    claims_count = 0
    while True:
        ud = await get_user_data(http_sess, init_data, device_id)
        if not ud:
            break

        mode, wait = find_ready_game(ud)
        if mode is None:
            if wait >= 999999:
                print(f"[{acc_name}] {NY}Semua game sudah mencapai daily limit hari ini!{R}")
            else:
                print(f"[{acc_name}] {NC}⏳ Cooldown game terdekat: {NY}{int(wait)}s{NC}. Beralih ke akun berikutnya...{R}")
            break

        res = await process_game(http_sess, init_data, device_id, mode)
        if res == "session_invalid":
            print(f"[{acc_name}] {NY}Session kedaluwarsa, refresh session...{R}")
            init_data = await get_init_data(account, skip_start=True)
            if not init_data: break
            continue
        elif not res:
            print(f"[{acc_name}] {NY}Claim gagal / dilewati. Coba game lain...{R}")
            await asyncio.sleep(5)

        claims_count += 1
        # Beri jeda kecil agar request natural
        await asyncio.sleep(3)

# ==================== MAIN ====================
async def main():
    if not menu_setup():
        return

    clear_screen()
    print(f"{NC}{B}╔══════════════════════════════════════════════════════════════╗{R}")
    print(f"{NC}{B}║{NP}       COINFREE AUTO FARMER — GACOR MULTI-ACCOUNT             {NC}║{R}")
    print(f"{NC}{B}║{NY}         Solver: WARYONO  •  Login: Telethon / WebApp          {NC}║{R}")
    print(f"{NC}{B}╚══════════════════════════════════════════════════════════════╝{R}\n")

    while True:
        for acc in ACCOUNTS:
            try:
                await run_account(acc)
            except Exception as e:
                print(f"{NR}Error pada {acc.get('name')}: {e}{R}")

        print(f"\n{NC}✨ Putaran semua akun selesai. Re-checking dalam 60 detik...{R}")
        countdown_timer(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{NY}Bot dihentikan oleh user.{R}")
    except Exception as e:
        print(f"\n{NR}Error: {e}{R}")

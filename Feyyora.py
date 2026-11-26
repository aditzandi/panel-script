import os
import sys
import time
import json
import re
import base64
import io
import requests
from PIL import Image, ImageDraw, ImageFont

def generate_yt_screenshot(title: str, handle: str) -> str:
    """
    Generates a realistic mobile-style YouTube channel screenshot
    with 'Disubscribe' (Subscribed) active state.
    Returns: base64-encoded JPEG string.
    """
    W, H = 720, 1280
    BG_COLOR = (15, 15, 15)
    CARD_BG = (39, 39, 39)
    TEXT_WHITE = (241, 241, 241)
    TEXT_GRAY = (170, 170, 170)
    BANNER_COLOR = (30, 40, 55)
    AVATAR_BG = (100, 110, 130)
    
    img = Image.new('RGB', (W, H), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    font_paths = [
        "arial.ttf",
        "/system/fonts/Roboto-Regular.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf"
    ]
    font_file = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_file = fp
            break

    try:
        if font_file:
            font_title = ImageFont.truetype(font_file, 36)
            font_handle = ImageFont.truetype(font_file, 24)
            font_sub = ImageFont.truetype(font_file, 26)
            font_nav = ImageFont.truetype(font_file, 26)
        else:
            font_title = ImageFont.load_default(size=36) if hasattr(ImageFont, 'load_default') and 'size' in ImageFont.load_default.__code__.co_varnames else ImageFont.load_default()
            font_handle = font_title
            font_sub = font_title
            font_nav = font_title
    except:
        font_title = ImageFont.load_default()
        font_handle = font_title
        font_sub = font_title
        font_nav = font_title

    # 1. Top Bar
    draw.rectangle([0, 0, W, 80], fill=(15, 15, 15))
    draw.text((40, 25), "<-", fill=TEXT_WHITE, font=font_title)
    draw.text((100, 25), handle if handle.startswith('@') else f"@{handle}", fill=TEXT_WHITE, font=font_title)
    
    # 2. Channel Banner
    draw.rectangle([0, 80, W, 260], fill=BANNER_COLOR)
    
    # 3. Avatar Circle
    draw.ellipse([40, 230, 140, 330], fill=AVATAR_BG)
    draw.ellipse([42, 232, 138, 328], fill=(50, 60, 80))
    
    # 4. Channel Title & Info
    draw.text((40, 350), title[:30], fill=TEXT_WHITE, font=font_title)
    h_str = handle if handle.startswith('@') else f"@{handle}"
    draw.text((40, 400), f"{h_str} \u2022 12.5 rb subscriber \u2022 145 video", fill=TEXT_GRAY, font=font_handle)
    draw.text((40, 435), "Channel resmi video gameplay & tutorial ...selengkapnya", fill=TEXT_GRAY, font=font_handle)
    
    # 5. Button 'Disubscribe' active state
    draw.rounded_rectangle([40, 480, 280, 540], radius=30, fill=CARD_BG)
    draw.text((65, 495), "\U0001F514 Disubscribe", fill=TEXT_WHITE, font=font_sub)
    
    # Join button
    draw.rounded_rectangle([300, 480, 460, 540], radius=30, fill=CARD_BG)
    draw.text((340, 495), "Gabung", fill=TEXT_WHITE, font=font_sub)
    
    # 6. Tab bar
    draw.text((40, 570), "Beranda", fill=TEXT_WHITE, font=font_nav)
    draw.rectangle([40, 605, 140, 608], fill=TEXT_WHITE)
    draw.text((180, 570), "Video", fill=TEXT_GRAY, font=font_nav)
    draw.text((290, 570), "Shorts", fill=TEXT_GRAY, font=font_nav)
    draw.text((410, 570), "Playlist", fill=TEXT_GRAY, font=font_nav)
    draw.line([0, 610, W, 610], fill=(45, 45, 45), width=1)
    
    # 7. Video feed preview
    draw.rectangle([40, 640, W - 40, 940], fill=(30, 30, 30))
    draw.ellipse([40, 960, 90, 1010], fill=AVATAR_BG)
    draw.text((110, 960), f"Video Terbaru - {title[:25]}", fill=TEXT_WHITE, font=font_handle)
    draw.text((110, 995), f"{title[:20]} \u2022 1.2 rb x ditonton \u2022 1 hari lalu", fill=TEXT_GRAY, font=font_handle)
    
    # Save & Base64
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

# ================= KREDENSIAL DEFAULT =================
DEFAULT_APIKEY     = "f7457613bf1330fe8086b923de6dbccd"
DEFAULT_EMAIL      = "cyberex04@gmail.com"
DEFAULT_PASSWORD   = "1januari2013"
DEFAULT_YT_USER_ID = "799542"
DEFAULT_YT_APP_ID  = "app_2ab9f91c84656ac5b078cc0f"
# ======================================================

HOST               = "https://feyorra.top"
IN_URL             = "https://api.waryono.my.id/in.php"
RES_URL            = "https://api.waryono.my.id/res.php"
TURNSTILE_SITEKEY  = "0x4AAAAAAA3a78IiE1GGrmei"
CONFIG_FILE        = "Feyyora.json"

# ANSI Colors
HITAM  = "\033[0;30m"
MERAH  = "\033[0;31m"
HIJAU  = "\033[0;32m"
KUNING = "\033[0;33m"
BIRU   = "\033[0;34m"
CYAN   = "\033[0;36m"
PUTIH  = "\033[0;37m"
RESET  = "\033[0m"

# Inisialisasi HTTP Session
session = requests.Session()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def timer(seconds, prefix="[!] please wait"):
    wait_time = int(seconds)
    frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
    frame_count = len(frames)
    current_frame = 0
    frame_delay = 0.1

    while wait_time > 0:
        start_time = time.time()
        while (time.time() - start_time) < 1:
            hours = wait_time // 3600
            minutes = (wait_time % 3600) // 60
            secs = wait_time % 60
            formatted = f"{hours:02d}:{minutes:02d}:{secs:02d}"
            spinner = frames[current_frame]
            sys.stdout.write(f"\r{PUTIH}{prefix}{HIJAU} {formatted} {PUTIH}{spinner}")
            sys.stdout.flush()
            time.sleep(frame_delay)
            current_frame = (current_frame + 1) % frame_count
            if (time.time() - start_time) >= 1:
                break
        wait_time -= 1
    sys.stdout.write("\r" + " " * 45 + "\r")
    sys.stdout.flush()

def load_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {
            "apikey": DEFAULT_APIKEY,
            "email": DEFAULT_EMAIL,
            "password": DEFAULT_PASSWORD,
            "yt_user_id": DEFAULT_YT_USER_ID,
            "yt_app_id": DEFAULT_YT_APP_ID
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return cfg
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if not cfg.get("apikey"): cfg["apikey"] = DEFAULT_APIKEY
            if not cfg.get("email"): cfg["email"] = DEFAULT_EMAIL
            if not cfg.get("password"): cfg["password"] = DEFAULT_PASSWORD
            if not cfg.get("yt_user_id"): cfg["yt_user_id"] = DEFAULT_YT_USER_ID
            if not cfg.get("yt_app_id"): cfg["yt_app_id"] = DEFAULT_YT_APP_ID
            return cfg
    except:
        return {
            "apikey": DEFAULT_APIKEY,
            "email": DEFAULT_EMAIL,
            "password": DEFAULT_PASSWORD,
            "yt_user_id": DEFAULT_YT_USER_ID,
            "yt_app_id": DEFAULT_YT_APP_ID
        }

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

def cloud_solve(apikey, sitekey, method):
    headers = {"Content-Type": "application/json"}
    body = {
        "apikey": apikey,
        "methods": method,
        "domain": HOST,
        "sitekey": sitekey,
        "json": 1
    }
    try:
        r = requests.post(IN_URL, json=body, headers=headers, timeout=30)
        res_text = r.text
        if "ERROR_" in res_text:
            print(f"{PUTIH}Error: {MERAH}{res_text.strip()}")
            return None
        j = r.json()
        if j.get("status") != 1 or not j.get("request"):
            print(f"{PUTIH}Error: {MERAH}in.php respon invalid")
            return None
        task_id = j["request"]
    except Exception as e:
        print(f"{PUTIH}Error solve in: {MERAH}{e}")
        return None

    while True:
        timer(3, "  cf")
        try:
            url = f"{RES_URL}?apikey={apikey}&id={task_id}&action=get&json=1"
            r = requests.get(url, timeout=30)
            rj = r.json()
            if rj.get("request") == "CAPCHA_NOT_READY":
                sys.stdout.write(f"\r{PUTIH}Status: {MERAH}CAPCHA_NOT_READY")
                sys.stdout.flush()
                time.sleep(1.8)
                sys.stdout.write("\r" + " " * 45 + "\r")
                sys.stdout.flush()
                continue
            if "ERROR_" in r.text:
                print(f"{PUTIH}Error: {MERAH}{r.text.strip()}")
                return None
            if rj.get("status") == 1 and rj.get("request"):
                return rj["request"]
        except Exception as e:
            time.sleep(2)

def check_login():
    headers = {
        "host": "feyorra.top",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "referer": "https://feyorra.top/"
    }
    try:
        r = session.get(f"{HOST}/dashboard", headers=headers, timeout=30)
        return "Dashboard" in r.text and "Sign In" not in r.text
    except:
        return False

def do_login(apikey, email, pwd):
    print(f"{PUTIH}[LOGIN] Mengambil halaman login...")
    headers = {
        "host": "feyorra.top",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "referer": "https://feyorra.top/"
    }
    try:
        r = session.get(f"{HOST}/login", headers=headers, timeout=30)
    except Exception as e:
        print(f"{MERAH}[LOGIN] Gagal koneksi: {e}{RESET}")
        return False

    m_csrf = re.search(r'name="csrf_token_name" value="([^"]+)"', r.text)
    if not m_csrf:
        print(f"{MERAH}[LOGIN] CSRF Token tidak ditemukan.{RESET}")
        return False
    csrf = m_csrf.group(1)

    m_key = re.search(r'data-sitekey="(0x4[A-Za-z0-9]+)"', r.text)
    login_sitekey = m_key.group(1) if m_key else TURNSTILE_SITEKEY
    print(f"{PUTIH}[LOGIN] Sitekey: {CYAN}{login_sitekey}")

    print(f"{PUTIH}[LOGIN] Solving Turnstile...")
    cap = cloud_solve(apikey, login_sitekey, "turnstile")
    if not cap:
        print(f"{MERAH}[LOGIN] Gagal solve Turnstile.{RESET}")
        return False

    print(f"{PUTIH}[LOGIN] Mengirim data login...")
    payload = {
        "csrf_token_name": csrf,
        "email": email,
        "password": pwd,
        "captcha": "turnstile",
        "cf-turnstile-response": cap,
        "g-recaptcha-response": cap
    }
    post_headers = headers.copy()
    post_headers["content-type"] = "application/x-www-form-urlencoded"
    post_headers["origin"] = "https://feyorra.top"
    post_headers["referer"] = "https://feyorra.top/login"

    try:
        session.post(f"{HOST}/auth/login", data=payload, headers=post_headers, timeout=30)
    except Exception as e:
        print(f"{MERAH}[LOGIN] Gagal submit form: {e}{RESET}")
        return False

    if check_login():
        print(f"{HIJAU}[LOGIN] Berhasil login!{RESET}")
        return True

    print(f"{MERAH}[LOGIN] Gagal login. Cek email/password.{RESET}")
    return False

def get_balance():
    headers = {
        "host": "feyorra.top",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "referer": "https://feyorra.top/"
    }
    try:
        dash = session.get(f"{HOST}/dashboard", headers=headers, timeout=30).text
        m = re.search(r'Main Balance</h3>\s*<p>([^<]+)</p>', dash)
        return m.group(1) if m else "Unknown"
    except:
        return "Unknown"

# --- 1. FAUCET CLAIM ---
def claim_faucet_once(apikey):
    headers = {
        "host": "feyorra.top",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "referer": "https://feyorra.top/"
    }
    post_headers = headers.copy()
    post_headers["origin"] = "https://feyorra.top"
    post_headers["content-type"] = "application/x-www-form-urlencoded"
    post_headers["referer"] = "https://feyorra.top/faucet"

    try:
        r = session.get(f"{HOST}/faucet", headers=headers, timeout=30)
        faucet = r.text
    except Exception as e:
        print(f"{MERAH}[FAUCET] Gagal request: {e}{RESET}")
        return {"status": "error"}

    if re.search(r'Daily Limit reached|Daily limit reached|You have reached the limit', faucet, re.I):
        print(f"{MERAH}[FAUCET] Daily Limit reached!{RESET}")
        return {"status": "limit"}
    if "complete shortlink" in faucet:
        print(f"{KUNING}[FAUCET] Selesaikan Shortlink dulu! Skip faucet.{RESET}")
        return {"status": "shortlink"}

    m_lock = re.search(r'Earn <b>(\d+) more coins</b>', faucet, re.I)
    if m_lock:
        print(f"{KUNING}[FAUCET] Faucet terkunci (butuh {m_lock.group(1)} Coins lagi). Farming task lain dulu...{RESET}")
        return {"status": "locked"}

    m_csrf = re.search(r'<input[^>]*name="csrf_token_name"[^>]*value="([^"]+)"', faucet, re.I)
    m_tok = re.search(r'<input[^>]*name="token"[^>]*value="([^"]+)"', faucet, re.I)

    if m_csrf and m_tok:
        csrf = m_csrf.group(1)
        tok = m_tok.group(1)
        print(f"{PUTIH}[FAUCET] Ready to claim! Solving Turnstile...{RESET}")
        cap = cloud_solve(apikey, TURNSTILE_SITEKEY, "turnstile")
        if cap:
            data = {
                "csrf_token_name": csrf,
                "token": tok,
                "captcha": "turnstile",
                "cf-turnstile-response": cap,
                "g-recaptcha-response": cap
            }
            try:
                c_res = session.post(f"{HOST}/faucet/verify", data=data, headers=post_headers, timeout=30)
                claim = c_res.text
                m_win = re.search(r"title:\s*'([\d\.]+) Coins has been added to your balance'", claim, re.I)
                if m_win:
                    got = m_win.group(1)
                    print(f"{PUTIH}[FAUCET] {HIJAU}Claim Success! (+{got} Coins){RESET}")
                    m_wait = re.search(r'(?:var|let) wait = (\d+) -', claim)
                    wait_sec = int(m_wait.group(1)) + 5 if m_wait else 245
                    return {"status": "cooldown", "wait": wait_sec}
                else:
                    m_fail = re.search(r'alert-danger">.*?</i>\s*([^<]+)', claim, re.S)
                    err = m_fail.group(1).strip() if m_fail else "Respon tidak dikenal"
                    print(f"{PUTIH}[FAUCET] {MERAH}{err}{RESET}")
                    return {"status": "cooldown", "wait": 60}
            except Exception as e:
                print(f"{MERAH}[FAUCET] Gagal submit: {e}{RESET}")
                return {"status": "error"}
    else:
        wait_time = 0
        m_wait = re.search(r'var wait = (\d+)', faucet, re.I)
        if m_wait:
            wait_time = int(m_wait.group(1))
        else:
            m_t = re.search(r'<b id="minute">\s*(\d+)\s*</b>\s*:\s*<b id="second">\s*(\d+)\s*</b>', faucet, re.I)
            if m_t:
                wait_time = (int(m_t.group(1)) * 60) + int(m_t.group(2))
        return {"status": "cooldown", "wait": wait_time if wait_time > 0 else 60}

# --- 2. PTC ADS ---
def run_ptc_once(apikey):
    headers = {
        "host": "feyorra.top",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "referer": "https://feyorra.top/"
    }
    try:
        r = session.get(f"{HOST}/ptc", headers=headers, timeout=30)
        ptc_ids = list(set(re.findall(r"window\.location\s*=\s*'https://feyorra\.top/ptc/view/(\d+)'", r.text, re.I)))
    except Exception as e:
        print(f"{MERAH}[PTC] Gagal ambil list: {e}{RESET}")
        return 0

    if not ptc_ids:
        print(f"{PUTIH}[PTC] Tidak ada iklan internal yang tersedia.{RESET}")
        return 0

    print(f"{PUTIH}[PTC] Ditemukan {len(ptc_ids)} iklan internal.{RESET}")
    claimed = 0
    for pid in ptc_ids:
        print(f"{PUTIH}[PTC] Memproses ID: {CYAN}{pid}{RESET}")
        try:
            view = session.get(f"{HOST}/ptc/view/{pid}", headers=headers, timeout=30).text
        except:
            continue

        m_key = re.search(r'data-sitekey="(0x4[A-Za-z0-9]+)"', view)
        ptc_sitekey = m_key.group(1) if m_key else TURNSTILE_SITEKEY

        m_timer = re.search(r'let timer = (\d+);', view, re.I)
        dur = int(m_timer.group(1)) if m_timer else 10
        timer(dur, "  wait")

        m1 = re.search(r'<input[^>]*name="csrf_token_name"[^>]*value="([^"]+)"', view, re.I)
        m2 = re.search(r'<input[^>]*name="token"[^>]*value="([^"]+)"', view, re.I)

        if m1 and m2:
            csrf = m1.group(1)
            tok = m2.group(1)
            print(f"{PUTIH}[PTC] Solving Turnstile...")
            cap = cloud_solve(apikey, ptc_sitekey, "turnstile")
            if cap:
                p_data = {
                    "captcha": "turnstile",
                    "cf-turnstile-response": cap,
                    "g-recaptcha-response": cap,
                    "csrf_token_name": csrf,
                    "token": tok
                }
                b_hd = headers.copy()
                b_hd["origin"] = "https://feyorra.top"
                b_hd["content-type"] = "application/x-www-form-urlencoded"
                b_hd["referer"] = f"https://feyorra.top/ptc/view/{pid}"
                try:
                    v_res = session.post(f"{HOST}/ptc/verify/{pid}", data=p_data, headers=b_hd, timeout=30).text
                    m_win = re.search(r"title:\s*'([\d\.]+) Coins has been added to your balance'", v_res, re.I)
                    if m_win:
                        print(f"{PUTIH}[PTC] {HIJAU}Berhasil klaim iklan #{pid} (+{m_win.group(1)} Coins){RESET}")
                        claimed += 1
                    else:
                        print(f"{PUTIH}[PTC] {MERAH}Gagal klaim iklan #{pid}{RESET}")
                except Exception as e:
                    print(f"{MERAH}[PTC] Error submit: {e}{RESET}")
        time.sleep(2)
    return claimed

# --- 3. YOUTUBE AVISO ---
def run_aviso_tasks():
    print(f"{PUTIH}[AVISO] Memeriksa task video YouTube Aviso...{RESET}")
    headers = {
        "host": "feyorra.top",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
        "accept": "*/*",
        "referer": "https://feyorra.top/"
    }
    try:
        yt_page = session.get(f"{HOST}/offerwall/youtube", headers=headers, timeout=30).text
    except Exception as e:
        print(f"{MERAH}[AVISO] Gagal koneksi: {e}{RESET}")
        return 0

    conf = {}
    m1 = re.search(r'data-api-key="([^"]+)"', yt_page)
    m2 = re.search(r'data-user-hash="([^"]+)"', yt_page)
    m3 = re.search(r'data-user-id="([^"]+)"', yt_page)
    m4 = re.search(r'data-user-sig="([^"]+)"', yt_page)
    if not (m1 and m2 and m3 and m4):
        print(f"{KUNING}[AVISO] Aviso offerwall tidak aktif/belum login.{RESET}")
        return 0

    conf['api_key'] = m1.group(1)
    conf['hash'] = m2.group(1)
    conf['user_id'] = m3.group(1)
    conf['user_sig'] = m4.group(1)

    aviso_hd = {
        "host": "aviso.bz",
        "content-type": "application/json",
        "x-api-key": conf['api_key'],
        "origin": "https://feyorra.top",
        "referer": "https://feyorra.top/",
        "user-agent": headers["user-agent"],
        "accept": "*/*"
    }
    platform = "Linux+armv81"
    avail_url = f"https://aviso.bz/api/v1/youtube/tasks/available?hash={conf['hash']}&platform={platform}"
    try:
        r = requests.get(avail_url, headers=aviso_hd, timeout=30)
        tasks = r.json().get('ads', [])
    except:
        return 0

    if not tasks:
        print(f"{PUTIH}[AVISO] Tidak ada video Aviso tersedia.{RESET}")
        return 0

    print(f"{PUTIH}[AVISO] Ditemukan {len(tasks)} video Aviso.{RESET}")
    count = 0
    for t in tasks:
        tid = t['id']
        dur = t['duration']
        amt = t['amount']
        print(f"{PUTIH}[AVISO] Tonton Task ID: {tid} (Durasi: {dur}s)...{RESET}")

        start_body = {
            "taskId": tid, "hash": conf['hash'], "type": "ads",
            "platform": "Linux armv81", "userId": conf['user_id'], "userSig": conf['user_sig']
        }
        try:
            res_st = requests.post("https://aviso.bz/api/v1/youtube/tasks/start", json=start_body, headers=aviso_hd, timeout=30).json()
            att_id = res_st.get('attemptId')
            if not att_id:
                continue

            timer_url = "https://aviso.bz/api/v1/youtube/tasks/timer-status"
            requests.post(timer_url, json={"attemptId": att_id, "action": "start"}, headers=aviso_hd, timeout=30)
            timer(dur + 3, "  watching")
            time.sleep(2)

            res_comp = requests.post(timer_url, json={"attemptId": att_id, "action": "complete", "watchedTime": dur}, headers=aviso_hd, timeout=30).json()
            stat = res_comp.get('status', 'unknown')
            if stat in ['good', 'verified', 'need_check', 'success']:
                requests.post(timer_url, json={"attemptId": att_id, "action": "check"}, headers=aviso_hd, timeout=30)
                fin = requests.post("https://aviso.bz/api/v1/youtube/tasks/complete", json={"attemptId": att_id}, headers=aviso_hd, timeout=30).text
                if '"earned"' in fin or '"success"' in fin:
                    print(f"{HIJAU}[AVISO] Success! (+${amt}){RESET}")
                    count += 1
        except Exception as e:
            print(f"{MERAH}[AVISO] Error: {e}{RESET}")
        time.sleep(2)
    return count

# --- 4. YOUTUBE SUBSCRIBE (MAKEYOUTASK) ---
def run_yt_sub_once(app_id, user_id):
    headers = {
        "accept": "*/*",
        "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "origin": "https://feyorra.top",
        "referer": "https://feyorra.top/",
        "sec-ch-ua": '"Chromium";v="158", "Not.A/Brand";v="24", "Google Chrome";v="158"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36"
    }

    task_url = f"https://makeyoutask.com/wall/task_api?app_id={app_id}&user_id={user_id}"
    try:
        r = requests.get(task_url, headers=headers, timeout=30)
        data = r.json()
    except Exception as e:
        print(f"{MERAH}[YT-SUB] Gagal membaca API: {e}{RESET}")
        return {"status": "error", "wait": 10}

    status = data.get("status", "unknown")
    if status == "cooldown":
        cd = int(data.get("retry_after", 60))
        print(f"{KUNING}[YT-SUB] Cooldown aktif: {cd}s.{RESET}")
        return {"status": "cooldown", "wait": cd}

    if status in ["daily_limit", "network_limit"]:
        print(f"{MERAH}[YT-SUB] Limit tercapai: {data.get('message', status)}{RESET}")
        return {"status": "limit"}

    if status != "available" or not data.get("task"):
        msg = data.get("message", "Tidak ada task subscribe saat ini.")
        print(f"{PUTIH}[YT-SUB] {msg}{RESET}")
        return {"status": "no_task", "wait": 30}

    task = data["task"]
    job_id = str(task["id"])
    ch_title = task.get("title") or task.get("channel_handle") or "YouTube Channel"
    ch_handle = task.get("channel_handle") or ch_title
    reward = task.get("reward", "?")
    curr = task.get("currency", "Coins")
    min_wait = int(task.get("min_wait_sec", 10))

    print(f"{HIJAU}[YT-SUB] Ditemukan Task #{job_id}!{RESET}")
    print(f"{PUTIH}         Target : {CYAN}{ch_title}{PUTIH} ({KUNING}{ch_handle}{PUTIH}){RESET}")
    print(f"{PUTIH}         Reward : {HIJAU}+{reward} {curr}{RESET}")

    print(f"{PUTIH}[YT-SUB] Generate proof via yt_generator...{RESET}")
    try:
        b64_img = generate_yt_screenshot(ch_title, ch_handle)
        img_bytes = base64.b64decode(b64_img)
        print(f"{HIJAU}[YT-SUB] Screenshot proof siap ({round(len(img_bytes)/1024, 1)} KB).{RESET}")
    except Exception as e:
        print(f"{MERAH}[YT-SUB] Gagal generate screenshot: {e}{RESET}")
        return {"status": "error", "wait": 5}

    wait_sec = max(min_wait, 10)
    timer(wait_sec, "  waiting min_wait_sec...")

    print(f"{PUTIH}[YT-SUB] Mengirimkan bukti ke makeyoutask...{RESET}")
    submit_url = "https://makeyoutask.com/wall/submit_proof"
    files = {'proof_screenshot': ('Screenshot_1.png', img_bytes, 'image/png')}
    form_data = {
        'app_id': app_id,
        'user_id': str(user_id),
        'job_id': str(job_id),
        'response_mode': 'json'
    }

    try:
        sub_res = requests.post(submit_url, data=form_data, files=files, headers=headers, timeout=45)
        sj = sub_res.json()
        if sj.get("status") == "success":
            msg = sj.get("message", "Task approved and reward credited.")
            print(f"{HIJAU}[YT-SUB] SUCCESS! {PUTIH}{msg}{RESET}")
            return {"status": "success"}
        elif sj.get("status") == "cooldown":
            cd = int(sj.get("retry_after", 60))
            print(f"{KUNING}[YT-SUB] Cooldown: {cd}s.{RESET}")
            return {"status": "cooldown", "wait": cd}
        else:
            print(f"{MERAH}[YT-SUB] Gagal: {sj.get('message', sub_res.text)}{RESET}")
            return {"status": "error", "wait": 10}
    except Exception as e:
        print(f"{MERAH}[YT-SUB] Error saat submit: {e}{RESET}")
        return {"status": "error", "wait": 10}

# --- SMART BOT ENGINE (ALL-IN-ONE) ---
def run_smart_bot(apikey, yt_app, yt_user):
    print(f"{CYAN}=============================================={RESET}")
    print(f"{HIJAU}      [SMART BOT] AUTO FARMING STARTED{RESET}")
    print(f"{PUTIH}   Prioritas Utama : FAUCET CLAIM{RESET}")
    print(f"{PUTIH}   Farming Rotasi  : YouTube Sub + PTC + Aviso{RESET}")
    print(f"{CYAN}=============================================={RESET}")

    next_faucet_time = 0
    next_yt_sub_time = 0
    faucet_locked = False

    while True:
        now = time.time()
        print(f"\n{PUTIH}[SMART] Saldo Sekarang : {CYAN}{get_balance()} Coins{RESET}")

        # ---------------- PRIORITAS UTAMA: FAUCET ----------------
        if now >= next_faucet_time:
            print(f"{PUTIH}\n--- [PRIORITAS 1] Memeriksa Faucet ---{RESET}")
            f_res = claim_faucet_once(apikey)
            status = f_res.get("status")

            if status == "cooldown":
                wait_sec = f_res.get("wait", 60)
                next_faucet_time = time.time() + wait_sec
                faucet_locked = False
                print(f"{HIJAU}[FAUCET] Sukses/Cooldown aktif: {wait_sec}s. Faucet aman!{RESET}")
            elif status == "locked":
                faucet_locked = True
                print(f"{KUNING}[FAUCET TERKUNCI] Butuh koin untuk unlock faucet! Mengaktifkan rotasi farming (YT Sub, PTC, Aviso)...{RESET}")
            elif status == "limit":
                print(f"{MERAH}[FAUCET] Limit harian tercapai. Lanjut rotasi farming.{RESET}")
                next_faucet_time = time.time() + 7200
                faucet_locked = False
            elif status == "shortlink":
                print(f"{KUNING}[FAUCET] Faucet butuh shortlink. Lanjut rotasi farming.{RESET}")
                next_faucet_time = time.time() + 600
                faucet_locked = False
            else:
                next_faucet_time = time.time() + 60
        else:
            sisa_fc = int(next_faucet_time - now)
            print(f"{PUTIH}[SMART] Faucet cooldown: {KUNING}{sisa_fc}s{RESET}")

        # ---------------- ROTASI FARMING (2, 3, 4) ----------------
        # Dijalankan saat faucet sedang terkunci (locked) atau sedang menunggu cooldown faucet
        need_farming = faucet_locked or (now < next_faucet_time)

        if need_farming:
            # 2. Farming YouTube Subscribe (MakeYouTask)
            if now >= next_yt_sub_time:
                print(f"{PUTIH}\n--- [ROTASI 1] Farming YouTube Subscribe ---{RESET}")
                yt_res = run_yt_sub_once(yt_app, yt_user)
                if yt_res.get("status") == "cooldown":
                    next_yt_sub_time = time.time() + yt_res.get("wait", 60)
                elif yt_res.get("status") == "success":
                    next_yt_sub_time = time.time() + 60
                elif yt_res.get("status") == "no_task":
                    next_yt_sub_time = time.time() + 30
                elif yt_res.get("status") == "limit":
                    next_yt_sub_time = time.time() + 3600
            else:
                sisa_yt = int(next_yt_sub_time - now)
                print(f"{PUTIH}[SMART] YouTube Subscribe cooldown: {KUNING}{sisa_yt}s{RESET}")

            # 3. Farming PTC Internal Feyorra
            print(f"{PUTIH}\n--- [ROTASI 2] Farming PTC Ads ---{RESET}")
            run_ptc_once(apikey)

            # 4. Farming YouTube Video Aviso
            print(f"{PUTIH}\n--- [ROTASI 3] Farming YouTube Aviso ---{RESET}")
            run_aviso_tasks()

            # Jika sebelumnya faucet terkunci, langsung reset timer faucet agar dicoba dicek lagi
            if faucet_locked:
                print(f"{HIJAU}[SMART] Rotasi selesai, cek ulang status koin & unlock Faucet...{RESET}")
                next_faucet_time = 0

        # Standby hitung mundur timer
        now = time.time()
        candidates = []
        if next_faucet_time > now:
            candidates.append(next_faucet_time - now)
        if next_yt_sub_time > now:
            candidates.append(next_yt_sub_time - now)

        wait_for = 15
        if candidates:
            wait_for = max(5, int(min(candidates)))
        
        wait_for = min(wait_for, 45)
        timer(wait_for, "  standby loop...")

def main():
    cfg = load_config()
    apikey   = cfg['apikey']
    email    = cfg['email']
    pwd      = cfg['password']
    yt_user  = cfg['yt_user_id']
    yt_app   = cfg['yt_app_id']

    while True:
        clear_screen()
        print(f"{CYAN}==============================================")
        print(f"{PUTIH}       FEYORRA AUTO BOT (PYTHON EDITION)")
        print(f"{HIJAU}       Dev: MoneyMaker_w / Smart Bot")
        print(f"{CYAN}=============================================={RESET}")
        print(" [1] Config Akun (Email, Password, API Key & YT)")
        print(" [2] Run Smart Bot (Auto Faucet + PTC + Aviso + YT Sub)")
        print(" [0] Exit")
        print(f"{CYAN}=============================================={RESET}")
        opt = input(f"{KUNING} Pilih > {RESET}").strip()

        if opt == '1':
            clear_screen()
            print(f"{CYAN}=== UPDATE CONFIG AKUN ==={RESET}")
            print(f"{PUTIH}(Tekan ENTER jika tidak ingin mengubah nilai){RESET}\n")
            newkey = input(f"{PUTIH}API Key Waryono (sekarang: {apikey}) : {KUNING}").strip()
            newemail = input(f"{PUTIH}Email Feyorra   (sekarang: {email}) : {KUNING}").strip()
            newpass = input(f"{PUTIH}Password Baru   : {KUNING}").strip()
            new_user = input(f"{PUTIH}MakeYouTask User ID (sekarang: {yt_user}) : {KUNING}").strip()
            new_app = input(f"{PUTIH}MakeYouTask App ID  (sekarang: {yt_app}) : {KUNING}").strip()

            if newkey:   cfg['apikey']     = newkey
            if newemail: cfg['email']      = newemail
            if newpass:  cfg['password']   = newpass
            if new_user: cfg['yt_user_id'] = new_user
            if new_app:  cfg['yt_app_id']  = new_app

            save_config(cfg)
            apikey  = cfg['apikey']
            email   = cfg['email']
            pwd     = cfg['password']
            yt_user = cfg['yt_user_id']
            yt_app  = cfg['yt_app_id']

            session.cookies.clear()
            print(f"\n{HIJAU}Config berhasil disimpan dan cookie di-reset!{RESET}")
            time.sleep(2)

        elif opt == '2':
            clear_screen()
            if not check_login():
                print(f"{KUNING}Memeriksa sesi login Feyorra...{RESET}")
                if not do_login(apikey, email, pwd):
                    print(f"{MERAH}Login gagal! Periksa email/password di menu [1] Config.{RESET}")
                    input(f"{PUTIH}Tekan Enter untuk kembali...{RESET}")
                    continue
            else:
                print(f"{HIJAU}Sesi login valid.{RESET}")

            run_smart_bot(apikey, yt_app, yt_user)
            input(f"\n{PUTIH}Tekan Enter untuk kembali ke menu...{RESET}")

        elif opt == '0':
            sys.exit(0)

if __name__ == "__main__":
    main()

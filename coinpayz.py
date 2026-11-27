#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
======================================================================
           MAKEYOUTASK BOT - STANDALONE EDITION
   Auto YouTube Subscribe Proof Generator & Auto Task Submitter
   Features:
   - 100% Standalone (yt_generator embedded directly inside)
   - Synchronized with server cooldown (10 minutes countdown sync)
   - 2 Menu Panel: [1] Login Cookie, [2] Start Bot
   - Headless / No browser required
======================================================================
"""

import os
import sys
import time
import json
import re
import base64
import io
import html
from bs4 import BeautifulSoup
import curl_cffi
from curl_cffi import requests
from PIL import Image, ImageDraw, ImageFont

# ================= ANSI COLORS =================
HITAM  = "\033[0;30m"
MERAH  = "\033[0;31m"
HIJAU  = "\033[0;32m"
KUNING = "\033[0;33m"
BIRU   = "\033[0;34m"
CYAN   = "\033[0;36m"
PUTIH  = "\033[0;37m"
RESET  = "\033[0m"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config_makeyoutask.json")
BASE_URL = "https://makeyoutask.com"
TASKS_URL = "https://makeyoutask.com/tasks"

# ================= SCREENSHOT GENERATOR ENGINE (EMBEDDED) =================
def generate_yt_screenshot(title: str, handle: str, avatar_url: str = None) -> str:
    """
    Generates a realistic mobile-style YouTube channel screenshot
    with 'Disubscribe' (Subscribed) active state.
    Embeds channel avatar if available.
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
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
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
            font_title = ImageFont.truetype(font_file, 34)
            font_handle = ImageFont.truetype(font_file, 22)
            font_sub = ImageFont.truetype(font_file, 25)
            font_nav = ImageFont.truetype(font_file, 24)
        else:
            font_title = ImageFont.load_default()
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
    h_display = handle if handle.startswith('@') else f"@{handle}"
    draw.text((100, 25), h_display, fill=TEXT_WHITE, font=font_title)

    # 2. Channel Banner
    draw.rectangle([0, 80, W, 260], fill=BANNER_COLOR)

    # 3. Avatar Circle
    avatar_pasted = False
    if avatar_url:
        try:
            r = requests.get(avatar_url, timeout=10)
            if r.status_code == 200:
                av_img = Image.open(io.BytesIO(r.content)).convert('RGBA')
                av_img = av_img.resize((100, 100), Image.Resampling.LANCZOS)
                mask = Image.new('L', (100, 100), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 100, 100), fill=255)
                img.paste(av_img, (40, 230), mask)
                avatar_pasted = True
        except Exception:
            avatar_pasted = False

    if not avatar_pasted:
        draw.ellipse([40, 230, 140, 330], fill=AVATAR_BG)
        draw.ellipse([42, 232, 138, 328], fill=(50, 60, 80))

    # 4. Channel Title & Info
    draw.text((40, 350), title[:30], fill=TEXT_WHITE, font=font_title)
    draw.text((40, 395), f"{h_display} \u2022 14.8 rb subscriber \u2022 182 video", fill=TEXT_GRAY, font=font_handle)
    draw.text((40, 430), "Channel resmi video & info ...selengkapnya", fill=TEXT_GRAY, font=font_handle)

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
    draw.text((110, 995), f"{title[:20]} \u2022 2.5 rb x ditonton \u2022 2 hari lalu", fill=TEXT_GRAY, font=font_handle)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

# ================= HELPER FUNCTIONS =================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def timer(seconds, prefix="[!] Menunggu"):
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
    sys.stdout.write("\r" + " " * 65 + "\r")
    sys.stdout.flush()

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"cookie": ""}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"cookie": ""}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

def parse_cookies_dict(cookie_str):
    cookies = {}
    if not cookie_str:
        return cookies
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies

def get_session():
    cfg = load_config()
    cookie_str = cfg.get("cookie", "")
    s = requests.Session(impersonate="chrome124")
    cookies = parse_cookies_dict(cookie_str)
    s.cookies.update(cookies)
    s.headers.update({
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'referer': 'https://makeyoutask.com/',
        'sec-ch-ua': '"Chromium";v="158", "Not.A/Brand";v="24", "Google Chrome";v="158"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36'
    })
    return s

def check_login(session=None):
    """Memeriksa apakah cookie valid dan user sudah login"""
    if session is None:
        session = get_session()
    try:
        r = session.get(TASKS_URL, timeout=30)
        if "Logout" in r.text or "myt-balance" in r.text or "tasks/complete" in r.text or "Cooldown Active" in r.text:
            return True, r.text
        return False, r.text
    except Exception as e:
        return False, str(e)

# ================= PARSER ENGINE =================
def parse_task(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Info User & Balance
    username = "User"
    balance = "0.00 TC"
    bal_el = soup.find('a', class_='myt-balance')
    if bal_el:
        balance = bal_el.get_text(strip=True)
        
    side_scroll = soup.find('div', class_='myt-side-scroll')
    if side_scroll:
        m = re.search(r'([a-zA-Z0-9_]+)\s*LEVEL', side_scroll.get_text(' ', strip=True))
        if m:
            username = m.group(1)

    # 2. Cek apakah Cooldown Server sedang aktif
    # Script format: let timeLeft = <detik>;
    m_tl = re.search(r'let\s+timeLeft\s*=\s*(\d+);', html_content)
    if m_tl:
        cooldown_sec = int(m_tl.group(1))
        return {
            "status": "cooldown",
            "username": username,
            "balance": balance,
            "cooldown_sec": cooldown_sec
        }

    # Cek teks "Next task available in: mm:ss"
    m_cd_text = re.search(r'Next task available in:\s*(\d+):(\d+)', html_content, re.I)
    if m_cd_text:
        mins = int(m_cd_text.group(1))
        secs = int(m_cd_text.group(2))
        cooldown_sec = (mins * 60) + secs
        return {
            "status": "cooldown",
            "username": username,
            "balance": balance,
            "cooldown_sec": cooldown_sec
        }

    # 3. Check Form Task Aktif
    form = soup.find('form', action=re.compile(r'/tasks/complete/(\d+)'))
    if not form:
        text = soup.get_text(' ', strip=True)
        if "no micro jobs" in text.lower() or "no tasks available" in text.lower():
            return {"status": "no_task", "username": username, "balance": balance, "cooldown_sec": 45}
        return {"status": "no_form", "username": username, "balance": balance, "cooldown_sec": 45}

    action_url = form.get('action')
    m_id = re.search(r'/tasks/complete/(\d+)', action_url)
    task_id = m_id.group(1) if m_id else ""

    csrf_input = form.find('input', {'name': 'csrf_token_name'})
    csrf_token = csrf_input.get('value') if csrf_input else ""

    card = form.find_parent('div', class_='task-container-card') or soup.find('div', class_='task-container-card')
    
    title = "YouTube Channel"
    handle = "@channel"
    avatar_url = None
    reward = "5 Task Coins"
    
    if card:
        name_el = card.find(class_='profile-name-text')
        if name_el:
            title = html.unescape(name_el.get_text(strip=True))
            
        handle_btn = card.find(class_='btn-copy-handle')
        if handle_btn:
            handle = html.unescape(handle_btn.get_text(strip=True))
        else:
            m_h = re.search(r'(@[A-Za-z0-9_\-\.]+)', card.get_text(' ', strip=True))
            if m_h:
                handle = m_h.group(1)
                
        avatar_img = card.find('img', class_='profile-avatar-img')
        if avatar_img and avatar_img.get('src'):
            avatar_url = avatar_img.get('src')
            
        rew_val = card.find(class_='reward-pill-val')
        if rew_val:
            reward = rew_val.get_text(strip=True)

    return {
        "status": "available",
        "username": username,
        "balance": balance,
        "task_id": task_id,
        "title": title,
        "handle": handle,
        "avatar_url": avatar_url,
        "reward": reward,
        "csrf_token": csrf_token,
        "submit_url": action_url
    }

# ================= TASK EXECUTOR =================
def run_task_once(session):
    try:
        r = session.get(TASKS_URL, timeout=30)
        html_content = r.text
    except Exception as e:
        print(f"{MERAH}[ERROR] Gagal memuat halaman tasks: {e}{RESET}")
        return {"status": "error", "wait": 15}

    task_info = parse_task(html_content)
    status = task_info.get("status")
    username = task_info.get("username", "User")
    balance = task_info.get("balance", "0.00 TC")

    # 1. Kasus Server Cooldown
    if status == "cooldown":
        cd_sec = task_info.get("cooldown_sec", 60)
        mins = cd_sec // 60
        secs = cd_sec % 60
        print(f"{PUTIH}[INFO] Akun: {CYAN}{username}{PUTIH} | Saldo: {HIJAU}{balance}{RESET}")
        print(f"{KUNING}[COOLDOWN SERVER] Menunggu {mins:02d}:{secs:02d} sesuai timer resmi server makeyoutask...{RESET}")
        # Tambahkan 2 detik buffer agar halaman pasti sudah refresh di server
        return {"status": "cooldown", "wait": cd_sec + 2}

    # 2. Kasus Tidak Ada Task
    if status in ["no_task", "no_form"]:
        print(f"{PUTIH}[INFO] Akun: {CYAN}{username}{PUTIH} | Saldo: {HIJAU}{balance}{RESET}")
        print(f"{KUNING}[TASK] Belum ada task tersedia. Standby pengecekan berkala...{RESET}")
        return {"status": "no_task", "wait": 30}

    # 3. Kasus Task Tersedia
    task_id = task_info["task_id"]
    title = task_info["title"]
    handle = task_info["handle"]
    avatar_url = task_info["avatar_url"]
    reward = task_info["reward"]
    csrf_token = task_info["csrf_token"]
    submit_url = task_info["submit_url"]

    print(f"\n{HIJAU}[+] Ditemukan Task #{task_id}!{RESET}")
    print(f"    Target Channel : {CYAN}{title}{RESET} ({KUNING}{handle}{RESET})")
    print(f"    Reward         : {HIJAU}+{reward}{RESET}")
    print(f"    Saldo Akun     : {PUTIH}{balance}{RESET}")

    # Generate screenshot
    print(f"{PUTIH}[1/3] Membuat bukti screenshot YouTube (Subscribed active state)...{RESET}")
    try:
        b64_img = generate_yt_screenshot(title, handle, avatar_url=avatar_url)
        img_bytes = base64.b64decode(b64_img)
        print(f"{HIJAU}[+] Screenshot proof berhasil dibuat ({round(len(img_bytes)/1024, 1)} KB){RESET}")
    except Exception as e:
        print(f"{MERAH}[-] Gagal generate screenshot: {e}{RESET}")
        return {"status": "error", "wait": 10}

    # Delay simulasi pengerjaan wajar
    wait_time = 12
    print(f"{PUTIH}[2/3] Simulasi pengerjaan task ({wait_time} detik)...{RESET}")
    timer(wait_time, "  Mengerjakan...")

    # Upload proof menggunakan CurlMime multipart
    print(f"{PUTIH}[3/3] Mengirim bukti screenshot ke server...{RESET}")
    mp = curl_cffi.CurlMime()
    if csrf_token:
        mp.addpart(name="csrf_token_name", data=csrf_token)
    mp.addpart(name="file", content_type="image/png", filename="Screenshot_Proof.png", data=img_bytes)

    headers = {
        "Referer": TASKS_URL,
        "Origin": BASE_URL
    }

    try:
        res = session.post(submit_url, multipart=mp, headers=headers, timeout=45)
        mp.close()
        res_text = res.text
        
        # Cek hasil submit
        if "has been added" in res_text or "successfully" in res_text.lower() or "reward credited" in res_text.lower() or res.status_code == 200:
            new_task = parse_task(res_text)
            new_bal = new_task.get("balance", balance)
            print(f"{HIJAU}[SUCCESS] Bukti terkirim & Task #{task_id} selesai! Saldo Baru: {CYAN}{new_bal}{RESET}")
            
            # Jika halaman setelah submit menampilkan cooldown, gunakan waktu tersebut
            if new_task.get("status") == "cooldown":
                cd = new_task.get("cooldown_sec", 600)
                print(f"{KUNING}[COOLDOWN] Server mengharuskan jeda {cd} detik sebelum task berikutnya.{RESET}")
                return {"status": "cooldown", "wait": cd + 2}
            return {"status": "success", "wait": 10}
        else:
            print(f"{KUNING}[INFO] Status submit: HTTP {res.status_code}{RESET}")
            return {"status": "submitted", "wait": 15}
    except Exception as e:
        mp.close()
        print(f"{MERAH}[-] Error saat submit: {e}{RESET}")
        return {"status": "error", "wait": 15}

# ================= MENU HANDLERS =================
def start_bot():
    cfg = load_config()
    cookie_str = cfg.get("cookie", "")
    if not cookie_str:
        print(f"{MERAH}[!] Cookie belum diatur! Silakan pilih menu [1] Login Cookie terlebih dahulu.{RESET}")
        input(f"{PUTIH}Tekan Enter untuk kembali...{RESET}")
        return

    session = get_session()
    print(f"{CYAN}[*] Memeriksa status login ke makeyoutask.com...{RESET}")
    is_logged_in, page_content = check_login(session)

    if not is_logged_in:
        print(f"{MERAH}[!] Cookie tidak valid atau sudah kedaluwarsa! Silakan perbarui di menu [1].{RESET}")
        input(f"{PUTIH}Tekan Enter untuk kembali...{RESET}")
        return

    task_init = parse_task(page_content)
    print(f"{HIJAU}[✓] Berhasil terhubung!{RESET}")
    print(f"{PUTIH}    User    : {CYAN}{task_init.get('username')}{RESET}")
    print(f"{PUTIH}    Saldo   : {HIJAU}{task_init.get('balance')}{RESET}")
    print(f"{CYAN}==============================================")
    print(f"{HIJAU}      BOT YOUTUBE GENERATOR STANDALONE RUNNING")
    print(f"{PUTIH}      (Tekan Ctrl+C untuk berhenti)")
    print(f"{CYAN}=============================================={RESET}\n")

    try:
        while True:
            res = run_task_once(session)
            wait_sec = res.get("wait", 15)
            
            if res.get("status") == "cooldown":
                timer(wait_sec, "  Cooldown Server")
            else:
                timer(wait_sec, "  Standby loop")
            print()
    except KeyboardInterrupt:
        print(f"\n{KUNING}[*] Bot dihentikan oleh pengguna.{RESET}")
        input(f"{PUTIH}Tekan Enter untuk kembali ke menu...{RESET}")

def login_cookie_menu():
    cfg = load_config()
    clear_screen()
    print(f"{CYAN}==============================================")
    print(f"{PUTIH}         MENU [1] LOGIN DENGAN COOKIE")
    print(f"{CYAN}=============================================={RESET}")
    current_cookie = cfg.get("cookie", "")
    if current_cookie:
        print(f"{PUTIH}Cookie saat ini : {HIJAU}{current_cookie[:50]}...{RESET}")
    else:
        print(f"{PUTIH}Cookie saat ini : {MERAH}(Belum ada cookie tersimpan){RESET}")
    
    print(f"\n{PUTIH}Pilihan:{RESET}")
    print(" [1] Masukkan / Paste Cookie baru secara manual")
    print(" [2] Ambil otomatis dari browser Chrome aktif (Opsional)")
    print(" [0] Kembali ke menu utama")
    print(f"{CYAN}=============================================={RESET}")
    choice = input(f"{KUNING}Pilih > {RESET}").strip()

    if choice == '1':
        print(f"\n{PUTIH}Paste cookie string Anda di bawah ini:{RESET}")
        new_cookie = input(f"{KUNING}Cookie > {RESET}").strip()
        if new_cookie:
            cfg["cookie"] = new_cookie
            save_config(cfg)
            print(f"\n{HIJAU}[✓] Cookie berhasil disimpan!{RESET}")
            time.sleep(1.5)
    elif choice == '2':
        print(f"\n{CYAN}[*] Menghubungi Chrome (DevTools Port 9222)...{RESET}")
        try:
            import urllib.request
            req = urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=2)
            tabs = json.loads(req.read().decode())
            myt_tabs = [t for t in tabs if 'makeyoutask.com' in t.get('url', '')]
            if not myt_tabs:
                print(f"{MERAH}[-] Tab makeyoutask.com tidak ditemukan di Chrome.{RESET}")
                time.sleep(2)
                return

            import websocket
            ws = websocket.create_connection(myt_tabs[0]['webSocketDebuggerUrl'])
            ws.send(json.dumps({'id': 1, 'method': 'Network.getCookies', 'params': {'urls': ['https://makeyoutask.com', 'https://makeyoutask.com/tasks']}}))
            res = json.loads(ws.recv())
            cookies = res.get('result', {}).get('cookies', [])
            ws.close()

            if cookies:
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                cfg["cookie"] = cookie_str
                save_config(cfg)
                print(f"{HIJAU}[✓] Berhasil sinkronisasi {len(cookies)} cookies dari Chrome!{RESET}")
                time.sleep(2)
            else:
                print(f"{MERAH}[-] Tidak ada cookies ditemukan.{RESET}")
                time.sleep(2)
        except Exception as e:
            print(f"{MERAH}[-] Gagal sinkronisasi dari Chrome: {e}{RESET}")
            time.sleep(2)

def main():
    while True:
        clear_screen()
        print(f"{CYAN}==============================================")
        print(f"{PUTIH}      MAKEYOUTASK BOT (STANDALONE EDITION)   ")
        print(f"{HIJAU}      Auto Proof Generator & Task Submitter  ")
        print(f"{CYAN}=============================================={RESET}")
        print(" [1] Login Cookie")
        print(" [2] Start Bot")
        print(" [0] Exit")
        print(f"{CYAN}=============================================={RESET}")
        opt = input(f"{KUNING}Pilih > {RESET}").strip()

        if opt == '1':
            login_cookie_menu()
        elif opt == '2':
            clear_screen()
            start_bot()
        elif opt == '0':
            print(f"\n{PUTIH}Sampai jumpa!{RESET}")
            sys.exit(0)

if __name__ == "__main__":
    main()

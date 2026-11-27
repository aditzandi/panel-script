# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   FOOD EMPIRE TYCOON — ULTIMATE STANDALONE BOT v2.1         ║
║   Auto-login Telethon | Cloudflare Auto-Bypass | VIP        ║
╚══════════════════════════════════════════════════════════════╝

Login cukup via Telethon (nomor HP + OTP).
Cloudflare bypass otomatis via cloudscraper — tidak perlu cf_clearance manual.
"""

import asyncio
import sys
import os
import io
import json
import time
import random
import base64
import hashlib
import secrets
import urllib.parse
import threading
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ─── YouTube Proof Screenshot Generator (In-Memory Headless) ──
def generate_yt_screenshot(title: str, handle: str, avatar_url: str = None) -> str:
    """
    Menghasilkan bukti screenshot YouTube mobile secara dinamis di RAM
    lengkap dengan status aktif 'Disubscribe' (Subscribed).
    100% in-memory — tidak meninggalkan file cache di penyimpanan.
    """
    W, H = 720, 1280
    
    # YouTube dark theme colors
    BG_COLOR = (15, 15, 15)
    CARD_BG = (39, 39, 39)
    TEXT_WHITE = (241, 241, 241)
    TEXT_GRAY = (170, 170, 170)
    BANNER_COLOR = (30, 40, 55)
    AVATAR_BG = (100, 110, 130)
    
    img = Image.new('RGB', (W, H), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Load fonts (fallback ke default jika ttf tidak ada)
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
            font_title = ImageFont.load_default(size=34) if hasattr(ImageFont, 'load_default') and 'size' in ImageFont.load_default.__code__.co_varnames else ImageFont.load_default()
            font_handle = font_title
            font_sub = font_title
            font_nav = font_title
    except Exception:
        font_title = ImageFont.load_default()
        font_handle = font_title
        font_sub = font_title
        font_nav = font_title

    # 1. Top Bar (Search & header)
    draw.rectangle([0, 0, W, 80], fill=(15, 15, 15))
    draw.text((40, 25), "<-", fill=TEXT_WHITE, font=font_title)
    h_display = handle if handle.startswith('@') else f"@{handle}"
    draw.text((100, 25), h_display, fill=TEXT_WHITE, font=font_title)
    
    # 2. Channel Banner
    draw.rectangle([0, 80, W, 260], fill=BANNER_COLOR)
    
    # 3. Avatar Circle (fetch jika tersedia)
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
    
    # 4. Channel Title & Handle & Info
    draw.text((40, 350), title[:30], fill=TEXT_WHITE, font=font_title)
    draw.text((40, 395), f"{h_display} \u2022 14.8 rb subscriber \u2022 182 video", fill=TEXT_GRAY, font=font_handle)
    draw.text((40, 430), "Channel video & tutorial resmi ...selengkapnya", fill=TEXT_GRAY, font=font_handle)
    
    # 5. Tombol 'Disubscribe' aktif
    btn_x0, btn_y0, btn_x1, btn_y1 = 40, 480, 280, 540
    draw.rounded_rectangle([btn_x0, btn_y0, btn_x1, btn_y1], radius=30, fill=CARD_BG)
    draw.text((65, 495), "\U0001F514 Disubscribe", fill=TEXT_WHITE, font=font_sub)
    
    # Tombol Gabung
    draw.rounded_rectangle([300, 480, 460, 540], radius=30, fill=CARD_BG)
    draw.text((340, 495), "Gabung", fill=TEXT_WHITE, font=font_sub)
    
    # 6. Tab bar (Beranda, Video, Shorts, Playlist)
    draw.text((40, 570), "Beranda", fill=TEXT_WHITE, font=font_nav)
    draw.rectangle([40, 605, 140, 608], fill=TEXT_WHITE)
    draw.text((180, 570), "Video", fill=TEXT_GRAY, font=font_nav)
    draw.text((290, 570), "Shorts", fill=TEXT_GRAY, font=font_nav)
    draw.text((410, 570), "Playlist", fill=TEXT_GRAY, font=font_nav)
    draw.line([0, 610, W, 610], fill=(45, 45, 45), width=1)
    
    # 7. Video preview
    draw.rectangle([40, 640, W - 40, 940], fill=(30, 30, 30))
    draw.ellipse([40, 960, 90, 1010], fill=AVATAR_BG)
    draw.text((110, 960), f"Video Terbaru - {title[:25]}", fill=TEXT_WHITE, font=font_handle)
    draw.text((110, 995), f"{title[:20]} \u2022 2.5 rb x ditonton \u2022 2 hari lalu", fill=TEXT_GRAY, font=font_handle)
    
    # Encode langsung di RAM ke base64
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    b64_str = base64.b64encode(buf.read()).decode('utf-8')
    return b64_str

import cloudscraper
import requests
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich.rule import Rule
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

# ─── Windows UTF-8 ───────────────────────────────────────────
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─── Paths & Constants ───────────────────────────────────────
BASE_DIR    = Path(__file__).parent
SESSION_DIR = BASE_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

PHONE_FILE   = SESSION_DIR / "last_phone.txt"

BOT_USERNAME   = "FoodEmpireTON_bot"
GAME_URL       = "https://makeyoutask.com/tycoon/"
GAME_API       = "https://makeyoutask.com/tycoon/api"
ADSGRAM_API    = "https://api.adsgram.ai"
ADSGRAM_BLOCK  = "58655"

# Telegram API credentials (Telegram Desktop public)
TG_API_ID   = 2040
TG_API_HASH = "b18441a1ff607e10a989891a5462e627"

console = Console()

# ─── Global state ────────────────────────────────────────────
bot_running   = False
bot_logs      = []          # list of (time_str, tag, msg, color)
game_state    = {}
player_info   = {}
stats_lock    = threading.Lock()

MAX_LOGS = 80

def add_log(tag: str, msg: str, color: str = "white"):
    t = datetime.now().strftime("%H:%M:%S")
    with stats_lock:
        bot_logs.append((t, tag, msg, color))
        if len(bot_logs) > MAX_LOGS:
            bot_logs.pop(0)

# ─── CF Clearance helpers ─────────────────────────────────────
def load_cf() -> str:
    if CF_FILE.exists():
        return CF_FILE.read_text(encoding="utf-8").strip()
    return ""

def save_cf(val: str):
    CF_FILE.write_text(val.strip(), encoding="utf-8")

def load_config_init_data() -> str:
    cfg = BASE_DIR / "config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            return data.get("init_data", "").strip()
        except Exception:
            pass
    return ""

# ─── CF Clearance helpers ─────────────────────────────────────
def load_cf() -> str:
    if CF_FILE.exists():
        return CF_FILE.read_text(encoding="utf-8").strip()
    return ""

def save_cf(val: str):
    CF_FILE.write_text(val.strip(), encoding="utf-8")

def load_config_init_data() -> str:
    cfg = BASE_DIR / "config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            return data.get("init_data", "").strip()
        except Exception:
            pass
    return ""

# ═══════════════════════════════════════════════════════════════
#  TELETHON LOGIN
# ═══════════════════════════════════════════════════════════════

async def telethon_login(phone: str) -> TelegramClient | None:
    """Login via Telethon dengan nomor HP, return client yang sudah ter-auth."""
    session_file = SESSION_DIR / f"{phone.replace('+', '')}"
    client = TelegramClient(str(session_file), TG_API_ID, TG_API_HASH)

    console.print(Panel(
        f"[cyan]Menghubungkan ke Telegram...[/cyan]\n"
        f"Nomor: [bold yellow]{phone}[/bold yellow]",
        title="[bold blue]TELETHON LOGIN[/bold blue]",
        border_style="blue"
    ))

    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        console.print(f"[green]Sudah login sebagai: {me.first_name} (ID: {me.id})[/green]")
        return client

    # Kirim kode OTP
    try:
        await client.send_code_request(phone)
        console.print(f"[yellow]Kode OTP dikirim ke {phone}[/yellow]")
    except Exception as e:
        console.print(f"[red]Error kirim OTP: {e}[/red]")
        await client.disconnect()
        return None

    # Input kode OTP
    code = Prompt.ask("[bold cyan]Masukkan kode OTP dari Telegram[/bold cyan]")
    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        console.print("[yellow]Akun ini menggunakan 2FA (Two-Step Verification)[/yellow]")
        password = Prompt.ask("[bold cyan]Masukkan password 2FA[/bold cyan]", password=True)
        try:
            await client.sign_in(password=password)
        except Exception as e:
            console.print(f"[red]Password 2FA salah: {e}[/red]")
            await client.disconnect()
            return None
    except PhoneCodeInvalidError:
        console.print("[red]Kode OTP salah![/red]")
        await client.disconnect()
        return None
    except Exception as e:
        console.print(f"[red]Login error: {e}[/red]")
        await client.disconnect()
        return None

    me = await client.get_me()
    # Simpan nomor terakhir
    PHONE_FILE.write_text(phone, encoding="utf-8")
    console.print(f"[green bold]Login berhasil! Selamat datang, {me.first_name}![/green bold]")
    return client


async def get_init_data(client: TelegramClient) -> str | None:
    """
    Ambil initData dari Telegram via RequestWebView.
    Otomatis — tidak perlu copy manual dari Chrome!
    """
    try:
        bot_entity = await client.get_entity(BOT_USERNAME)
        result = await client(RequestWebViewRequest(
            peer=bot_entity,
            bot=bot_entity,
            platform="android",
            url=GAME_URL,
            from_bot_menu=True,
        ))
        url = result.url
        # Fragment bisa berformat: https://.../#tgWebAppData=...&...
        # atau encoded: https://.../%23tgWebAppData%3D...
        if "#" in url:
            fragment = url.split("#", 1)[1]
        else:
            # Coba decode dulu
            url_dec = urllib.parse.unquote(url)
            fragment = url_dec.split("#", 1)[1] if "#" in url_dec else ""

        params = dict(urllib.parse.parse_qsl(fragment, keep_blank_values=True))
        init_data_raw = params.get("tgWebAppData", "")

        # Double-decode jika perlu
        if not init_data_raw:
            fragment2 = urllib.parse.unquote(fragment)
            params2 = dict(urllib.parse.parse_qsl(fragment2, keep_blank_values=True))
            init_data_raw = params2.get("tgWebAppData", "")

        if init_data_raw:
            return init_data_raw
        else:
            add_log("AUTH-ERR", f"tgWebAppData kosong. URL: {url[:120]}", "red")
            return None
    except Exception as e:
        add_log("AUTH-ERR", f"Gagal ambil initData: {e}", "red")
        return None


# ═══════════════════════════════════════════════════════════════
#  GAME BOT ENGINE
# ═══════════════════════════════════════════════════════════════

class FoodEmpireBot:
    def __init__(self, init_data: str):
        self.init_data     = init_data
        self.base_url      = GAME_API
        self._parse_init_data()

        # Session game — cloudscraper otomatis bypass Cloudflare (tidak perlu cf_clearance manual)
        self.session = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "android",
                "mobile": True,
            }
        )
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "origin": "https://makeyoutask.com",
            "referer": "https://makeyoutask.com/tycoon",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        })

        # Session Adsgram
        self.ads_session = requests.Session()
        self.ads_session.headers.update({
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Origin": "https://makeyoutask.com",
            "Referer": "https://makeyoutask.com/",
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1"
            ),
            "X-Color-Scheme": "dark",
            "X-Is-Fullscreen": "false",
            "sec-ch-ua": '"Chromium";v="158", "Not.A/Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
        })

        # Tracking cooldowns
        self.last_daily      = 0
        self.last_pass       = 0
        self.last_chef       = 0
        self.last_pet        = 0
        self.last_sp         = 0
        self.last_offline    = 0
        self.last_upgrade    = 0
        self.last_fleet      = 0
        self.last_quest      = 0
        self.last_factory    = 0
        self.last_order      = 0
        self.last_pb         = 0
        self.last_decor      = 0
        self.last_boost_ad   = 0
        self.last_path       = 0
        self.last_task       = 0

        # Session stats
        self.vip_served_total  = 0
        self.ton_earned_total  = 0
        self.gems_earned_total = 0
        self.cash_earned_total = 0
        self.total_cycles      = 0

    def update_init_data(self, init_data: str):
        self.init_data = init_data
        self._parse_init_data()
        add_log("REFRESH", "initData diperbarui!", "green")

    def _parse_init_data(self):
        try:
            params = dict(urllib.parse.parse_qsl(self.init_data))
            self.signature     = params.get("signature", "")
            self.auth_date     = params.get("auth_date", str(int(time.time())))
            self.chat_instance = params.get("chat_instance", "")
            self.chat_type     = params.get("chat_type", "sender")
            user_raw           = params.get("user", "{}")
            # user_raw mungkin sudah decoded atau masih %7B...
            try:
                user_obj = json.loads(user_raw)
            except Exception:
                user_obj = json.loads(urllib.parse.unquote(user_raw))
            self.tg_id         = str(user_obj.get("id", ""))
            self.tg_name       = user_obj.get("first_name", "Unknown")
            # data_check_string: semua param kecuali hash & signature, sorted, join \n
            excluded    = {"hash", "signature"}
            check_lines = [f"{k}={v}" for k, v in sorted(params.items()) if k not in excluded]
            self.data_check_string = "\n".join(check_lines)
        except Exception as e:
            add_log("PARSE-ERR", str(e), "red")
            self.signature = self.auth_date = self.chat_instance = ""
            self.chat_type = "sender"; self.tg_id = ""; self.tg_name = "Bot"
            self.data_check_string = ""

    # ── API Call ──────────────────────────────────────────────
    def api(self, action: str, payload: dict = None, taps: int = 0) -> dict:
        url  = f"{self.base_url}/{action}"
        body = payload.copy() if payload else {}
        body["init"] = self.init_data
        body["taps"] = taps
        try:
            r = self.session.post(url, json=body, timeout=20)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 403:
                add_log("CF-ERR", "HTTP 403 — cloudscraper sedang retry...", "yellow")
                return {"ok": False, "error": "Cloudflare 403"}
            elif r.status_code == 401:
                add_log("AUTH", "Session expired! Refresh initData via menu 3", "yellow")
                return {"ok": False, "error": "Unauthorized"}
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:100]}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Sync & Tap ────────────────────────────────────────────
    def do_sync(self, taps: int = 0) -> dict | None:
        res = self.api("sync", {}, taps=taps)
        if res.get("ok"):
            st = res.get("state", {})
            with stats_lock:
                game_state.update(st)
            return st
        return None

    # ── Profile ───────────────────────────────────────────────
    def do_profile(self) -> dict | None:
        res = self.api("profile", {"id": 0})
        if res.get("ok"):
            p = res.get("p", {})
            with stats_lock:
                player_info.update(p)
            return p
        return None

    # ── Daily / Offline / Pass ────────────────────────────────
    def do_daily_claims(self):
        now = time.time()

        # Daily reward
        if now - self.last_daily > 3600:
            r = self.api("daily")
            if r.get("ok"):
                rew = r.get("reward", {})
                add_log("DAILY", f"+{rew.get('cash',0):,.0f} Cash | +{rew.get('gems',0)} Gems", "green")
            self.last_daily = now

        # Offline income
        if now - self.last_offline > 300:
            r = self.api("collect_offline")
            if r.get("ok") and r.get("reward"):
                rew = r.get("reward", {})
                if rew.get("cash", 0) > 0:
                    add_log("OFFLINE", f"+{rew.get('cash',0):,.0f} Cash offline", "cyan")
            self.last_offline = now

        # Season pass
        if now - self.last_pass > 3600:
            r = self.api("pass_claim")
            if r.get("ok"):
                add_log("PASS", "Season pass diklaim!", "green")
            self.last_pass = now

        # Chef box (cooldown 20 jam)
        if now - self.last_chef > 3600 * 20:
            r = self.api("chef_box", {"kind": "free"})
            if r.get("ok"):
                add_log("CHEF", f"Chef box gratis: {r.get('reward','')}", "green")
            self.last_chef = now

        # Pet feed (cooldown 8 jam)
        if now - self.last_pet > 3600 * 8:
            r = self.api("pet_feed")
            if r.get("ok"):
                add_log("PET", "Kucing dikasih makan!", "green")
            self.last_pet = now

        # Speed pass / sp_claim
        if now - self.last_sp > 600:
            r = self.api("sp_claim")
            if r.get("ok") and r.get("reward"):
                rew = r.get("reward", {})
                if rew.get("cash", 0) > 0:
                    add_log("SP", f"+{rew.get('cash',0):,.0f} Cash bonus", "cyan")
            self.last_sp = now

    # ── Auto Upgrade (Stasiun + Staf + Dapur + Tier) ──────────
    def do_upgrade(self, state: dict):
        now = time.time()
        if now - self.last_upgrade < 10:
            return
        self.last_upgrade = now

        stations = state.get("stations", {})

        # 1. Upgrade semua stasiun
        for st_name in list(stations.keys()):
            r = self.api("station", {"key": st_name, "n": 1})
            if r.get("ok"):
                lvl = r.get("state", {}).get("stations", {}).get(st_name, "?")
                add_log("UPGRADE", f"Stasiun '{st_name}' Lv.{lvl}", "yellow")

        # 2. Upgrade semua staf (chef, waiter, manager)
        staff = state.get("staff", {})
        for s_name in list(staff.keys()) or ["chef", "waiter", "manager"]:
            r = self.api("staff", {"key": s_name, "n": 1})
            if r.get("ok"):
                lvl = r.get("state", {}).get("staff", {}).get(s_name, "?")
                add_log("STAFF", f"Staf '{s_name}' Lv.{lvl}", "yellow")

        # 3. Upgrade peralatan Dapur (eq_up)
        for eq_name in ["oven", "fridge", "espresso", "grill"]:
            r = self.api("eq_up", {"key": eq_name})
            if r.get("ok"):
                lvl = r.get("state", {}).get("eq", {}).get(eq_name, "?")
                add_log("DAPUR", f"Dapur '{eq_name}' Lv.{lvl}", "yellow")

        # 4. Coba naik tier
        r = self.api("tier")
        if r.get("ok"):
            new_tier = r.get("new_tier", "?")
            add_log("TIER-UP", f"RESTORAN NAIK ke TIER {new_tier}!!!", "bold green")
            with stats_lock:
                player_info["tier"] = new_tier

    # ── Order Board ───────────────────────────────────────────
    def do_order_board(self, state: dict):
        now = time.time()
        if now - self.last_order < 20:
            return
        self.last_order = now

        ob    = state.get("mt", {}).get("ob", {})
        slots = ob.get("slots", [])
        if not slots:
            # Coba dari state langsung
            slots = state.get("ob", {}).get("slots", [])

        for idx, slot in enumerate(slots):
            if not isinstance(slot, dict):
                continue
            sid = slot.get("id", 0)
            r   = self.api("ob_deliver", {"slot": idx, "id": sid, "fill": 0})
            if r.get("ok"):
                rew  = r.get("reward", {})
                cash = rew.get("cash", 0)
                gems = rew.get("gems", 0)
                self.cash_earned_total += cash
                self.gems_earned_total += gems
                add_log("ORDER", f"Pesanan slot #{idx} (id={sid}): +{cash:,.0f} Cash +{gems} Gems", "cyan")

    # ── Party Box / Catering (pb_start) ───────────────────────
    def do_party_box(self, state: dict):
        now = time.time()
        if now - self.last_pb < 25:
            return
        self.last_pb = now

        pb = state.get("mt", {}).get("ob", {}).get("pb", {})
        if not isinstance(pb, dict):
            return

        # Coba start paket yang tersedia di pb["av"]
        av = pb.get("av", []) or ["bmeal"]
        for k in av:
            r = self.api("pb_start", {"k": k, "fill": 0})
            if r.get("ok"):
                add_log("PARTY", f"Party Box '{k}' dimulai!", "magenta")
                break

    # ── Dekorasi (decor_buy) ──────────────────────────────────
    def do_decor(self, state: dict):
        now = time.time()
        if now - self.last_decor < 30:
            return
        self.last_decor = now

        owned = set(state.get("decor", []) or [])
        for k in ["plants", "neon", "art", "aquarium", "fountain", "vip_lounge"]:
            if k in owned:
                continue
            r = self.api("decor_buy", {"key": k})
            if r.get("ok"):
                add_log("DECOR", f"Dekorasi '{k}' dibeli!", "green")
                owned.add(k)

    # ── Fleet (Scooter / Deliveries) ─────────────────────────
    def do_fleet(self, state: dict):
        now = time.time()
        if now - self.last_fleet < 30:
            return
        self.last_fleet = now

        fl = state.get("lv", {}).get("fl", {})
        if not fl:
            fl = state.get("fl", {})

        for vehicle, data in fl.items() if isinstance(fl, dict) else []:
            if not isinstance(data, dict):
                continue
            end_time = data.get("e", 0)
            if end_time > 0 and now >= end_time:
                r = self.api("fleet_claim", {"key": vehicle, "resend": 1})
                if r.get("ok"):
                    rew = r.get("reward", {})
                    add_log("FLEET", f"{vehicle} kembali! +{rew.get('cash',0):,.0f} Cash", "cyan")
            elif end_time == 0 and data.get("ok", 0) == 1:
                r = self.api("fleet_send", {"key": vehicle})
                if r.get("ok"):
                    add_log("FLEET", f"{vehicle} dikirim!", "blue")

        # Coba auto upgrade armada untuk naikin reward gems
        for vehicle in ["scooter", "van"]:
            r_up = self.api("fleet_up", {"key": vehicle})
            if r_up.get("ok"):
                add_log("FLEET", f"Armada '{vehicle}' BERHASIL DI-UPGRADE!", "bold yellow")

    # ── Gem Factory (TON Printer) — MAXIMIZED ─────────────────
    def do_factory(self, state: dict):
        now = time.time()
        if now - self.last_factory < 12:
            return
        self.last_factory = now

        # 1. Panen TON tips
        r = self.api("tj_collect")
        if r.get("ok"):
            rew  = r.get("reward", {})
            tips = rew.get("tips", 0)
            if tips > 0:
                self.ton_earned_total += tips
                add_log("PABRIK", f"Panen TON: +{tips} Golden Tips (TON)!", "bold yellow")

        # 2. Coba auto-upgrade level pabrik TON jika suku cadang cukup
        r_up = self.api("tj_up")
        if r_up.get("ok"):
            add_log("PABRIK", "PABRIK TON BERHASIL DI-UPGRADE LEVEL BARU!", "bold green")

        # 3. Isi SEMUA gems yang ada ke pabrik tanpa batas cicil
        gems = state.get("gems", 0)
        if gems >= 5:
            r = self.api("tj_fill", {"n": gems})
            if r.get("ok"):
                filled = r.get("filled", 0)
                if filled > 0:
                    add_log("PABRIK", f"Isi pabrik: {filled} Gems -> Dicetak jadi TON!", "yellow")

    # ── Daily Quests ──────────────────────────────────────────
    def do_quests(self, state: dict):
        now = time.time()
        if now - self.last_quest < 60:
            return
        self.last_quest = now

        # 1. Quests reguler
        for q_key in ["serv", "tap", "up", "vip", "fl", "ob", "tj", "task", "ad"]:
            r = self.api("quest", {"key": q_key})
            if r.get("ok"):
                rew = r.get("reward", {})
                gems = rew.get("gems", 0) if isinstance(rew, dict) else 0
                self.gems_earned_total += gems
                add_log("QUEST", f"Misi '{q_key}' selesai! +{gems} Gems", "green")

    # ── Path Quest Tracker (Banjir Gems untuk TON) ─────────────
    def do_path_quests(self, state: dict):
        now = time.time()
        if now - self.last_path < 45:
            return
        self.last_path = now

        # Klaim semua tugas harian di menu Path (Day 1 - 7)
        for day in [1, 2, 3, 4, 5, 6, 7]:
            for i in [0, 1, 2]:
                r = self.api("path_claim", {"day": day, "i": i})
                if r.get("ok"):
                    rew = r.get("reward", {})
                    g = rew.get("gems", 0) if isinstance(rew, dict) else 0
                    self.gems_earned_total += g
                    add_log("PATH", f"Misi Path Day {day} #{i} selesai! +{g} Gems", "bold green")

            # Klaim kotak hadiah utama harian
            r_box = self.api("path_claim", {"day": day, "i": "day"})
            if r_box.get("ok"):
                add_log("PATH", f"Hadiah Kotak Path Day {day} diklaim!", "bold yellow")

    # ── Official Sponsor Tasks (TG Task) ──────────────────────
    # ── Sponsor & Partner Tasks (Adsgram task_out) ───────────
    def do_sponsor_tasks(self, state: dict):
        now = time.time()
        # Cooldown umum antar tugas
        if now - self.last_task < 35:
            return

        # Cek task gap / cooldown dari server
        task_gap = state.get("task_gap_left", 0)
        if task_gap > 0:
            return

        tasks_left = state.get("tasks_left", 0)
        if tasks_left <= 0:
            return

        self.last_task = now

        # 1. Cek tugas official Telegram channel (jika ada)
        tgtask = state.get("tgtask", {})
        if isinstance(tgtask, dict) and tgtask.get("ch"):
            ch_id = tgtask["ch"].get("id", 1)
            r = self.api("task", {"id": ch_id})
            if r.get("ok"):
                rew = r.get("reward", {})
                tips = rew.get("tips", 0) if isinstance(rew, dict) else 0
                gems = rew.get("gems", 0) if isinstance(rew, dict) else 0
                self.ton_earned_total += tips
                self.gems_earned_total += gems
                add_log("TASK", f"Tugas Channel #{ch_id} diklaim: +{tips} TON +{gems} Gems!", "bold yellow")
                return

        # 2. Partner Task Adsgram (58654) via task_out
        add_log("TASK-OUT", f"Mengerjakan Partner Task Adsgram... (Sisa: {tasks_left})", "bold cyan")

        # Ambil banner tugas partner (blockId: 58654)
        banner = self._get_adsgram_banner(block_id="58654")
        if not banner:
            banner = self._get_adsgram_banner(block_id=ADSGRAM_BLOCK)

        tracking = self._get_tracking_urls(banner) if banner else {}
        banner_obj = banner.get("banners", [{}])[0].get("banner", {}) if banner else {}
        task_link = banner_obj.get("link", "")

        # 1. Trigger tracking render
        if "render" in tracking:
            self._fire(tracking["render"])
        time.sleep(0.8)

        # 2. Trigger tracking show
        if "show" in tracking:
            self._fire(tracking["show"])
        time.sleep(0.8)

        # 3. Trigger tracking click
        if "click" in tracking:
            self._fire(tracking["click"])

        # Simulasi waktu user berada di luar app (out: 6-8 detik)
        out_time = random.randint(6200, 8500)
        add_log("TASK-STAY", f"Menunggu durasi tugas ({out_time/1000:.1f}s)...", "dim cyan")
        time.sleep(out_time / 1000.0)

        # 4. Trigger reward tracking
        if "reward" in tracking:
            self._fire(tracking["reward"])
        time.sleep(1.5)

        # 5. Kirim bukti task_out ke game server
        payload = {
            "out": out_time,
            "link": task_link,
            "lvia": "-",
            "cv": 192,
            "pf": "android"
        }
        r = self.api("task_out", payload)
        if r.get("ok"):
            st = r.get("state", {})
            with stats_lock:
                game_state.update(st)
            new_gems = st.get("gems", 0)
            new_tips = st.get("tips", 0)
            t_today = st.get("tasks_today", 0)
            add_log("TASK-WIN", f"Partner Task Sukses! Hari ini: {t_today} | Tips: {new_tips} | Gems: {new_gems}", "bold green")
        elif r.get("tout_gap"):
            gap = r.get("tout_gap")
            add_log("TASK-GAP", f"Cooldown task dari server: tunggu {gap}s", "yellow")
        elif r.get("tout_dup"):
            add_log("TASK-DUP", "Tugas ini sudah pernah diselesaikan", "yellow")
        elif r.get("tout_limit"):
            add_log("TASK-LIMIT", "Batas harian tugas Adsgram telah tercapai!", "dim")
        else:
            err = r.get("error", "Gagal task_out")
            add_log("TASK-ERR", f"Error: {err}", "red")

    # ── Adsgram /adv ──────────────────────────────────────────
    def _get_adsgram_banner(self, block_id: str = ADSGRAM_BLOCK) -> dict | None:
        # Build data_check_string as base64url (sama persis seperti SDK)
        dcs_b64 = base64.b64encode(
            self.data_check_string.encode()
        ).decode().replace("+", "-").replace("/", "_").rstrip("=")

        # raw = SHA256(data_check_string)
        raw_hash = hashlib.sha256(self.data_check_string.encode()).hexdigest()

        request_id = str(int.from_bytes(secrets.token_bytes(12), "big"))

        params = {
            "envType":           "telegram",
            "blockId":           block_id,
            "platform":          "Win32",
            "language":          "id",
            "chat_type":         self.chat_type or "sender",
            "chat_instance":     self.chat_instance,
            "top_domain":        "makeyoutask.com",
            "signature":         self.signature,
            "data_check_string": dcs_b64,
            "sdk_version":       "2.2.5",
            "tg_id":             self.tg_id,
            "tg_platform":       "android",
            "tma_version":       "8.0",
            "request_id":        request_id,
            "raw":               raw_hash,
        }
        try:
            r = self.ads_session.get(f"{ADSGRAM_API}/adv", params=params, timeout=15)
            if r.status_code == 200:
                d = r.json()
                if "error" in d:
                    add_log("ADV-ERR", f"[{block_id}] " + d["error"], "red")
                    return None
                return d
            add_log("ADV-ERR", f"[{block_id}] HTTP {r.status_code}: {r.text[:80]}", "red")
        except Exception as e:
            add_log("ADV-ERR", f"[{block_id}] " + str(e), "red")
        return None

    def _get_tracking_urls(self, banner_data: dict) -> dict:
        """Extract tracking URLs dari banners[0].banner.trackings"""
        tm = {}
        try:
            b_inner = banner_data.get("banners", [{}])[0].get("banner", {})
            for item in b_inner.get("trackings", []):
                name = item.get("name", "")
                val  = item.get("value", "")
                if name and val:
                    tm[name] = val
        except Exception:
            pass
        return tm

    def _fire(self, url: str):
        try:
            self.ads_session.get(url, timeout=10)
        except Exception:
            pass

    def _watch_and_reward_ad(self, block_id: str, ad_title: str) -> bool:
        """Helper memutar iklan Adsgram headless (render -> show -> watch -> reward)."""
        banner = self._get_adsgram_banner(block_id=block_id)
        if banner is None:
            add_log(f"{ad_title}-SKIP", f"Gagal ambil banner Adsgram ({block_id})", "yellow")
            return False

        tracking = self._get_tracking_urls(banner)
        if not tracking:
            add_log(f"{ad_title}-SKIP", f"Tracking kosong ({block_id})", "yellow")
            return False

        campaign = banner.get("banners", [{}])[0].get("campaignId", "?")
        add_log("ADV-OK", f"[{ad_title}] Banner #{campaign} | keys: {list(tracking.keys())}", "blue")

        # Fire sequence: render -> show -> [tunggu] -> reward
        if "render" in tracking:
            self._fire(tracking["render"])
        time.sleep(0.5 + random.uniform(0, 0.4))

        if "show" in tracking:
            self._fire(tracking["show"])

        # Simulasi nonton iklan 10-15 detik
        watch = 10 + random.uniform(0, 4)
        add_log("AD-WATCH", f"[{ad_title}] Simulasi tonton iklan {watch:.1f}s...", "dim cyan")
        time.sleep(watch)

        if "reward" in tracking:
            self._fire(tracking["reward"])

        time.sleep(2.0 + random.uniform(0, 1.5))
        return True

    # ── Boost Ad (RewardBlock) ────────────────────────────────
    def do_boost_ad(self, state: dict):
        now = time.time()
        if now - self.last_boost_ad < 35:
            return

        boost_ads_left = state.get("boost_ads_left", 0)

        # Jika kuota iklan masih ada
        if boost_ads_left <= 0:
            return

        self.last_boost_ad = now
        add_log("BOOST-AD", f"Tonton Iklan Boost! Sisa hari ini: {boost_ads_left}", "bold magenta")

        # Menggunakan ADSGRAM_BLOCK (58655) dengan fallback 58654
        if not self._watch_and_reward_ad(block_id=ADSGRAM_BLOCK, ad_title="BOOST"):
            return

        for attempt in range(1, 8):
            r = self.api("boost_ad", {})
            ok = r.get("ok", False)
            err = r.get("error", "")
            if ok:
                st = r.get("state", {})
                with stats_lock:
                    game_state.update(st)
                add_log("BOOST-WIN", f"Boost Income Aktif (x2 Cash)! Sisa iklan: {st.get('boost_ads_left', 0)}", "bold green")
                return
            if "not confirmed" in err.lower() or "ad" in err.lower():
                add_log("BOOST-WAIT", f"Percobaan {attempt}/7 — tunggu konfirmasi...", "yellow")
                time.sleep(3)
            else:
                add_log("BOOST-ERR", f"Error: {err}", "red")
                return

        add_log("BOOST-FAIL", "Gagal klaim iklan boost", "red")

    # ── VIP Auto-Serve (HEADLESS) ─────────────────────────────
    def do_vip(self, state: dict):
        # Cek field vip di state
        vip_left = state.get("vip_left", 0)
        vip_next = state.get("vip_next_at", 0)
        now      = time.time()

        # Fallback key lain
        if vip_left == 0:
            vip_left = state.get("vip", {}).get("left", 0) if isinstance(state.get("vip"), dict) else 0

        if vip_left <= 0:
            return
        if vip_next > 0 and now < vip_next:
            rem = int(vip_next - now)
            if rem < 60:
                add_log("VIP", f"Tamu VIP tiba dalam {rem}s", "dim")
            return

        add_log("VIP", f"Tamu VIP! Sisa hari ini: {vip_left} | Ambil banner iklan...", "bold cyan")

        if not self._watch_and_reward_ad(block_id=ADSGRAM_BLOCK, ad_title="VIP"):
            return

        # Klaim VIP
        for attempt in range(1, 8):
            r   = self.api("vip", {})
            ok  = r.get("ok", False)
            err = r.get("error", "")
            if ok:
                rew  = r.get("reward", {})
                tips = rew.get("tips", 0) if isinstance(rew, dict) else 0
                gems = rew.get("gems", 0) if isinstance(rew, dict) else 0
                self.vip_served_total  += 1
                self.ton_earned_total  += tips
                self.gems_earned_total += gems
                add_log(
                    "VIP-WIN",
                    f"VIP #{self.vip_served_total} BERHASIL! "
                    f"+{tips} TON Tips | +{gems} Gems",
                    "bold green"
                )
                return
            if "not confirmed" in err.lower() or "ad" in err.lower():
                add_log("VIP-WAIT", f"Percobaan {attempt}/7 — tunggu konfirmasi...", "yellow")
                time.sleep(3)
            else:
                add_log("VIP-ERR", f"Error: {err}", "red")
                return

        add_log("VIP-FAIL", "VIP gagal (server tidak konfirmasi iklan)", "red")

    # ── Auto YouTube Proof (Headless OCR Bypass) ──────────────
    def do_youtube_task(self, state: dict):
        yt = state.get("yt", {})
        if not yt or not isinstance(yt, dict):
            return
        
        now = state.get("now", int(time.time()))
        next_time = yt.get("next", 0)
        retry_time = yt.get("retry", 0)
        day_n = yt.get("day_n", 0)
        day_lim = yt.get("day_lim", 15)

        if day_n >= day_lim:
            return

        if now < next_time or now < retry_time:
            return

        ch = yt.get("ch")
        if not ch or not isinstance(ch, dict):
            return

        ch_id = ch.get("id")
        title = ch.get("title", "")
        handle = ch.get("handle", "")
        if not ch_id or not handle:
            return

        add_log("YT-PROOF", f"Garap Channel #{ch_id} ({handle})...", "bold cyan")
        try:
            b64_img = generate_yt_screenshot(title, handle)
            r = self.api("yt_proof", {"ch": ch_id, "img": b64_img})
            if r.get("ok"):
                rew = r.get("reward", {})
                gems = rew.get("gems", 0)
                tips = rew.get("tips", 50)
                self.ton_earned_total += tips
                self.gems_earned_total += gems
                add_log("YT-WIN", f"Klaim YouTube Sukses! +{tips} Golden Tips | +{gems} Gems", "bold green")
                # Update state
                if "state" in r:
                    with stats_lock:
                        game_state.update(r["state"])
            else:
                err = r.get("error", "Verifikasi gagal")
                add_log("YT-FAIL", f"Gagal: {err}", "yellow")
        except Exception as e:
            add_log("YT-ERR", f"Error yt_proof: {e}", "red")

    # ── Main Loop ─────────────────────────────────────────────
    def run(self):
        global bot_running
        add_log("BOT", "Bot dimulai!", "bold green")

        # Profil awal
        p = self.do_profile()
        if not p:
            cfg_init = load_config_init_data()
            if cfg_init and cfg_init != self.init_data:
                add_log("FALLBACK", "initData ditolak server, pakai config.json...", "yellow")
                self.update_init_data(cfg_init)
                p = self.do_profile()

        if p:
            add_log(
                "LOGIN",
                f"{p.get('name','?')} | Tier {p.get('tier','?')} | "
                f"Rank #{p.get('rank','?')} | "
                f"Earned: {p.get('total_earned',0):,.0f} Cash",
                "bold blue"
            )
        else:
            add_log("LOGIN-ERR", "Gagal profil! Cek initData di config.json", "bold red")

        # Klaim awal
        self.do_daily_claims()

        cycle = 0
        while bot_running:
            cycle += 1
            self.total_cycles = cycle
            try:
                taps  = random.randint(50, 100)
                state = self.do_sync(taps=taps)

                if state:
                    cash = state.get("cash", 0)
                    gems = state.get("gems", 0)
                    tips = state.get("tips", 0)
                    rate = state.get("rate", 0)
                    add_log(
                        "SYNC",
                        f"Cash: {cash:>13,.0f} | {rate}/s | "
                        f"Gems: {gems} | TON: {tips}",
                        "white"
                    )

                    # VIP (prioritas!)
                    self.do_vip(state)

                    # Tonton Iklan Boost (x2 Cash multiplier)
                    self.do_boost_ad(state)

                    # Otomatis Tugas YouTube (AI CV Bypass)
                    self.do_youtube_task(state)

                    # Pabrik TON prioritas tinggi (setiap cycle!)
                    self.do_factory(state)

                    # Daily claims
                    self.do_daily_claims()

                    # Path Quests & Sponsor Tasks
                    self.do_path_quests(state)
                    self.do_sponsor_tasks(state)

                    # Order Board & Party Box setiap 3 cycle
                    if cycle % 3 == 0:
                        self.do_order_board(state)
                        self.do_party_box(state)

                    # Upgrade stasiun & staf
                    self.do_upgrade(state)

                    # Fleet & Decor setiap 5 cycle
                    if cycle % 5 == 0:
                        self.do_fleet(state)
                        self.do_decor(state)

                    # Quest setiap 3 cycle
                    if cycle % 3 == 0:
                        self.do_quests(state)

                    # Profil update setiap 20 cycle
                    if cycle % 20 == 0:
                        self.do_profile()

                else:
                    add_log("SYNC-FAIL", "Sync gagal — coba lagi...", "yellow")

            except Exception as e:
                add_log("ERR", str(e), "red")

            # Jeda ~6 detik
            sleep = 6 + random.uniform(-1, 2)
            slept = 0.0
            while slept < sleep and bot_running:
                time.sleep(0.5)
                slept += 0.5

        add_log("BOT", "Bot dihentikan.", "yellow")


# ═══════════════════════════════════════════════════════════════
#  RICH UI
# ═══════════════════════════════════════════════════════════════

def make_header() -> Panel:
    art = Text(justify="center")
    art.append("╔══════════════════════════════════════════╗\n", style="bold cyan")
    art.append("║  FOOD EMPIRE TYCOON — ULTIMATE BOT v2   ║\n", style="bold cyan")
    art.append("║  Auto-Claim | VIP Headless | Full Power  ║\n", style="bold cyan")
    art.append("╚══════════════════════════════════════════╝\n", style="bold cyan")
    art.append("  Telethon Auto-Login | No Browser Needed  ", style="dim white")
    return Panel(Align.center(art), border_style="cyan", padding=(0, 2))


def make_stats_panel(bot_obj: "FoodEmpireBot | None") -> Panel:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Key",   style="bold cyan", width=16)
    table.add_column("Value", style="white")

    with stats_lock:
        pi = dict(player_info)
        gs = dict(game_state)

    if bot_obj:
        table.add_row("Player",      pi.get("name", "—"))
        table.add_row("Tier",        str(pi.get("tier", "—")))
        table.add_row("Rank",        f"#{pi.get('rank','—')}")
        table.add_row("─" * 14,     "─" * 18)
        table.add_row("Cash",        f"{gs.get('cash', 0):>13,.0f}")
        table.add_row("Rate /s",     f"{gs.get('rate', 0)}")
        table.add_row("Gems",        f"{gs.get('gems', 0)}")
        table.add_row("TON Tips",    f"{gs.get('tips', 0)}")
        table.add_row("VIP Sisa",    f"{gs.get('vip_left', 0)} / hari")
        table.add_row("─" * 14,     "─" * 18)
        table.add_row("VIP Dilayani",   f"[bold green]{bot_obj.vip_served_total}[/bold green]")
        table.add_row("TON Diraih",     f"[bold yellow]{bot_obj.ton_earned_total}[/bold yellow]")
        table.add_row("Gems Diraih",    f"[bold cyan]{bot_obj.gems_earned_total}[/bold cyan]")
        table.add_row("Cycles",         f"{bot_obj.total_cycles}")
    else:
        table.add_row("Status", "[yellow]Bot belum berjalan[/yellow]")

    status = "[bold green]● RUNNING[/bold green]" if bot_running else "[bold red]● STOPPED[/bold red]"
    return Panel(table, title=f"[bold]STATISTIK  {status}[/bold]", border_style="green")


def make_log_panel(n: int = 25) -> Panel:
    with stats_lock:
        logs = list(bot_logs[-n:])

    text = Text()
    for t, tag, msg, color in logs:
        text.append(f"[{t}] ", style="dim")
        text.append(f"{tag:<11}", style=f"bold {color}")
        text.append(f" {msg}\n", style=color)

    return Panel(text, title="[bold]LOG AKTIVITAS[/bold]", border_style="blue", padding=(0, 1))


def make_menu_panel(logged_in: bool) -> Panel:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key",    width=4)
    table.add_column("Action")

    table.add_row("[bold cyan]1[/bold cyan]",    "Masukkan / Update initData")
    if logged_in:
        if bot_running:
            table.add_row("[bold red]2[/bold red]",    "STOP Bot")
        else:
            table.add_row("[bold green]2[/bold green]", "START Bot")
    table.add_row("[bold red]0[/bold red]",        "Keluar")

    return Panel(table, title="[bold]MENU[/bold]", border_style="yellow")


# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

async def main():
    global bot_running

    tg_client  : TelegramClient | None   = None
    bot_obj    : FoodEmpireBot  | None   = None
    init_data  : str | None              = None
    bot_thread : threading.Thread | None = None

    console.clear()
    console.print(make_header())
    console.print()

    # Auto-detect phone dari sesi sebelumnya
    saved_phone = ""
    if PHONE_FILE.exists():
        saved_phone = PHONE_FILE.read_text(encoding="utf-8").strip()
        if saved_phone:
            console.print(f"[dim]Nomor terakhir: {saved_phone}[/dim]")

    # Auto-load initData dari config.json jika tersedia
    cfg_init = load_config_init_data()
    if cfg_init:
        init_data = cfg_init
        bot_obj = FoodEmpireBot(init_data)
        console.print(f"[dim]initData dimuat dari config.json ({bot_obj.tg_name} / ID: {bot_obj.tg_id})[/dim]")

    console.print("[dim]Cloudflare bypass: otomatis via cloudscraper[/dim]")
    console.print()

    while True:
        can_start = (bot_obj is not None)
        console.print(make_menu_panel(logged_in=can_start))

        if bot_obj:
            console.print(Columns([
                make_stats_panel(bot_obj),
                make_log_panel(15)
            ]))
        elif bot_logs:
            console.print(make_log_panel(10))

        console.print()

        valid_choices = ["0", "1"]
        if can_start:
            valid_choices.append("2")

        default_choice = "2" if (can_start and not bot_running) else "1"

        choice = Prompt.ask(
            "[bold white]Pilih menu[/bold white]",
            choices=valid_choices,
            default=default_choice
        )
        console.print()

        # ── 0: Keluar ───────────────────────────────────────
        if choice == "0":
            bot_running = False
            if bot_thread and bot_thread.is_alive():
                bot_thread.join(timeout=5)
            console.print("[yellow]Sampai jumpa![/yellow]")
            break

        # ── 1: Masukkan / Update initData ────────────────────
        elif choice == "1":
            new_init = Prompt.ask("[bold cyan]Paste initData[/bold cyan]").strip()
            if new_init:
                cfg_path = BASE_DIR / "config.json"
                cfg_data = {}
                if cfg_path.exists():
                    try:
                        cfg_data = json.loads(cfg_path.read_text(encoding="utf-8"))
                    except Exception:
                        cfg_data = {}
                cfg_data["init_data"] = new_init
                cfg_path.write_text(json.dumps(cfg_data, indent=2, ensure_ascii=False), encoding="utf-8")

                init_data = new_init
                if bot_obj:
                    bot_obj.update_init_data(init_data)
                else:
                    bot_obj = FoodEmpireBot(init_data)
                console.print(
                    f"[bold green]initData disimpan ke config.json! "
                    f"TG ID: {bot_obj.tg_id} | Nama: {bot_obj.tg_name}[/bold green]"
                )
            else:
                console.print("[yellow]Dibatalkan — initData kosong.[/yellow]")
            console.print()
            input("Tekan Enter untuk lanjut...")
            console.clear()
            console.print(make_header())

        # ── 2: Start / Stop Bot ──────────────────────────────
        elif choice == "2":
            if bot_obj is None:
                console.print("[red]Login dulu (menu 1) atau pastikan config.json ada![/red]")
                input("Tekan Enter...")
                continue

            if bot_running:
                # Stop
                bot_running = False
                console.print("[yellow]Menghentikan bot...[/yellow]")
                if bot_thread and bot_thread.is_alive():
                    bot_thread.join(timeout=15)
                console.print("[green]Bot dihentikan.[/green]")
                input("Tekan Enter...")
                console.clear()
                console.print(make_header())
            else:
                # Start
                bot_running = True
                bot_logs.clear()

                def _run():
                    try:
                        bot_obj.run()
                    except Exception as e:
                        add_log("CRASH", str(e), "bold red")
                        global bot_running
                        bot_running = False

                bot_thread = threading.Thread(target=_run, daemon=True)
                bot_thread.start()

                console.print("[bold green]Bot berjalan! Ctrl+C untuk berhenti.[/bold green]")
                console.print("[dim](Tekan Ctrl+C untuk kembali ke menu)[/dim]")
                console.print()

                # Live display
                try:
                    with Live(console=console, refresh_per_second=1, screen=False) as live:
                        while bot_running:
                            live.update(Columns([
                                make_stats_panel(bot_obj),
                                make_log_panel(20)
                            ]))
                            await asyncio.sleep(1)
                except KeyboardInterrupt:
                    bot_running = False
                    console.print("\n[yellow]Bot dihentikan (Ctrl+C)[/yellow]")

                console.clear()
                console.print(make_header())

        # ── 3: Refresh initData ──────────────────────────────
        elif choice == "3":
            if tg_client is None:
                console.print("[red]Login dulu! (menu 1)[/red]")
                input("Tekan Enter...")
                continue

            console.print("[cyan]Memperbarui initData dari Telegram...[/cyan]")
            new_init = await get_init_data(tg_client)
            if new_init:
                init_data = new_init
                if bot_obj:
                    bot_obj.update_init_data(init_data)
                else:
                    bot_obj = FoodEmpireBot(init_data)
                console.print(
                    f"[green]initData diperbarui! auth_date={bot_obj.auth_date}[/green]"
                )
            else:
                console.print("[red]Gagal perbarui initData[/red]")
            console.print()
            input("Tekan Enter untuk lanjut...")
            console.clear()
            console.print(make_header())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        bot_running = False
        console.print("\n[yellow]Keluar...[/yellow]")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cashopolis Automation Bot
Automates claims, PTC ads, daily wheel spins, city power charging, and achievements for Cashopolis.site.
Dibuat oleh : BANG MIUN "RCH C12"
"""

import sys
import os
import time
import json
import argparse
from datetime import datetime
import requests
import colorama
from colorama import Fore, Style

# Ensure stdout handles UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

colorama.init(autoreset=True)

CREATOR = 'BANG MIUN "RCH C12"'
VERSION = "2.0"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

BASE_URL = "https://cashopolis.site"
SB_URL = "https://dexriqzqimmpgwkrdrau.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRleHJpcXpxaW1tcGd3a3JkcmF1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIyNDgzNjksImV4cCI6MjEwNzgyNDM2OX0.Hzr2CxHbGgRPD7bL0Ua3uBOdx0XUWxgWFpO60Jh3UQc"

# Symbol to word mapping matching game frontend
PTC_MAP = {
    '★': 'star',
    '♥': 'heart',
    '◆': 'diamond',
    '●': 'circle'
}

# ==============================================================================
# TAMPILAN (UI HELPERS)
# ==============================================================================

WIDTH = 66
C = Fore
RST = Style.RESET_ALL
BOLD = Style.BRIGHT
DIM = Fore.LIGHTBLACK_EX

LEVELS = {
    "ok":    ("✔", Fore.LIGHTGREEN_EX),
    "info":  ("●", Fore.LIGHTCYAN_EX),
    "start": ("▶", Fore.LIGHTBLUE_EX),
    "watch": ("◔", Fore.LIGHTMAGENTA_EX),
    "wait":  ("⏳", Fore.LIGHTYELLOW_EX),
    "warn":  ("⚠", Fore.YELLOW),
    "err":   ("✖", Fore.LIGHTRED_EX),
    "done":  ("★", Fore.LIGHTGREEN_EX),
    "dim":   ("·", Fore.LIGHTBLACK_EX),
}

TAG_LABEL = {
    "CONFIG": "CONFIG", "AUTH": "LOGIN", "API": "API", "STATUS": "STATUS",
    "POWER": "LISTRIK", "SPIN": "SPIN", "ACHIEVE": "PRESTASI", "PTC": "IKLAN PTC",
    "BOT": "BOT", "LOOP": "LOOP",
}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def line(char="─", color=Fore.CYAN):
    print(color + char * WIDTH + RST)


def box_top(color=Fore.CYAN):
    print(color + "╔" + "═" * (WIDTH - 2) + "╗" + RST)


def box_bottom(color=Fore.CYAN):
    print(color + "╚" + "═" * (WIDTH - 2) + "╝" + RST)


def box_row(text="", color=Fore.CYAN, text_color=Fore.WHITE, center=True):
    inner = WIDTH - 4
    text = text[:inner]
    pad = text.center(inner) if center else text.ljust(inner)
    print(f"{color}║ {text_color}{pad}{color} ║{RST}")


def section(title):
    print()
    print(f"{Fore.LIGHTCYAN_EX}┌─ {BOLD}{title}{RST}{Fore.LIGHTCYAN_EX} " + "─" * max(2, WIDTH - len(title) - 5) + RST)


def fmt_time(sec):
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def bar(cur, total, size=16):
    if total <= 0:
        return ""
    cur = min(cur, total)
    filled = int(size * cur / total)
    return "█" * filled + "░" * (size - filled)


def print_banner():
    print(Fore.LIGHTYELLOW_EX + BOLD + r"""
   ____          _                     _ _
  / ___|__ _ ___| |__   ___  _ __   ___ | (_)___
 | |   / _` / __| '_ \ / _ \| '_ \ / _ \| | / __|
 | |__| (_| \__ \ | | | (_) | |_) | (_) | | \__ \
  \____\__,_|___/_| |_|\___/| .__/ \___/|_|_|___/
                            |_|""" + RST)
    box_top(Fore.LIGHTMAGENTA_EX)
    box_row(f"AUTOMATION BOT v{VERSION}  •  cashopolis.site", Fore.LIGHTMAGENTA_EX, Fore.LIGHTYELLOW_EX)
    box_row("Auto Claim  •  PTC Ads  •  Spin  •  Power  •  Achievement", Fore.LIGHTMAGENTA_EX, Fore.WHITE)
    box_row(f"Dibuat oleh : {CREATOR}", Fore.LIGHTMAGENTA_EX, Fore.LIGHTGREEN_EX)
    box_bottom(Fore.LIGHTMAGENTA_EX)


def pause(msg="Tekan Enter untuk kembali ke Menu..."):
    try:
        input(f"\n{DIM}{msg}{RST}")
    except (KeyboardInterrupt, EOFError):
        pass


def sleep_countdown(seconds, label="Siklus berikutnya"):
    """Hitung mundur dengan progress bar. Ctrl+C melempar KeyboardInterrupt."""
    total = max(1, int(seconds))
    for left in range(total, 0, -1):
        print(f"\r{DIM}⏳ {label}: {C.LIGHTYELLOW_EX}{fmt_time(left)}{DIM} "
              f"[{C.LIGHTYELLOW_EX}{bar(total - left, total)}{DIM}]  Ctrl+C = kembali ke menu{RST}   ",
              end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 110 + "\r", end="", flush=True)


class CashopolisBot:
    def __init__(self, config_path=None, auto_prompt=True):
        if config_path is None:
            self.config_path = DEFAULT_CONFIG_PATH
        elif not os.path.isabs(config_path):
            self.config_path = os.path.join(SCRIPT_DIR, config_path)
        else:
            self.config_path = config_path

        self.auto_prompt = auto_prompt
        self.config = self.load_config(self.config_path)
        self.email = self.config.get("email", "")
        self.password = self.config.get("password", "")
        self.username = None
        self.display_name = None
        self.token = None
        self.start_blk = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/"
        })

    # ------------------------------------------------------------------ log
    def log(self, tag, message, color=None, level="info"):
        """Log rapi: JAM │ ikon LABEL │ pesan. Parameter color lama dipetakan ke level."""
        if color is not None:
            level = {
                Fore.GREEN: "ok", Fore.RED: "err", Fore.YELLOW: "warn",
                Fore.LIGHTBLACK_EX: "dim", Fore.LIGHTGREEN_EX: "ok",
                Fore.LIGHTMAGENTA_EX: "watch", Fore.LIGHTBLUE_EX: "info",
            }.get(color, level)
        icon, col = LEVELS.get(level, LEVELS["info"])
        ts = datetime.now().strftime("%H:%M:%S")
        label = TAG_LABEL.get(tag, tag)
        print(f"{DIM}{ts} │ {col}{icon} {label:<9}{DIM} │ {col}{message}{RST}")

    # --------------------------------------------------------------- config
    def load_config(self, path):
        if not os.path.exists(path):
            self.log("CONFIG", f"File '{os.path.basename(path)}' belum ada → membuat template default", level="warn")
            default_cfg = {
                "email": "",
                "password": "",
                "auto_daily_spin": True,
                "auto_claim_achievements": True,
                "auto_charge_power": True,
                "auto_claim_ptc": True,
                "auto_sync_state": True,
                "ptc_max_wait_seconds": 60,
                "loop_interval_minutes": 30
            }
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(default_cfg, f, indent=2)
            except Exception as e:
                self.log("CONFIG", f"Gagal menyimpan config default: {e}", level="err")
            return default_cfg

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.log("CONFIG", f"Error membaca config: {e} → memakai default", level="err")
            return {}

    def save_config(self):
        self.config["email"] = self.email
        self.config["password"] = self.password
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.log("CONFIG", f"Gagal menyimpan config: {e}", level="warn")

    # ---------------------------------------------------------- credentials
    def prompt_credentials(self, force=False):
        print()
        box_top()
        box_row("PANEL LOGIN CASHOPOLIS", Fore.CYAN, Fore.LIGHTYELLOW_EX)
        box_bottom()
        if self.email and self.password:
            print(f"{DIM}  (Tekan Enter untuk memakai nilai yang tersimpan){RST}\n")
        else:
            print(f"{DIM}  (Silakan masukkan akun Cashopolis Anda){RST}\n")

        current_email = self.email.strip() if self.email else ""
        while True:
            if current_email:
                prompt_text = f"  {C.LIGHTCYAN_EX}✉  Email    {RST}[{C.LIGHTGREEN_EX}{current_email}{RST}]: "
            else:
                prompt_text = f"  {C.LIGHTCYAN_EX}✉  Email    {RST}: "
            try:
                entered = input(prompt_text).strip()
            except (KeyboardInterrupt, EOFError):
                print("\n  Dibatalkan.")
                return False
            if entered:
                self.email = entered
                break
            elif current_email:
                self.email = current_email
                break
            print(f"  {Fore.LIGHTRED_EX}✖ Email tidak boleh kosong!{RST}")

        current_pwd = self.password.strip() if self.password else ""
        while True:
            if current_pwd:
                hint = "*" * min(len(current_pwd), 8)
                prompt_text = f"  {C.LIGHTCYAN_EX}🔑 Password {RST}[{C.LIGHTGREEN_EX}{hint}{RST}]: "
            else:
                prompt_text = f"  {C.LIGHTCYAN_EX}🔑 Password {RST}: "
            try:
                entered = input(prompt_text).strip()
            except (KeyboardInterrupt, EOFError):
                print("\n  Dibatalkan.")
                return False
            if entered:
                self.password = entered
                break
            elif current_pwd:
                self.password = current_pwd
                break
            print(f"  {Fore.LIGHTRED_EX}✖ Password tidak boleh kosong!{RST}")

        self.save_config()
        print(f"\n  {Fore.LIGHTGREEN_EX}✔ Kredensial tersimpan di config.json{RST}\n")
        return True

    # ----------------------------------------------------------------- auth
    def login(self, max_retries=3):
        for attempt in range(1, max_retries + 1):
            if not self.email or not self.password:
                if not self.prompt_credentials():
                    return False

            self.log("AUTH", f"Login sebagai {self.email} ...", level="start")
            url = f"{BASE_URL}/api/login"
            payload = {"email": self.email, "password": self.password}
            try:
                res = self.session.post(url, json=payload, timeout=15)
                data = res.json()
                if res.ok and data.get("ok"):
                    self.username = data.get("username")
                    self.display_name = data.get("displayName") or self.username
                    self.token = data.get("token")
                    self.log("AUTH", f"Login BERHASIL │ Mayor: {self.display_name} ({self.username})", level="ok")
                    return True

                err_msg = data.get('error', 'Email atau password salah')
                self.log("AUTH", f"Login GAGAL: {err_msg}", level="err")

                if attempt < max_retries:
                    try:
                        ans = input(f"\n  {Fore.LIGHTYELLOW_EX}? Masukkan ulang email/password? (Y/n): {RST}").strip().lower()
                    except (KeyboardInterrupt, EOFError):
                        return False
                    if ans in ['', 'y', 'yes', 'ya']:
                        self.email = ""
                        self.password = ""
                        if not self.prompt_credentials():
                            return False
                    else:
                        return False
                else:
                    return False
            except Exception as e:
                self.log("AUTH", f"Error jaringan saat login: {e}", level="err")
                if attempt == max_retries:
                    return False
                time.sleep(2)
        return False

    def api_post(self, endpoint, data=None):
        url = f"{BASE_URL}{endpoint}"
        payload = data or {}
        if "username" not in payload and self.username:
            payload["username"] = self.username
        if "token" not in payload and self.token:
            payload["token"] = self.token

        try:
            res = self.session.post(url, json=payload, timeout=15)
            if res.status_code == 401:
                self.log("AUTH", "Token kedaluwarsa → login ulang...", level="warn")
                if self.login():
                    payload["username"] = self.username
                    payload["token"] = self.token
                    res = self.session.post(url, json=payload, timeout=15)
                else:
                    return None
            return res.json()
        except Exception as e:
            self.log("API", f"Request ke {endpoint} gagal: {e}", level="err")
            return None

    # --------------------------------------------------------------- status
    def get_profile(self):
        data = self.api_post("/api/sync-state", {"peek": True})
        if not data or not data.get("ok"):
            state_data = self.api_post("/api/my-state")
            if state_data and state_data.get("ok") and state_data.get("row"):
                row = state_data["row"]
                return {"blk": row.get("blk", 0), "pblk": row.get("pblk", 0)}
            return None
        return {"blk": data.get("blk", 0), "pblk": data.get("pblk", 0)}

    def print_status(self):
        prof = self.get_profile()
        if not prof:
            self.log("STATUS", "Gagal mengambil ringkasan akun.", level="err")
            return

        blk_earned = prof["blk"] / 100.0
        pblk_spend = prof["pblk"] / 100.0
        if self.start_blk is None:
            self.start_blk = blk_earned
        profit = blk_earned - self.start_blk

        print()
        box_top(Fore.LIGHTMAGENTA_EX)
        box_row(f"DASHBOARD  •  Mayor: {self.display_name}", Fore.LIGHTMAGENTA_EX, Fore.LIGHTYELLOW_EX)
        box_row(f"💰 Earned BLK (bisa WD) : {blk_earned:.3f} BLK", Fore.LIGHTMAGENTA_EX, Fore.LIGHTGREEN_EX, False)
        box_row(f"🏙️  Spend BLK (in-game)  : {pblk_spend:.3f} BLK", Fore.LIGHTMAGENTA_EX, Fore.LIGHTCYAN_EX, False)
        box_row(f"📈 Profit sesi ini      : {profit:+.3f} BLK", Fore.LIGHTMAGENTA_EX, Fore.LIGHTGREEN_EX if profit >= 0 else Fore.LIGHTRED_EX, False)
        box_bottom(Fore.LIGHTMAGENTA_EX)
        print()

    # ---------------------------------------------------------------- tasks
    def auto_charge_power(self):
        section("LISTRIK KOTA")
        self.log("POWER", "Mengecek status listrik kota...", level="start")
        res = self.api_post("/api/power", {"action": "status"})
        if not res or not res.get("ok"):
            self.log("POWER", "Gagal mengambil status listrik.", level="warn")
            return

        until = res.get("until", 0)
        now = res.get("now", int(time.time() * 1000))
        hours_left = max(0, until - now) / (1000 * 3600)
        self.log("POWER", f"Sisa listrik kota: {hours_left:.1f} jam", level="info")

        if hours_left < 24:
            self.log("POWER", "Listrik hampir habis (< 24 jam) → mengisi ulang...", level="wait")
            charge_res = self.api_post("/api/power", {"action": "charge"})
            if charge_res and charge_res.get("ok"):
                new_until = charge_res.get("until", 0)
                new_hours = max(0, new_until - now) / (1000 * 3600)
                until_str = datetime.fromtimestamp(new_until / 1000).strftime('%Y-%m-%d %H:%M')
                self.log("POWER", f"Listrik terisi! Aktif {new_hours:.1f} jam (sampai {until_str})", level="ok")
            else:
                self.log("POWER", "Gagal mengisi listrik kota.", level="err")
        else:
            self.log("POWER", "Listrik kota masih aman", level="ok")

    def auto_daily_spin(self):
        section("DAILY SPIN WHEEL")
        self.log("SPIN", "Mengecek roda harian...", level="start")
        res = self.api_post("/api/daily-spin", {"action": "status"})
        if not res or not res.get("ok"):
            self.log("SPIN", "Gagal mengambil status spin.", level="warn")
            return

        is_ready = res.get("ready", False)
        next_at = res.get("nextAt", 0)

        if not is_ready:
            if next_at > 0:
                t = datetime.fromtimestamp(next_at / 1000).strftime("%Y-%m-%d %H:%M:%S")
                self.log("SPIN", f"Belum siap │ spin gratis berikutnya: {t}", level="wait")
            else:
                self.log("SPIN", "Spin harian belum siap.", level="wait")
            return

        self.log("SPIN", "Spin SIAP! Memutar roda...", level="watch")
        spin_res = self.api_post("/api/daily-spin", {"action": "spin"})
        if not spin_res or not spin_res.get("ok"):
            err = spin_res.get('error', 'Tidak diketahui') if spin_res else 'Error jaringan'
            self.log("SPIN", f"Spin gagal: {err}", level="err")
            return

        prize = spin_res.get("prize")
        label = spin_res.get("label", prize)
        if prize == "none":
            self.log("SPIN", f"Hasil: belum beruntung ({label})", level="warn")
        else:
            self.log("SPIN", f"MENANG: {label}!  (ID hadiah: {prize})", level="done")

    def auto_claim_achievements(self):
        section("ACHIEVEMENT")
        self.log("ACHIEVE", "Mengecek achievement...", level="start")
        res = self.api_post("/api/claim-achievement", {"action": "status"})
        if not res or not res.get("ok"):
            self.log("ACHIEVE", "Gagal mengambil status achievement.", level="warn")
            return

        ready = res.get("ready", [])
        claimed = res.get("claimed", {})
        unclaimed = [aid for aid in ready if not claimed.get(aid)]
        if not unclaimed:
            self.log("ACHIEVE", f"Tidak ada achievement baru │ total diklaim: {len(claimed)}", level="dim")
            return

        self.log("ACHIEVE", f"Ditemukan {len(unclaimed)} achievement siap klaim: {', '.join(map(str, unclaimed))}", level="ok")
        for aid in unclaimed:
            self.log("ACHIEVE", f"Mengklaim '{aid}'...", level="start")
            claim_res = self.api_post("/api/claim-achievement", {"id": aid})
            if claim_res and claim_res.get("ok"):
                reward = claim_res.get("reward", 0)
                self.log("ACHIEVE", f"'{aid}' BERHASIL  +{reward / 100.0:.3f} Spend BLK ({reward} unit)", level="ok")
            else:
                err = claim_res.get('error') if claim_res else 'Error'
                self.log("ACHIEVE", f"Gagal klaim '{aid}': {err}", level="err")
            time.sleep(1)

    def get_ptc_ads(self):
        sb_headers = {
            "apikey": SB_KEY,
            "Authorization": f"Bearer {SB_KEY}",
            "Content-Type": "application/json"
        }
        sb_url = f"{SB_URL}/rest/v1/ptc_ads?active=eq.true&clicks_remaining=gt.0&select=*&order=id.asc"
        try:
            r = self.session.get(sb_url, headers=sb_headers, timeout=15)
            active_ads = r.json() if r.ok else []
        except Exception as e:
            self.log("PTC", f"Gagal mengambil daftar iklan: {e}", level="err")
            return [], []

        status_url = f"{BASE_URL}/api/ptc-status?username={self.username}"
        try:
            r2 = self.session.get(status_url, headers={"X-Player-Token": self.token}, timeout=15)
            claimed = r2.json().get("claimed", []) if r2.ok else []
        except Exception as e:
            self.log("PTC", f"Gagal mengambil status klaim: {e}", level="err")
            claimed = []
        return active_ads, claimed

    def auto_claim_ptc(self):
        section("IKLAN PTC")
        self.log("PTC", "Mencari iklan sponsor PTC...", level="start")
        active_ads, claimed_ids = self.get_ptc_ads()

        unclaimed_ads = [ad for ad in active_ads if ad.get("id") not in claimed_ids]
        if not unclaimed_ads:
            self.log("PTC", f"Semua iklan PTC sudah selesai ({len(claimed_ids)} diklaim hari ini)", level="done")
            return

        total = len(unclaimed_ads)
        self.log("PTC", f"Ada {total} iklan PTC yang belum diklaim", level="info")

        total_earned = 0.0
        success = 0
        for idx, ad in enumerate(unclaimed_ads, start=1):
            ad_id = ad.get("id")
            title = ad.get("title", f"Ad #{ad_id}")
            reward = ad.get("reward", 0)
            tag_no = f"[{idx}/{total}]"

            self.log("PTC", f"{tag_no} {title} │ ID {ad_id} │ hadiah +{reward / 100:.3f} BLK", level="start")
            start_res = self.api_post("/api/ptc-start", {"ad_id": ad_id})

            if not start_res or not start_res.get("token"):
                err = start_res.get("error", "Gagal memulai") if start_res else "Error jaringan"
                self.log("PTC", f"{tag_no} Tidak bisa membuka iklan {ad_id}: {err}", level="err")
                continue

            ptc_token = start_res.get("token")
            target_symbol = start_res.get("target")
            duration = start_res.get("seconds", 15)

            max_wait = self.config.get("ptc_max_wait_seconds", 60)
            if duration > max_wait:
                self.log("PTC", f"{tag_no} Durasi {duration}s melebihi batas {max_wait}s → dilewati", level="warn")
                continue

            symbol_name = PTC_MAP.get(target_symbol, target_symbol)
            self.log("PTC", f"{tag_no} Menonton {duration} detik │ target: '{target_symbol}' ({symbol_name})", level="watch")

            for sec_left in range(duration, 0, -1):
                done = duration - sec_left
                sys.stdout.write(f"\r{DIM}   ◔ {bar(done, duration, 20)} {sec_left:>3}s tersisa  {RST}")
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r" + " " * 60 + "\r")
            sys.stdout.flush()

            time.sleep(1.2)

            self.log("PTC", f"{tag_no} Mengirim verifikasi jawaban '{target_symbol}'...", level="info")
            claim_url = f"{BASE_URL}/api/ptc-claim"
            try:
                c_res = self.session.post(claim_url, json={"token": ptc_token, "answer": target_symbol}, timeout=15)
                c_data = c_res.json()
                if c_res.ok and c_data.get("ok"):
                    earned_units = c_data.get("reward", reward)
                    earned_blk = earned_units / 100.0
                    total_earned += earned_blk
                    success += 1
                    self.log("PTC", f"{tag_no} BERHASIL  +{earned_blk:.3f} BLK ({earned_units} unit)", level="ok")
                else:
                    self.log("PTC", f"{tag_no} Klaim ditolak: {c_data.get('error', 'Tidak diketahui')}", level="err")
            except Exception as e:
                self.log("PTC", f"{tag_no} Error saat klaim: {e}", level="err")

            time.sleep(2)

        if total_earned > 0:
            self.log("PTC", f"Selesai! {success}/{total} iklan sukses │ total +{total_earned:.3f} BLK", level="done")

    # ------------------------------------------------------------- run modes
    def run_all(self):
        if self.auto_prompt and (not self.email or not self.password):
            if not self.prompt_credentials():
                return False

        print()
        line("═", Fore.LIGHTCYAN_EX)
        self.log("BOT", "MULAI SIKLUS CASHOPOLIS BOT", level="start")
        line("═", Fore.LIGHTCYAN_EX)
        if not self.login():
            self.log("BOT", "Siklus dibatalkan karena login gagal.", level="err")
            return False

        self.print_status()

        if self.config.get("auto_charge_power", True):
            self.auto_charge_power()
        if self.config.get("auto_daily_spin", True):
            self.auto_daily_spin()
        if self.config.get("auto_claim_achievements", True):
            self.auto_claim_achievements()
        if self.config.get("auto_claim_ptc", True):
            self.auto_claim_ptc()

        self.print_status()
        box_top(Fore.LIGHTGREEN_EX)
        box_row("★ SIKLUS SELESAI — SEMUA TUGAS SUDAH DIKERJAKAN", Fore.LIGHTGREEN_EX, Fore.LIGHTGREEN_EX)
        box_bottom(Fore.LIGHTGREEN_EX)
        return True

    def run_loop(self, interval_minutes=None):
        """Loop terus-menerus. Ctrl+C kembali ke menu (tidak menutup aplikasi)."""
        if self.auto_prompt and (not self.email or not self.password):
            if not self.prompt_credentials():
                return

        interval = interval_minutes or self.config.get("loop_interval_minutes", 30)
        self.log("LOOP", f"Mode otomatis aktif │ interval {interval} menit │ Ctrl+C untuk kembali ke menu", level="start")
        cycle = 0
        while True:
            cycle += 1
            try:
                self.log("LOOP", f"Siklus ke-{cycle}", level="info")
                self.run_all()
                sleep_countdown(interval * 60, f"Siklus ke-{cycle + 1} dalam")
            except KeyboardInterrupt:
                print()
                self.log("LOOP", "Mode otomatis dihentikan → kembali ke menu", level="warn")
                break
            except Exception as e:
                self.log("LOOP", f"Error tak terduga: {e}", level="err")
                try:
                    sleep_countdown(60, "Mencoba lagi dalam")
                except KeyboardInterrupt:
                    print()
                    break


# ==============================================================================
# MENU UTAMA (aplikasi tidak menutup sendiri setelah bot selesai)
# ==============================================================================

def menu(bot, interval=None):
    while True:
        clear_screen()
        print_banner()
        akun = bot.email if bot.email else "(belum diatur)"
        print()
        box_top()
        box_row("PANEL KONTROL", Fore.CYAN, Fore.LIGHTYELLOW_EX)
        box_row(f"Akun: {akun}", Fore.CYAN, Fore.LIGHTGREEN_EX if bot.email else Fore.LIGHTRED_EX)
        box_bottom()
        print(f"  {C.LIGHTCYAN_EX}[1]{RST} ▶  Jalankan sekali  {DIM}(semua tugas 1x lalu kembali ke menu){RST}")
        print(f"  {C.LIGHTCYAN_EX}[2]{RST} 🔁 Mode otomatis    {DIM}(loop tiap {interval or bot.config.get('loop_interval_minutes', 30)} menit){RST}")
        print(f"  {C.LIGHTCYAN_EX}[3]{RST} 📊 Cek saldo & status")
        print(f"  {C.LIGHTCYAN_EX}[4]{RST} 🔑 Ganti email / password")
        print(f"  {C.LIGHTCYAN_EX}[0]{RST} ❌ Keluar")
        line("─")
        print(f"{DIM}  Dibuat oleh {CREATOR}{RST}")

        try:
            pilihan = input(f"\n{BOLD}Pilih menu [0-4]: {RST}").strip()
        except (KeyboardInterrupt, EOFError):
            pilihan = "0"

        if pilihan == "1":
            bot.run_all()
            pause()
        elif pilihan == "2":
            bot.run_loop(interval_minutes=interval)
            pause()
        elif pilihan == "3":
            if bot.login():
                bot.print_status()
            pause()
        elif pilihan == "4":
            bot.prompt_credentials(force=True)
            time.sleep(1)
        elif pilihan == "0":
            print(Fore.LIGHTGREEN_EX + f"\n  Terima kasih! Sampai jumpa.\n  — {CREATOR}\n")
            break
        else:
            print(Fore.LIGHTRED_EX + "  ✖ Pilihan tidak valid.")
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="Cashopolis Automation Bot")
    parser.add_argument("--config", "-c", default=None, help="Path to configuration JSON file")
    parser.add_argument("--loop", "-l", action="store_true", help="Langsung jalankan mode loop")
    parser.add_argument("--interval", "-i", type=int, default=None, help="Loop interval in minutes (default from config or 30)")
    parser.add_argument("--status", "-s", action="store_true", help="Tampilkan saldo lalu kembali ke menu")
    parser.add_argument("--no-prompt", action="store_true", help="Skip interactive credential input prompt")
    parser.add_argument("--change-login", action="store_true", help="Force change email/password prompt")
    args = parser.parse_args()

    os.chdir(SCRIPT_DIR)

    clear_screen()
    print_banner()
    bot = CashopolisBot(config_path=args.config, auto_prompt=not args.no_prompt)

    # Setup kredensial awal bila perlu
    if args.change_login or not bot.email or not bot.password:
        if not args.no_prompt:
            bot.prompt_credentials(force=args.change_login)

    # Opsi CLI dijalankan dulu, lalu masuk menu (tidak keluar aplikasi)
    try:
        if args.status:
            if bot.login():
                bot.print_status()
            pause()
        elif args.loop:
            bot.run_loop(interval_minutes=args.interval)
            pause()
    except KeyboardInterrupt:
        pass

    menu(bot, interval=args.interval)


if __name__ == "__main__":
    main()
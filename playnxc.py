#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║            🎮  P L A Y N X C   —  AUTO  CLAIM  BOT            ║
║  Login   : Telegram Mini App initData (tanpa cookie/cURL)     ║
║  Claim   : PTC Direct-Link + PTC Site (emoji-captcha) + Ref   ║
║  Author  : AHD1905   |   Grup : ScriptyXsouu                  ║
╚══════════════════════════════════════════════════════════════╝

Cara pakai:
  1. Buka PlayNXC di dalam bot Telegram (@PlayNXC_bot -> Open App).
  2. Ambil initData (lihat README/menu Input Config) lalu paste ke bot ini.
  3. Pilih menu "Auto Claim". Ulangi ambil initData baru kalau server
     menolak karena initData kedaluwarsa (auth_date terlalu lama).
"""

import os
import sys
import time
import json
import re
import io
import base64
import colorsys
from urllib.parse import quote

try:
    import requests
except ImportError:
    sys.exit("\n[!] Modul 'requests' belum terpasang. Jalankan: pip install requests\n")

try:
    from PIL import Image, ImageFont, ImageDraw
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

# ── Warna terminal ────────────────────────────────────────────────────────────
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[1;31m"
C_GREEN = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_BLUE = "\033[1;34m"
C_PURPLE = "\033[1;35m"
C_CYAN = "\033[1;36m"
C_WHITE = "\033[1;37m"
C_GREY = "\033[0;37m"

BASE = "https://playnxc.com"
API_URL = BASE + "/api/telegramapp"
PTCVIEW_URL = BASE + "/api/ptc-view"
UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36")

CONFIG_FILE = "playnxc_config.json"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def msg(text, is_final=False):
    if is_final:
        sys.stdout.write("\r\033[K" + text + "\n")
        sys.stdout.flush()
        return
    sys.stdout.write("\r\033[K" + text)
    sys.stdout.flush()


# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


# ── Emoji captcha solver (pick_emoji) ─────────────────────────────────────────
# Tile captcha bukan glyph emoji, tapi ikon vektor flat di atas latar putih
# (diamond=cyan, water=biru, fire=oranye, lemon/kuning, leaf=hijau, dst).
# Jadi pencocokan paling andal = HUE dominan ikon, bukan render font emoji.
#
# Peta karakter emoji -> hue (derajat 0-360). None = putih/abu (saturasi rendah).
EMOJI_HUE = {
    "\U0001F48E": 190,  # 💎 diamond (cyan)
    "\U0001F537": 210, "\U0001F535": 210, "\U0001F30A": 205,  # 🔷🔵 biru
    "\U0001F4A7": 205,  # 💧 water drop (biru)
    "\U0001F525": 18,   # 🔥 fire (oranye/merah)
    "\U0001F34B": 52,   # 🍋 lemon (kuning)
    "⭐": 52, "\U0001F31F": 52, "✨": 52,   # ⭐🌟✨ (kuning)
    "\U0001F319": 50, "\U0001F311": 50,    # 🌙🌑 moon (kuning)
    "⚡": 52,           # ⚡ lightning (kuning)
    "\U0001F343": 120, "\U0001F33F": 120, "\U0001F331": 120, "\U0001F34F": 110,  # 🍃🌿🍏 hijau
    "\U0001F338": 330, "\U0001F33A": 330, "\U0001F337": 330,  # 🌸🌷 pink
    "\U0001F352": 352, "\U0001F34E": 3,    # 🍒🍎 merah
    "❤️": 0, "\U0001F534": 0,             # ❤️🔴 merah
    "❄️": 195,          # ❄️ snowflake (biru muda)
    "☁️": None, "⚪": None,            # ☁️ cloud/putih (saturasi rendah)
    "\U0001F7E2": 120, "\U0001F7E1": 52, "\U0001F7E0": 30, "\U0001F7E3": 280,  # 🟢🟠🟣
}
# Peta kata nama (fallback bila emoji tak terpetakan) -> hue.
NAME_HUE = {
    "diamond": 190, "water": 205, "drop": 205, "blue": 205,
    "fire": 18, "flame": 18, "lemon": 52, "star": 52, "moon": 50,
    "lightning": 52, "bolt": 52, "leaf": 120, "grass": 120, "green": 120,
    "flower": 330, "blossom": 330, "cherry": 352, "cherries": 352,
    "apple": 3, "red": 0, "cloud": None, "snow": 195, "purple": 280,
    "orange": 30, "yellow": 52,
}
_UNKNOWN = object()


def _extract_target_emoji(prompt):
    """Ambil karakter emoji pertama dari prompt (mis. 'Pick the ☁️ cloud')."""
    for ch in prompt or "":
        cp = ord(ch)
        if cp in (0x200D, 0xFE0E, 0xFE0F):   # ZWJ / variation selector
            continue
        if cp >= 0x2600:                        # blok simbol & emoji
            return ch
    return None


def _target_hue(prompt):
    """Kembalikan hue target (float/None utk putih) atau _UNKNOWN bila tak dikenal."""
    for ch in prompt or "":
        if ch in EMOJI_HUE:
            return EMOJI_HUE[ch]
    low = (prompt or "").lower()
    for w, h in NAME_HUE.items():
        if w in low:
            return h
    return _UNKNOWN


def _tile_to_image(tile):
    data = tile.get("image", "")
    if not data:
        return None
    try:
        if data.startswith("data:"):
            data = data.split(",", 1)[1]
        return Image.open(io.BytesIO(base64.b64decode(data)))
    except Exception:
        return None


def _dom_hue(im):
    """Hitung hue dominan (derajat) + rata-rata saturasi sebuah ikon tile.
    Pixel latar (near-white) diabaikan supaya tidak menenggelamkan warna."""
    im = im.convert("RGBA").resize((32, 32))
    hist = [0.0] * 36
    sat_sum = 0.0
    fg = 0
    for r, g, b, a in im.getdata():
        if a < 128:
            continue
        if r > 235 and g > 235 and b > 235:   # latar putih
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        sat_sum += s
        fg += 1
        if s < 0.12:                            # nyaris abu-abu
            continue
        hist[int(h * 36) % 36] += s * v
    if fg == 0:
        return 0.0, 0.0
    peak = max(range(36), key=lambda i: hist[i])
    domhue = (peak + 0.5) * 10.0 if hist[peak] > 0 else -1.0
    return domhue, sat_sum / fg


def _huedist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def pick_emoji_tile(challenge):
    """Kembalikan (tile_id, info). Pilih tile dgn hue paling dekat target."""
    tiles = challenge.get("tiles") or []
    if not tiles:
        return None, "no-tiles"
    prompt = challenge.get("prompt", "")
    th = _target_hue(prompt)
    if th is _UNKNOWN or not HAVE_PIL:
        return tiles[0]["id"], "fallback-first"

    scored = []
    for t in tiles:
        im = _tile_to_image(t)
        if im is None:
            continue
        dh, ds = _dom_hue(im)
        if th is None:                 # target putih/cloud -> paling rendah saturasi
            score = -ds
        else:
            score = _huedist(dh, th) if dh >= 0 else 999
        scored.append((score, t["id"], dh, ds))
    if not scored:
        return tiles[0]["id"], "no-decodable-tile"
    scored.sort(key=lambda x: x[0])
    best = scored[0]
    tgt = "white" if th is None else int(th)
    return best[1], f"hue~{int(best[2])} tgt~{tgt} d={int(best[0])}"


# ── Emoji captcha solver v2 (color-band + shape classifier) ─────────────────
# 14 konsep ikon tetap; hue saja tidak cukup utk keluarga kuning.
WEIGHTS = [3.0, 3.0, 2.0, 6.0, 8.0, 8.0, 6.0, 4.0, 4.0]
CONCEPTS = {
    "diamond":   (0.00, 0.00, 0.00, 0.00, 0.99, 0.00, 0.00, 0.01, 0.60),
    "water":     (0.00, 0.00, 0.00, 0.00, 0.00, 0.97, 0.00, 0.02, 0.65),
    "fire":      (0.00, 0.72, 0.25, 0.00, 0.00, 0.00, 0.00, 0.02, 0.58),
    "lemon":     (0.00, 0.02, 0.90, 0.07, 0.00, 0.00, 0.00, 0.01, 0.74),
    "leaf":      (0.00, 0.00, 0.00, 0.92, 0.00, 0.00, 0.00, 0.05, 0.45),
    "star":      (0.00, 0.00, 0.95, 0.00, 0.00, 0.00, 0.00, 0.03, 0.42),
    "moon":      (0.00, 0.00, 0.95, 0.00, 0.00, 0.00, 0.00, 0.02, 0.55),
    "lightning": (0.00, 0.00, 0.94, 0.00, 0.00, 0.00, 0.00, 0.04, 0.34),
    "sun":       (0.00, 0.06, 0.90, 0.00, 0.00, 0.00, 0.00, 0.03, 0.62),
    "cloud":     (0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.95, 0.60),
    "flower":    (0.00, 0.00, 0.11, 0.00, 0.00, 0.00, 0.82, 0.03, 0.68),
    "cherry":    (0.70, 0.05, 0.01, 0.12, 0.00, 0.00, 0.00, 0.09, 0.46),
    "apple":     (0.80, 0.05, 0.00, 0.11, 0.00, 0.00, 0.00, 0.03, 0.66),
    "heart":     (0.97, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.02, 0.66),
}
EMOJI_CONCEPT = {
    "\U0001F48E": "diamond", "\U0001F4A7": "water", "\U0001F525": "fire",
    "\U0001F34B": "lemon", "\U0001F343": "leaf", "\U0001F33F": "leaf",
    "\u2B50": "star", "\U0001F31F": "star", "\u2728": "star",
    "\U0001F319": "moon", "\U0001F31C": "moon", "\u26A1": "lightning",
    "\u2600": "sun", "\U0001F31E": "sun", "\U0001F506": "sun",
    "\u2601": "cloud", "\U0001F324": "cloud", "\U0001F325": "cloud",
    "\U0001F338": "flower", "\U0001F33A": "flower", "\U0001F337": "flower",
    "\U0001F352": "cherry", "\U0001F34E": "apple", "\u2764": "heart",
}
NAME_CONCEPT = {
    "diamond": "diamond", "water": "water", "drop": "water", "fire": "fire",
    "flame": "fire", "lemon": "lemon", "leaf": "leaf", "grass": "leaf",
    "star": "star", "moon": "moon", "lightning": "lightning", "bolt": "lightning",
    "sun": "sun", "cloud": "cloud", "flower": "flower", "blossom": "flower",
    "cherry": "cherry", "cherries": "cherry", "apple": "apple", "heart": "heart",
}


def _norm(s):
    return "".join(c for c in (s or "") if ord(c) not in (0xFE0F, 0xFE0E, 0x200D))


def _prompt_concept(prompt):
    p = _norm(prompt)
    for emo, c in EMOJI_CONCEPT.items():
        if emo in p:
            return c
    low = (prompt or "").lower()
    for w, c in NAME_CONCEPT.items():
        if w in low:
            return c
    return None


def _tile_features(im):
    """Vektor fitur [red,orange,yellow,green,cyan,blue,pink,gray,fill] + mean_sat."""
    im = im.convert("RGB").resize((48, 48))
    W, H = im.size
    px = im.load()
    bands = [0.0] * 7
    gray = 0.0
    fg = 0
    sat_sum = 0.0
    minx, miny, maxx, maxy = W, H, 0, 0
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            if r > 225 and g > 225 and b > 225:
                continue
            fg += 1
            if x < minx: minx = x
            if x > maxx: maxx = x
            if y < miny: miny = y
            if y > maxy: maxy = y
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            sat_sum += s
            hd = h * 360.0
            if s < 0.18:
                gray += 1
            elif hd < 12 or hd >= 345: bands[0] += 1
            elif hd < 42: bands[1] += 1
            elif hd < 72: bands[2] += 1
            elif hd < 170: bands[3] += 1
            elif hd < 193: bands[4] += 1
            elif hd < 255: bands[5] += 1
            else: bands[6] += 1
    if fg == 0:
        return [0.0] * 8 + [0.0], 0.0
    feats = [b / fg for b in bands] + [gray / fg]
    bw = max(1, maxx - minx + 1)
    bh = max(1, maxy - miny + 1)
    feats.append(fg / (bw * bh))
    return feats, sat_sum / fg


def _concept_match_score(feats, mean_sat, concept):
    p = CONCEPTS[concept]
    d = sum(w * (a - b) ** 2 for w, a, b in zip(WEIGHTS, feats, p))
    score = -d
    if concept == "cloud" and mean_sat < 0.22:
        score += 0.40
    return score


def pick_emoji_tile(challenge):
    """Kembalikan (tile_id, info). Pilih tile paling cocok dgn konsep target."""
    tiles = challenge.get("tiles") or []
    if not tiles:
        return None, "no-tiles"
    concept = _prompt_concept(challenge.get("prompt", ""))
    if not concept or not HAVE_PIL:
        return tiles[0]["id"], "fallback-first"
    ranked = []
    for t in tiles:
        im = _tile_to_image(t)
        if im is None:
            continue
        feats, ms = _tile_features(im)
        ranked.append((_concept_match_score(feats, ms, concept), t["id"]))
    if not ranked:
        return tiles[0]["id"], "no-decodable-tile"
    ranked.sort(reverse=True)
    top = ",".join(f"{i}:{s:.2f}" for s, i in ranked[:3])
    return ranked[0][1], f"{concept} [{top}]"


# ── Core client ───────────────────────────────────────────────────────────────
class PlayNXC:
    def __init__(self, initdata):
        self.initdata = initdata.strip()
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Origin": BASE,
            "Referer": BASE + "/telegram-app",
            "Accept": "application/json, text/plain, */*",
        })

    def api(self, action, **extra):
        data = {"action": action, "initData": self.initdata}
        data.update(extra)
        try:
            r = self.s.post(API_URL, data=data, timeout=25)
            try:
                return r.json()
            except Exception:
                return {"success": False, "message": f"HTTP {r.status_code} (non-JSON)"}
        except Exception as e:
            return {"success": False, "message": f"Koneksi: {e}"}

    # ── Info ──
    def init(self):
        return self.api("init")

    def roll_state(self):
        return self.api("roll_state")

    def weekly_contest(self):
        return self.api("weekly_contest")

    def history(self, period="today"):
        return self.api("history", period=period)

    def invite(self):
        return self.api("invite")

    def ptc_state(self):
        return self.api("ptc_state")

    # ── Referral ──
    def claim_referral(self):
        pend = (self.invite().get("data") or {}).get("pending_gems", 0) or 0
        if pend < 1:
            return 0, "Tidak ada referral pending."
        r = self.api("claim_referral")
        if r.get("success"):
            return int(r["data"].get("gems_claimed", 0) or 0), "OK"
        return 0, r.get("message", "gagal")

    # ── PTC Direct-Link ──
    def claim_directlink(self, ad):
        ad_id = ad["id"]
        r = self.api("start_directlink", directlink_id=ad_id)
        if not r.get("success"):
            return False, r.get("message", "start gagal"), 0
        d = r["data"]
        tok = d["session_token"]
        dur = int(d.get("duration_seconds") or ad.get("duration_seconds") or 7)
        for i in range(dur, 0, -1):
            msg(f"{C_YELLOW}⏳ DL {ad.get('title','?')}#{ad_id}: tunggu {i}s...{C_RESET}")
            time.sleep(1)
        c = self.api("directlink_claim", session_token=tok)
        if c.get("success"):
            rew = int(c["data"].get("reward_gems", 0) or 0)
            return True, "OK", rew
        return False, c.get("message", "claim gagal"), 0

    # ── PTC Site (emoji captcha) ──
    def claim_site_ptc(self, ad):
        ad_id = ad["id"]
        # Sesi BARU utk SELURUH alur iklan ini (start_site_ptc + ptc-view).
        # Server menautkan state view ke PHPSESSID yg memanggil start_site_ptc;
        # pakai sesi utama (self.s) lintas iklan bikin challenge/verify tertukar.
        vs = requests.Session()
        vs.headers.update({
            "User-Agent": UA, "Origin": BASE, "Referer": BASE + "/telegram-app",
            "Accept": "application/json, text/plain, */*",
        })
        try:
            r = vs.post(API_URL, data={"action": "start_site_ptc",
                                       "initData": self.initdata,
                                       "ad_id": ad_id}, timeout=25).json()
        except Exception as e:
            return False, f"start gagal: {e}", 0
        if not r.get("success"):
            return False, r.get("message", "start gagal"), 0
        view_url = r["data"]["view_url"]

        try:
            page = vs.get(view_url, timeout=25).text
        except Exception as e:
            return False, f"gagal muat view: {e}", 0
        m_csrf = re.search(r'CSRF\s*=\s*"([^"]+)"', page)
        m_tok = re.search(r'data-token="([^"]+)"', page)
        if not (m_csrf and m_tok):
            return False, "CSRF/token view tidak ketemu", 0
        csrf, tok = m_csrf.group(1), m_tok.group(1)

        def pv(action, **extra):
            data = {"csrf_token": csrf, "t": tok, "action": action}
            data.update(extra)
            try:
                rr = vs.post(PTCVIEW_URL, data=data, timeout=25,
                             headers={"Referer": view_url})
                return rr.json()
            except Exception as e:
                return {"success": False, "message": f"pv {action}: {e}"}

        # captcha -> verify. Classifier lokal akurat, cukup 3 percobaan.
        # Deteksi rate-limit server ("Too many attempts") agar tidak makin di-spam.
        verified = False
        cap = pv("captcha")
        challenge = (cap.get("data") or {}).get("challenge")
        last_msg = ""
        for _ in range(3):
            if not challenge:
                break
            tid, info = pick_emoji_tile(challenge)
            prompt = challenge.get("prompt", "?")
            msg(f"{C_CYAN}🧩 Site {ad_id}: '{prompt}' -> pilih {tid} ({info}){C_RESET}", is_final=True)
            time.sleep(1.5)                      # pacing ala manusia
            v = pv("verify", tile=tid)
            if v.get("success"):
                verified = True
                break
            last_msg = str(v.get("message") or "")
            low = last_msg.lower()
            if "too many" in low or "wait a moment" in low:
                return False, f"rate-limit: {last_msg}", -1   # -1 = sinyal backoff
            challenge = (v.get("errors") or {}).get("challenge") or (pv("captcha").get("data") or {}).get("challenge")
        if not verified:
            return False, f"captcha gagal ({last_msg})", 0

        st = pv("start")
        if not st.get("success"):
            return False, st.get("message", "start view gagal"), 0
        secs = int(st["data"].get("seconds") or ad.get("duration_seconds") or 7)
        for i in range(secs, 0, -1):
            msg(f"{C_YELLOW}⏳ Site {ad_id}: nonton {i}s...{C_RESET}")
            time.sleep(1)
        cp = pv("complete")
        if cp.get("success"):
            return True, "OK", int(ad.get("reward_gems") or 0)
        return False, cp.get("message", "complete gagal"), 0

    # ── Jalankan semua PTC yang tersedia ──
    def run_ptc(self):
        st = self.ptc_state()
        if not st.get("success"):
            msg(f"{C_RED}✖ ptc_state: {st.get('message')}{C_RESET}", is_final=True)
            return 0, 0
        data = st["data"]
        if not data.get("enabled"):
            msg(f"{C_YELLOW}ℹ PTC sedang tidak aktif.{C_RESET}", is_final=True)
            return 0, 0

        site = data.get("site_ads", []) or []
        dls = data.get("directlinks", []) or []
        total_gems = 0
        n_claim = 0
        cooldowns = []

        for ad in dls:
            if ad.get("status") != "available":
                if ad.get("status") == "cooldown":
                    cooldowns.append(int(ad.get("next_available_at") or 0))
                continue
            ok, why, rew = self.claim_directlink(ad)
            if ok:
                total_gems += rew
                n_claim += 1
                msg(f"{C_GREEN}{C_BOLD}✅ DL '{ad.get('title')}' +{rew} gems{C_RESET}", is_final=True)
            else:
                msg(f"{C_RED}✖ DL '{ad.get('title')}': {why}{C_RESET}", is_final=True)
            time.sleep(1)

        for ad in site:
            if ad.get("status") != "available":
                if ad.get("status") == "cooldown":
                    cooldowns.append(int(ad.get("next_available_at") or 0))
                continue
            ok, why, rew = self.claim_site_ptc(ad)
            if ok:
                total_gems += rew
                n_claim += 1
                msg(f"{C_GREEN}{C_BOLD}✅ SITE '{ad.get('title')}' +{rew} gems{C_RESET}", is_final=True)
            else:
                msg(f"{C_RED}✖ SITE '{ad.get('title')}': {why}{C_RESET}", is_final=True)
                if rew == -1:   # rate-limit: berhenti iklan site, tunggu lebih lama
                    msg(f"{C_YELLOW}⚠ Kena rate-limit captcha, berhenti sejenak.{C_RESET}", is_final=True)
                    cooldowns.append(int(time.time()) + 120)
                    break
            time.sleep(1)

        next_cd = min([c for c in cooldowns if c], default=0)
        return total_gems, next_cd

    # ── Roll (nonton iklan -> roll hadiah acak, kredit via postback server) ──
    # Provider iklan = Monetag: hadiah HANYA dikredit kalau iklan benar-benar
    # ditonton lewat SDK di mini app (postback server-to-server dgn ymid).
    # confirm_watch ditolak server utk jaringan ini, jadi alur bot hybrid:
    # start_watch -> poll; kalau postback tak masuk, tonton manual di app.
    def run_roll(self):
        st = self.roll_state()
        if not st.get("success"):
            return False, st.get("message", "roll_state gagal"), 0
        d = st["data"]
        if not d.get("enabled"):
            return False, "Roll tidak aktif", 0
        if d.get("country_unavailable") or d.get("account_unpaid"):
            return False, "Tidak ada iklan roll utk akun/negara ini", 0
        if int(d.get("daily_remaining") or 0) <= 0:
            return False, "Limit harian habis", 0
        if int(d.get("cooldown_remaining_seconds") or 0) > 0 or d.get("waiting_confirm"):
            return False, "Cooldown / menunggu konfirmasi iklan", 0

        r = self.api("start_watch", purpose="roll")
        if not r.get("success"):
            return False, r.get("message", "start_watch gagal"), 0
        # Poll sampai lock (waiting_confirm) lepas. Hadiah masuk saat postback
        # Monetag mendarat; last_result dipercaya hanya bila lock sesi ini
        # pernah aktif lalu lepas (menghindari hasil basi roll sebelumnya).
        saw_pending = False
        for i in range(30, 0, -1):
            time.sleep(2)
            dd = (self.roll_state().get("data") or {})
            if dd.get("waiting_confirm"):
                saw_pending = True
                continue
            if saw_pending:
                res = dd.get("last_result")
                if res:
                    return True, "OK", int(res.get("reward_amount") or res.get("reward_gems") or 0)
                break
        # Lock lepas tanpa postback = iklan tak pernah benar-benar ditonton.
        return False, "manual", 0

    def wait_roll_result(self, max_wait=180):
        """Poll roll_state menunggu postback masuk (dipakai setelah iklan
        ditonton manual di mini app). Return (ok, gems)."""
        deadline = time.time() + max_wait
        while time.time() < deadline:
            time.sleep(2)
            dd = (self.roll_state().get("data") or {})
            if dd.get("waiting_confirm"):
                continue
            res = dd.get("last_result")
            if res:
                return True, int(res.get("reward_amount") or res.get("reward_gems") or 0)
            return False, 0   # lock lepas tanpa hasil = tak terkonfirmasi
        return False, 0

    # ── Auto claim semua (referral + PTC + Roll) ──
    def auto_claim_once(self, do_roll=True):
        gained = 0
        g, why = self.claim_referral()
        if g:
            msg(f"{C_GREEN}✅ Referral +{g} gems ({why}){C_RESET}", is_final=True)
            gained += g
        else:
            msg(f"{C_GREY}ℹ Referral: {why}{C_RESET}", is_final=True)

        ptc_gems, next_cd = self.run_ptc()
        gained += ptc_gems

        if do_roll:
            ok, why, rew = self.run_roll()
            if ok:
                gained += rew
                msg(f"{C_GREEN}{C_BOLD}🎰 Roll menang +{rew} gems!{C_RESET}", is_final=True)
            elif why == "manual":
                msg(f"{C_YELLOW}🎰 Roll: iklan dibuka — tonton di mini app, bot menunggu...{C_RESET}", is_final=True)
                ok2, g2 = self.wait_roll_result(120)
                if ok2:
                    gained += g2
                    msg(f"{C_GREEN}{C_BOLD}🎰 Roll (manual) menang +{g2} gems!{C_RESET}", is_final=True)
                else:
                    msg(f"{C_GREY}🎰 Roll: postback iklan tidak masuk.{C_RESET}", is_final=True)
            else:
                msg(f"{C_GREY}🎰 Roll: {why}{C_RESET}", is_final=True)
        return gained, next_cd


# ── UI ────────────────────────────────────────────────────────────────────────
def print_banner(balance="?", user="?"):
    balance = str(balance) if balance is not None else "?"
    user = str(user) if user else "?"
    clear_screen()
    print(f"{C_PURPLE}{C_BOLD}╔══════════════════════════════════════════════════════╗")
    print("║              🎮  P L A Y N X C  B O T                ║")
    print("╠══════════════════════════════════════════════════════╣")
    print("║ Login   : Telegram Mini App (initData)              ║")
    print("║ Solver  : Emoji captcha (lokal, tanpa biaya)        ║")
    print(f"║ User    : {user:<39}║")
    print(f"║ Balance : {C_YELLOW}{balance:<39}{C_PURPLE}║")
    print(f"╚══════════════════════════════════════════════════════╝{C_RESET}\n")
    if not HAVE_PIL:
        print(f"{C_RED}[!] PIL tidak terpasang — solver emoji site-PTC akan menebak. "
              f"Jalankan: pip install pillow{C_RESET}\n")


def do_status(client):
    r = client.init()
    if not r.get("success"):
        msg(f"{C_RED}✖ Login gagal: {r.get('message')}{C_RESET}", is_final=True)
        return
    d = r["data"]
    print_banner(f"{d.get('gem_balance')} gems", d.get("telegram_username", "?"))
    print(f"{C_CYAN}── STATUS AKUN ──{C_RESET}")
    print(f"  Gems            : {C_YELLOW}{d.get('gem_balance')}{C_RESET}")
    print(f"  Telegram user   : {'@'+d['telegram_username'] if d.get('telegram_username') else '(tanpa username)'}")
    print(f"  Linked website  : {'@'+d['linked_username'] if d.get('linked_username') else '(belum di-link)'}")
    print(f"  Roll / PTC / Ref: {d.get('roll_enabled')} / {d.get('ptc_enabled')} / {d.get('referral_enabled')}")
    print(f"  Transfer bonus  : +{d.get('transfer_bonus_percent')}%")

    # PTC ringkas
    ptc = client.ptc_state()
    if ptc.get("success"):
        pd = ptc["data"]
        avail = sum(1 for a in pd.get("site_ads", []) if a.get("status") == "available")
        avail += sum(1 for a in pd.get("directlinks", []) if a.get("status") == "available")
        print(f"\n{C_CYAN}── PTC ──{C_RESET}")
        print(f"  Iklan tersedia sekarang: {C_GREEN}{avail}{C_RESET}")
        for a in (pd.get("directlinks", []) + pd.get("site_ads", [])):
            print(f"   - [{a.get('status'):<12}] +{a.get('reward_gems'):>3} gems  {a.get('title')}")

    # Roll ringkas
    rs = client.roll_state()
    if rs.get("success"):
        rd = rs["data"]
        lr = rd.get("last_result") or {}
        print(f"\n{C_CYAN}── ROLL ──{C_RESET}")
        print(f"  Sisa roll hari ini: {C_GREEN}{rd.get('daily_remaining')}/{rd.get('daily_limit')}{C_RESET} "
              f"| Cooldown: {rd.get('cooldown_remaining_seconds')}s "
              f"| Terakhir: {lr.get('label', '-')}")

    # Referral
    inv = client.invite()
    if inv.get("success"):
        idata = inv["data"]
        print(f"\n{C_CYAN}── REFERRAL ──{C_RESET}")
        print(f"  Pending: {idata.get('pending_gems')} gems | Total: {idata.get('total_earned')} | "
              f"Teman: {idata.get('referred_count')}")

    # Contest
    ct = client.weekly_contest()
    if ct.get("success") and ct["data"].get("active"):
        cd = ct["data"]
        print(f"\n{C_CYAN}── CONTEST: {cd.get('title')} ──{C_RESET}")
        print(f"  Pool {cd.get('prizeTotal')} | Sisa {cd.get('secsLeft')}s | Rank kamu: {cd.get('myRank')}")

    input(f"\n{C_YELLOW}Tekan Enter untuk kembali...{C_RESET}")


def input_config_menu():
    print_banner()
    cfg = load_config()
    print(f"{C_CYAN}Cara ambil initData:{C_RESET}")
    print("  Buka @PlayNXC_bot -> Open App, lalu salin initData (lihat catatan script).")
    print("  Format: query_id=...&user=...&auth_date=...&signature=...&hash=...\n")
    existing = cfg.get("initdata", "")
    if existing:
        print(f"{C_GREY}Tersimpan: ...{existing[-40:]}{C_RESET}")
        if input(f"{C_YELLOW}Ganti initData? (y/n) [n]: {C_WHITE}").strip().lower() != "y":
            return
    raw = input(f"{C_YELLOW}Paste initData: {C_WHITE}").strip()
    # dukung paste berupa URL fragment tgWebAppData=...
    if "tgWebAppData=" in raw:
        frag = raw.split("tgWebAppData=", 1)[1].split("&", 1)[0] if "#" not in raw else raw.split("tgWebAppData=", 1)[1]
        from urllib.parse import unquote
        raw = unquote(frag.split("#", 1)[0])
    if raw:
        cfg["initdata"] = raw
        save_config(cfg)
        print(f"{C_GREEN}[✔] initData disimpan.{C_RESET}")
    input(f"\n{C_YELLOW}Tekan Enter untuk kembali...{C_RESET}")


def reset_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        print(f"{C_GREEN}[✔] Config direset.{C_RESET}")
    else:
        print(f"{C_YELLOW}Tidak ada config.{C_RESET}")
    time.sleep(1)


def auto_claim_loop(client):
    loop = 0
    try:
        while True:
            loop += 1
            r = client.init()
            bal = r["data"]["gem_balance"] if r.get("success") else "?"
            usr = r["data"].get("telegram_username", "?") if r.get("success") else "?"
            if not r.get("success") and "nvalid" in str(r.get("message", "")):
                print_banner(bal, usr)
                msg(f"{C_RED}✖ initData ditolak ({r.get('message')}). Ambil initData baru!{C_RESET}", is_final=True)
                input(f"{C_YELLOW}Enter untuk keluar ke menu...{C_RESET}")
                return
            print_banner(f"{bal} gems (loop #{loop})", usr)
            msg(f"{C_CYAN}🔄 Loop #{loop}: menjalankan auto claim...{C_RESET}", is_final=True)

            gained, next_cd = client.auto_claim_once()

            r2 = client.init()
            if r2.get("success"):
                print_banner(r2["data"]["gem_balance"], r2["data"].get("telegram_username", "?"))
            print(f"\n{C_GREEN}{C_BOLD}✔ Loop selesai: +{gained} gems{C_RESET}")

            now = time.time()
            wait = 60
            if next_cd:
                wait = max(15, int(next_cd - now) + 5)
            wait = min(wait, 3600)
            msg(f"{C_PURPLE}😴 Cooldown berikutnya ~{wait}s. Menunggu...{C_RESET}", is_final=True)
            for i in range(wait, 0, -1):
                msg(f"{C_YELLOW}⏳ {i}s...{C_RESET}")
                time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[!] Loop dihentikan.{C_RESET}")
        time.sleep(1)


def roll_loop(client):
    """Loop khusus Roll: 1 roll per iterasi, hormati cooldown 1 menit.
    Iklan Monetag hanya dibayar server kalau benar-benar ditonton — bila
    postback tidak masuk, tonton iklannya di mini app dan bot menunggu."""
    loop = 0
    try:
        while True:
            loop += 1
            r = client.init()
            bal = r["data"]["gem_balance"] if r.get("success") else "?"
            usr = r["data"].get("telegram_username", "?") if r.get("success") else "?"
            print_banner(f"{bal} gems (roll #{loop})", usr)
            msg(f"{C_CYAN}🎰 Roll #{loop}: mulai iklan...{C_RESET}", is_final=True)
            ok, why, rew = client.run_roll()
            if ok:
                msg(f"{C_GREEN}{C_BOLD}✅ Roll menang +{rew} gems!{C_RESET}", is_final=True)
            elif why == "manual":
                msg(f"{C_YELLOW}▶ TONTON IKLANNYA sekarang di mini app PlayNXC (tab Roll).{C_RESET}", is_final=True)
                msg(f"{C_YELLOW}   Bot menunggu hadiah masuk otomatis (maks 3 menit)...{C_RESET}", is_final=True)
                ok2, g2 = client.wait_roll_result(180)
                if ok2:
                    msg(f"{C_GREEN}{C_BOLD}✅ Roll (manual) menang +{g2} gems!{C_RESET}", is_final=True)
                else:
                    msg(f"{C_RED}✖ Roll: iklan tidak terkonfirmasi server.{C_RESET}", is_final=True)
            elif "habis" in why:
                msg(f"{C_RED}✖ Roll: {why} — reset besok 07:00 waktu server.{C_RESET}", is_final=True)
                input(f"{C_YELLOW}Enter untuk kembali ke menu...{C_RESET}")
                return
            else:
                msg(f"{C_YELLOW}🎰 Roll: {why}{C_RESET}", is_final=True)
            msg(f"{C_PURPLE}😴 Jeda 65s sebelum roll berikutnya...{C_RESET}", is_final=True)
            for i in range(65, 0, -1):
                msg(f"{C_YELLOW}⏳ {i}s...{C_RESET}")
                time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[!] Loop roll dihentikan.{C_RESET}")
        time.sleep(1)


def main():
    cfg = load_config()
    initdata = cfg.get("initdata", "")
    while True:
        if not initdata:
            print_banner("belum login", "-")
            print(f" {C_GREEN}1.{C_RESET} Input / Update initData")
            print(f" {C_RED}0.{C_RESET} Exit")
            ch = input(f"\n{C_YELLOW}Pilih [0-1]: {C_WHITE}").strip()
            if ch == "1":
                input_config_menu()
                cfg = load_config()
                initdata = cfg.get("initdata", "")
            elif ch == "0":
                clear_screen(); return
            continue

        client = PlayNXC(initdata)
        r = client.init()
        if not r.get("success"):
            print_banner("GAGAL", "-")
            print(f"{C_RED}✖ initData ditolak: {r.get('message')}{C_RESET}")
            print(f"{C_YELLOW}Ambil initData baru dari @PlayNXC_bot (mini app).{C_RESET}")
        else:
            print_banner(f"{r['data']['gem_balance']} gems", r["data"].get("telegram_username") or "?")

        print(f" {C_GREEN}1.{C_RESET} Status (balance, PTC, referral, contest)")
        print(f" {C_GREEN}2.{C_RESET} 🚀 Auto Claim (Referral + PTC + Roll) [loop]")
        print(f" {C_GREEN}3.{C_RESET} 🎰 Roll saja [loop] (5x/hari, cooldown 1m)")
        print(f" {C_GREEN}4.{C_RESET} Update initData")
        print(f" {C_RED}5.{C_RESET} Reset config")
        print("----------------------------------------------------")
        print(f" {C_YELLOW}0.{C_RESET} Exit")
        ch = input(f"\n{C_YELLOW}Pilih menu [0-5]: {C_WHITE}").strip()

        if ch == "1":
            do_status(client)
        elif ch == "2":
            auto_claim_loop(client)
        elif ch == "3":
            roll_loop(client)
        elif ch == "4":
            input_config_menu()
            cfg = load_config(); initdata = cfg.get("initdata", "")
        elif ch == "5":
            reset_config(); initdata = ""; cfg = {}
        elif ch == "0":
            clear_screen()
            print(f"{C_CYAN}Terima kasih, Kapten Caplung! Sampai jumpa.{C_RESET}\n")
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        sys.exit(0)

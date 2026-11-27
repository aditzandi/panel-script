#!/usr/bin/env python3
"""
◆ EstateCity Smart Bot · Multitasking All-in-One
- Sekali jalan langsung multitasking (Auto Claim Lot + Auto Convert Pool + Auto Faucet 15 menit).
- API Key Waryono sudah tertanam permanen.
- Fitur ganti/input cookie manual langsung saat bot baru dibuka.
"""
import http.client
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid

# ── Konfigurasi Default ───────────────────────────────────────────
BASE = "https://estatecity.net"
WARY_KEY_DEFAULT = "f7457613bf1330fe8086b923de6dbccd"
WARY_IN = "https://api.waryono.my.id/in.php"
WARY_RES = "https://api.waryono.my.id/res.php"
CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estate_smart_config.json")
UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36")

FAUCET_COOLDOWN = 15 * 60 + 5  # 15 menit + 5 detik pengaman

# Warna ANSI
R = "\033[0m"
B = "\033[1m"
ACC = "\033[38;5;51m"
GOLD = "\033[38;5;220m"
OK = "\033[38;5;84m"
BAD = "\033[38;5;203m"
MUTE = "\033[38;5;244m"
TXT = "\033[38;5;255m"

def log(tag, msg, color=TXT):
    t = time.strftime("%H:%M:%S")
    print(f"{MUTE}[{t}]{R} {color}[{tag}]{R} {msg}")

def parse_cookies(raw):
    raw = raw.strip()
    if raw.lower().startswith("cookie:"):
        raw = raw.split(":", 1)[1].strip()
    out = {}
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out

def load_config():
    cfg = {
        "cookies": {},
        "csrf": "",
        "waryono_key": WARY_KEY_DEFAULT,
        "auto_convert_pool": True
    }
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg

def save_config(cfg):
    try:
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log("ERR", f"Gagal simpan config: {e}", BAD)

class EstateClient:
    def __init__(self, cookies, apikey=WARY_KEY_DEFAULT):
        self.cookies = cookies
        self.apikey = apikey
        self.csrf = ""
        self.data = None
        self.synced_at = 0.0

    def _headers(self, is_post=False):
        cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items() if v)
        h = {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "X-Estate-Client": "1",
            "Referer": BASE + "/play",
            "Cookie": cookie_str
        }
        if is_post:
            h.update({
                "Content-Type": "application/json",
                "Origin": BASE,
                "X-CSRF-Token": self.csrf
            })
        return h

    def request(self, method, path, body=None, extra_headers=None):
        url = BASE + path
        headers = self._headers(method == "POST")
        if extra_headers:
            headers.update(extra_headers)
        data = json.dumps(body).encode() if body is not None and method == "POST" else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return json.loads(raw) if raw.strip() else {}

    def session(self):
        d = self.request("GET", "/api/session")
        if not isinstance(d, dict) or "state" not in d:
            raise Exception("Sesi gagal dimuat. Cookie kedaluwarsa atau tidak valid.")
        self.data = d
        self.synced_at = time.time()
        if d.get("csrf"):
            self.csrf = d["csrf"]
        return d

    def act(self, action, inp, extra_headers=None):
        body = {
            "action": action,
            "input": inp,
            "revision": self.data.get("revision"),
            "requestId": str(uuid.uuid4())
        }
        res = self.request("POST", "/api/action", body, extra_headers)
        if "state" in res:
            self.data["state"] = res["state"]
        for k in ("revision", "serverNow", "pool"):
            if k in res:
                self.data[k] = res[k]
        return res

    def solve_turnstile(self, sitekey, challenge):
        payload = {
            "apikey": self.apikey,
            "methods": "turnstile",
            "domain": BASE,
            "sitekey": sitekey,
            "action": "faucet",
            "cdata": challenge,
            "json": 1
        }
        req = urllib.request.Request(WARY_IN, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read().decode())
        if res.get("status") != 1:
            raise Exception(f"Waryono in.php: {res.get('request')}")
        task_id = res["request"]

        # Polling
        deadline = time.time() + 180
        while time.time() < deadline:
            time.sleep(3)
            q_url = f"{WARY_RES}?apikey={urllib.parse.quote(self.apikey)}&action=get&id={task_id}&json=1"
            try:
                with urllib.request.urlopen(urllib.request.Request(q_url, headers={"User-Agent": UA}), timeout=15) as r:
                    res_raw = r.read().decode().strip()
                if res_raw.startswith("OK|"):
                    return res_raw.split("|", 1)[1].strip()
                rd = json.loads(res_raw)
                if rd.get("status") == 1:
                    return str(rd["request"])
                if rd.get("request") == "CAPCHA_NOT_READY":
                    continue
                raise Exception(f"Waryono error: {rd.get('request')}")
            except Exception as e:
                if "CAPCHA_NOT_READY" in str(e):
                    continue
                time.sleep(1)
        raise Exception("Turnstile solver timeout (180s)")

    def claim_faucet(self):
        cap = self.request("GET", "/api/faucet/captcha")
        sitekey = (cap.get("captcha") or {}).get("siteKey", "")
        ch = cap.get("challengeId", "")

        ad = self.request("POST", "/api/faucet/ad-check", {"layout": True, "local": True, "aads": True, "zerads": True})
        ad_token = ad.get("token")
        if not ad_token:
            raise Exception("Gagal mendapatkan ad-check token")

        faucet_token = ""
        if sitekey:
            log("FAUCET", f"Menyelesaikan Turnstile solver Waryono (ID: {ch[:8]}...)...", GOLD)
            faucet_token = self.solve_turnstile(sitekey, ch)
            log("FAUCET", "Turnstile berhasil dipecahkan!", OK)

        headers = {
            "x-estate-ad-check": ad_token,
            "x-estate-faucet-captcha": faucet_token
        }
        res = self.act("faucet", {}, headers)
        return res.get("result", {}).get("message", "Faucet berhasil diklaim")

    def convert_to_pool(self, amount):
        pool = self.data.get("pool") or {}
        if not pool.get("active"):
            return False, "Pool tidak aktif saat ini"
        round_no = pool.get("round")
        res = self.act("pool", {"amount": amount, "round": round_no})
        msg = (res.get("result") or {}).get("message", f"{amount} rent dikonversi ke pool")
        return True, msg

def get_assets(client_data):
    st = client_data.get("state") or {}
    out = []
    for h in st.get("homes") or []:
        pend = int(h.get("pendingRent") or 0)
        out.append({
            "lot": int(h["lot"]),
            "kind": "home",
            "id": h.get("id"),
            "pending": pend,
            "start": float(h.get("rentCycleStartFraction") or 0)
        })
    for k, v in (st.get("landRent") or {}).items():
        out.append({
            "lot": int(k),
            "kind": "land",
            "id": None,
            "pending": int(v.get("pending") or 0),
            "start": float(v.get("startFraction") or 0)
        })
    return sorted(out, key=lambda x: x["lot"])

def prompt_cookie(cfg):
    print(f"\n{GOLD}[LOGIN COOKIE MANUAL]{R}")
    print(f"{MUTE}Tempel (paste) header cookie dari Reqable / Browser DevTools:{R}")
    raw_cookie = input(f"{ACC}Cookie > {R}").strip()
    if not raw_cookie:
        print(f"{BAD}[BATAL]{R} Tidak ada cookie yang dimasukkan.")
        return False
    parsed = parse_cookies(raw_cookie)
    if "__Host-estate_session" not in parsed:
        print(f"{BAD}[ERROR]{R} Cookie tidak valid! Pastikan mengandung __Host-estate_session.")
        return False
    cfg["cookies"] = parsed
    save_config(cfg)
    print(f"{OK}[SUKSES]{R} Cookie berhasil diperbarui dan disimpan!\n")
    return True

def run_smart_bot():
    print(f"\n{B}{ACC}======================================================{R}")
    print(f"{B}{TXT}   ESTATE CITY SMART BOT · MULTITASKING ALL-IN-ONE    {R}")
    print(f"{MUTE}   Auto Claim Lot + Auto Pool + Auto Faucet 15 Menit  {R}")
    print(f"{B}{ACC}======================================================{R}\n")

    cfg = load_config()

    # Cek apakah sudah ada cookie tersimpan
    has_cookie = bool(cfg.get("cookies") and "__Host-estate_session" in cfg["cookies"])
    if has_cookie:
        print(f"{MUTE}Cookie tersimpan ditemukan.{R}")
        print(f"{ACC}[Enter]{R} Langsung Jalankan Bot")
        print(f"{GOLD}[C]{R}     Ganti / Masukkan Cookie Baru Manual")
        pilihan = input(f"{ACC}Pilih (Enter / C): {R}").strip().lower()
        if pilihan == "c":
            if not prompt_cookie(cfg):
                sys.exit(1)
    else:
        if not prompt_cookie(cfg):
            sys.exit(1)

    client = EstateClient(cfg["cookies"], cfg.get("waryono_key", WARY_KEY_DEFAULT))

    log("INIT", "Menghubungkan ke EstateCity...", ACC)
    try:
        sess = client.session()
        cfg["csrf"] = client.csrf
        save_config(cfg)
        user = (sess.get("user") or {}).get("username", "Anonim")
        st = sess.get("state", {})
        log("LOGIN", f"Berhasil masuk sebagai: {B}{user}{R}", OK)
        log("SALDO", f"Rent: {GOLD}{st.get('balance', 0)}{R} | Credits: {ACC}{st.get('credits', 0)}{R} | Gold: {st.get('goldCoins', 0)}", TXT)
    except Exception as e:
        log("AUTH_ERR", f"Gagal login: {e}", BAD)
        print(f"{GOLD}[PERINGATAN]{R} Cookie tidak valid atau sudah kedaluwarsa.")
        if prompt_cookie(cfg):
            client.cookies = cfg["cookies"]
            sess = client.session()
        else:
            sys.exit(1)

    # Inisialisasi waktu Faucet
    last_faucet_ms = (sess.get("state", {}).get("creditClaims", {}) or {}).get("faucet", 0)
    server_now_ms = sess.get("serverNow", time.time() * 1000)
    elapsed_faucet_s = max(0.0, (server_now_ms - last_faucet_ms) / 1000)
    
    if elapsed_faucet_s >= FAUCET_COOLDOWN:
        next_faucet_at = time.time()
    else:
        rem = FAUCET_COOLDOWN - elapsed_faucet_s
        next_faucet_at = time.time() + rem
        log("FAUCET", f"Cooldown faucet masih berjalan: sisa {int(rem)} detik ({int(rem//60)}m {int(rem%60)}s)", MUTE)

    last_sync_at = time.time()
    last_ping_at = time.time()
    next_claim_check_at = 0.0

    print(f"\n{OK}[START]{R} Bot Multitasking Aktif Berjalan Nonstop! Tekan Ctrl+C untuk berhenti.\n")

    while True:
        try:
            now = time.time()

            # 1. Ping aktif tiap 60 detik (agar session tidak putus)
            if now - last_ping_at >= 60:
                try:
                    client.request("POST", "/api/auth/activity", {})
                    last_ping_at = now
                except Exception:
                    pass

            # 2. Sinkron berkala tiap 30 detik
            if now - last_sync_at >= 30:
                try:
                    client.session()
                    last_sync_at = now
                except Exception as e:
                    log("SYNC", f"Sinkron gagal: {e}", BAD)

            # 3. Task: AUTO FAUCET (Setiap 15 Menit)
            if now >= next_faucet_at:
                log("FAUCET", "Waktunya klaim Faucet! Memproses...", ACC)
                try:
                    fmsg = client.claim_faucet()
                    log("FAUCET", f"{OK}Klaim Berhasil: {fmsg}{R}", OK)
                    credits_now = client.data.get("state", {}).get("credits", "?")
                    log("SALDO", f"Total Credits saat ini: {ACC}{credits_now}{R}", OK)
                    next_faucet_at = time.time() + FAUCET_COOLDOWN
                except Exception as e:
                    log("FAUCET", f"Klaim Faucet gagal ({e}). Coba lagi dalam 30 detik.", BAD)
                    next_faucet_at = time.time() + 30

            # 4. Task: AUTO CLAIM LOT (Rumah & Tanah Kosong)
            if now >= next_claim_check_at:
                assets = get_assets(client.data)
                for a in assets:
                    if a["pending"] > 0:
                        try:
                            if a["kind"] == "home":
                                res = client.act("collect", {"lot": a["lot"], "homeId": a["id"], "kind": "regular"})
                            else:
                                res = client.act("land-rent", {"lot": a["lot"]})
                            msg = res.get("result", {}).get("message", "Klaim berhasil")
                            log("CLAIM", f"Lot {a['lot']} ({a['kind']}): {msg}", OK)
                            time.sleep(2)
                        except Exception as e:
                            log("CLAIM", f"Lot {a['lot']} gagal diklaim: {e}", BAD)
                
                # 5. Task: AUTO CONVERT RENT KE POOL (Jika ada saldo Rent)
                bal = int((client.data.get("state") or {}).get("balance") or 0)
                if bal > 0 and cfg.get("auto_convert_pool", True):
                    log("POOL", f"Mendeteksi saldo Rent: {bal}. Mengonversi ke Pool ronde aktif...", GOLD)
                    try:
                        ok_conv, cmsg = client.convert_to_pool(bal)
                        if ok_conv:
                            log("POOL", f"{OK}Sukses Convert ke Pool: {cmsg}{R}", OK)
                        else:
                            log("POOL", f"Info: {cmsg}", MUTE)
                    except Exception as e:
                        log("POOL", f"Gagal convert ke pool: {e}", BAD)

                next_claim_check_at = time.time() + 15

            time.sleep(2)

        except KeyboardInterrupt:
            print(f"\n{GOLD}[INFO]{R} Bot dihentikan oleh pengguna. Sampai jumpa!")
            break
        except Exception as e:
            log("LOOP_ERR", f"Terjadi kesalahan di loop: {e}", BAD)
            time.sleep(5)

if __name__ == "__main__":
    run_smart_bot()

import os
import sys
import json
import time
import base64
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

API_BASE = "https://gram-edge-farm.onrender.com/api"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "active_account.json")

def log(tag, msg, color=Fore.WHITE):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{tag}] {color}{msg}{Style.RESET_ALL}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(account):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(account, f, indent=2)

def parse_user_from_init_data(init_data: str):
    parsed = urllib.parse.parse_qs(init_data)
    user_str = parsed.get("user", [""])[0]
    if user_str:
        try:
            return json.loads(user_str)
        except Exception:
            pass
    return {}

class AdsgramEngine:
    """Mesin emulator Adsgram resmi untuk memicu event tracking S2S."""
    def __init__(self, init_data: str, telegram_id: int):
        self.init_data = init_data
        self.telegram_id = str(telegram_id)
        parsed = urllib.parse.parse_qs(init_data)
        
        items = []
        for k, v_list in parsed.items():
            if k not in ['hash', 'signature']:
                items.append(f"{k}={v_list[0]}")
        items.sort()
        b64 = base64.b64encode("\n".join(items).encode('utf-8')).decode('utf-8')
        self.data_check_string = b64.replace('+', '-').replace('/', '_').rstrip('=')
        self.signature = parsed.get('signature', [''])[0]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.6834.163 Mobile Safari/537.36',
            'Origin': 'https://ton-edge-play.vercel.app',
            'Referer': 'https://ton-edge-play.vercel.app/'
        }

    def simulate_ad(self, block_id: str, is_task=False):
        try:
            params = {
                'envType': 'telegram',
                'blockId': block_id,
                'platform': 'android',
                'language': 'id',
                'top_domain': 'ton-edge-play.vercel.app',
                'signature': self.signature,
                'data_check_string': self.data_check_string,
                'sdk_version': '2.2.5',
                'tg_id': self.telegram_id,
                'tg_platform': 'android',
                'tma_version': '8.0'
            }
            url = f"https://api.adsgram.ai/adv?{urllib.parse.urlencode(params)}"
            r = requests.get(url, headers=self.headers, timeout=15)
            d = r.json()
            banners = d.get('banners', [])
            if not banners:
                return False

            trackings = banners[0].get('banner', {}).get('trackings', [])
            track_map = {t['name']: t['value'] for t in trackings}

            if 'render' in track_map:
                requests.get(track_map['render'], headers=self.headers, timeout=10)
            if 'show' in track_map:
                requests.get(track_map['show'], headers=self.headers, timeout=10)

            if is_task:
                time.sleep(1)
                if 'click' in track_map:
                    requests.get(track_map['click'], headers=self.headers, timeout=10)
                time.sleep(6)
            else:
                time.sleep(15)

            if 'reward' in track_map:
                requests.get(track_map['reward'], headers=self.headers, timeout=10)
            time.sleep(1.5)
            return True
        except Exception:
            return False

class GramEdgeBot:
    def __init__(self, init_data: str):
        self.init_data = init_data.strip()
        user_info = parse_user_from_init_data(self.init_data)
        self.telegram_id = user_info.get("id", 8596999800)
        self.username = user_info.get("username", "") or user_info.get("first_name", "User")
        self.first_name = user_info.get("first_name", self.username)
        self.balance = 0
        
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Sec-Ch-Ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "Origin": "https://ton-edge-play.vercel.app",
            "Referer": "https://ton-edge-play.vercel.app/",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        self.ads_engine = AdsgramEngine(self.init_data, self.telegram_id)
        self.running = True

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

            if not token:
                log("CAPTCHA", "Token challenge tidak ditemukan.", Fore.RED)
                return False

            part = token.split(".")[0]
            decoded = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)).decode("utf-8")
            token_info = json.loads(decoded)
            answer = token_info.get("e")

            log("CAPTCHA", f"Pertanyaan: '{question}' -> Jawaban otomatis: {answer}", Fore.CYAN)
            time.sleep(2.5)

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
                "username": self.username,
                "firstName": self.first_name,
                "referCode": "",
                "initData": self.init_data,
                "fp": f"fp_{self.telegram_id}"
            }
            r = requests.post(f"{API_BASE}/user", json=body, headers=self.headers, verify=False, timeout=30)
            d = r.json()
            if d.get("success"):
                u = d.get("user", {})
                self.balance = u.get("egBalance", 0)
                log("USER", f"Login Berhasil! User: @{u.get('username', self.username)} | Saldo: {self.balance} MM$", Fore.GREEN)
                return u
            else:
                log("USER", f"Gagal load user: {d.get('error')}", Fore.RED)
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
                self.balance = d.get("balance", self.balance)
                log("LOGIN", f"✓ Bonus Login: +{d.get('reward', 0)} MM$ | Saldo: {self.balance} MM$", Fore.GREEN)
            elif "Already claimed" in str(d.get("error", "")):
                log("LOGIN", "Bonus login hari ini sudah diambil.", Fore.YELLOW)
        except Exception as e:
            log("LOGIN", f"Error claim login: {e}", Fore.RED)

    def check_and_claim_farm(self):
        """Memeriksa farm, memanen jika sudah siap, dan mengembalikan sisa detik panen terdekat."""
        try:
            r = requests.get(
                f"{API_BASE}/farm?telegramId={self.telegram_id}&initData={urllib.parse.quote(self.init_data)}",
                headers=self.headers, verify=False, timeout=25
            )
            d = r.json()
            if not d.get("success"):
                return None

            farm_data = d.get("farm", {})
            now_ms = farm_data.get("now", int(time.time() * 1000))
            farms = farm_data.get("farms", [])
            min_seconds_left = None

            for f in farms:
                fid = f.get("id")
                name = f.get("name", f"Farm #{fid+1}")
                unlocked = f.get("unlocked", False)
                ready_at = f.get("readyAt", 0)

                if unlocked:
                    if now_ms >= ready_at:
                        log("FARM", f"PRIORITAS: Farm {fid+1} ({name}) SIAP PANEN! Memulai panen...", Fore.CYAN)
                        self._do_farm_claim(fid, name)
                    else:
                        s_left = max(0, int((ready_at - now_ms) / 1000))
                        if min_seconds_left is None or s_left < min_seconds_left:
                            min_seconds_left = s_left

            return min_seconds_left
        except Exception as e:
            log("FARM", f"Error check farm: {e}", Fore.RED)
            return None

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
                log("FARM", f"[{name}] Nonton iklan farm ({net})... (15s)", Fore.MAGENTA)
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
                        self.balance = d2.get("balance", self.balance + d2.get("reward", 0))
                        log("FARM", f"✓ [{name}] Panen berhasil! +{d2.get('reward')} MM$ | Saldo: {self.balance} MM$", Fore.GREEN)
                        return
                    elif d2.get("error") == "s2s_pending":
                        time.sleep(3)
                    else:
                        break
            except Exception as e:
                log("FARM", f"Error farm claim {slot_id}: {e}", Fore.RED)

    def watch_daily_ads(self):
        """Klaim SEMUA iklan harian (GigaPub, Adsgram Task, Adsgram Video) hingga tuntas."""
        try:
            r = requests.get(
                f"{API_BASE}/ads?telegramId={self.telegram_id}&initData={urllib.parse.quote(self.init_data)}",
                headers=self.headers, verify=False, timeout=25
            )
            d = r.json()
            if not d.get("success"):
                return

            networks = d.get("networks", [])

            for net_info in networks:
                net_key = net_info.get("network")
                watched = net_info.get("watched", 0)
                limit = net_info.get("limit", 5)

                if watched >= limit:
                    log("ADS", f"[{net_key}] Sudah selesai hari ini ({watched}/{limit})", Fore.YELLOW)
                    continue

                log("ADS", f"=== Mulai klaim [{net_key}] | Progress: {watched}/{limit} ===", Fore.CYAN)

                while watched < limit and self.running:
                    self.check_and_claim_farm()

                    try:
                        log("ADS", f"Menonton Iklan [{net_key}] ({watched+1}/{limit})...", Fore.MAGENTA)

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
                                break

                        if ds.get("error") == "ad_cooldown":
                            log("ADS", f"[{net_key}] Cooldown antar-iklan, tunggu 10s...", Fore.YELLOW)
                            time.sleep(10)
                            continue

                        if not ds.get("success"):
                            log("ADS", f"[{net_key}] Start error: {ds.get('error')} — skip.", Fore.RED)
                            break

                        st = ds.get("startTime")
                        sig = ds.get("signature")

                        # Eksekusi AdsEngine sesuai tipe iklan
                        view_ms = 15200
                        if net_key == "daily_adsgram_task":
                            self.ads_engine.simulate_ad("56002", is_task=True)
                            view_ms = 0
                        elif net_key == "daily_adsgram":
                            self.ads_engine.simulate_ad("37275", is_task=False)
                        else:
                            time.sleep(15)

                        claimed = False
                        for attempt in range(1, 10):
                            r_claim = requests.post(f"{API_BASE}/ads", json={
                                "telegramId": self.telegram_id,
                                "initData": self.init_data,
                                "network": net_key,
                                "action": "claim",
                                "startTime": st,
                                "signature": sig,
                                "viewMs": view_ms
                            }, headers=self.headers, verify=False, timeout=25)
                            dc = r_claim.json()

                            if dc.get("error") == "human_check_required":
                                if self.solve_captcha():
                                    time.sleep(2)
                                    continue
                                else:
                                    break

                            if dc.get("error") == "s2s_pending":
                                time.sleep(2.5)
                                continue

                            if dc.get("success"):
                                watched = dc.get("watched", watched + 1)
                                reward = dc.get("reward", 0)
                                self.balance += reward
                                log("ADS", f"✓ [{net_key}] +{reward} MM$ ({watched}/{limit}) | Saldo: {self.balance} MM$", Fore.GREEN)
                                claimed = True
                                break
                            else:
                                log("ADS", f"[{net_key}] Claim error: {dc.get('error')} — skip.", Fore.RED)
                                break

                        if not claimed:
                            break

                        time.sleep(3)

                    except Exception as ex:
                        log("ADS", f"[{net_key}] Exception: {ex}", Fore.RED)
                        break

        except Exception as e:
            log("ADS", f"Error daily ads: {e}", Fore.RED)

    def run_smart_mode(self):
        """Mode Smart: Selalu memantau & memprioritaskan panen farm, sambil menghabiskan semua daily ads."""
        print(f"\n{Fore.GREEN}═══ GRAM EDGE FARM — SMART AUTO BOT AKTIF ═══{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}User: {self.username} (ID: {self.telegram_id})")
        print(f"Fitur: Auto Panen Farm + Auto Bypass Adsgram S2S + GigaPub + Captcha Solver")
        print(f"Tekan Ctrl+C kapan saja untuk berhenti.{Style.RESET_ALL}\n")

        self.register_or_load()
        self.claim_daily_login()

        while self.running:
            try:
                sisa_farm = self.check_and_claim_farm()
                if sisa_farm is not None:
                    jam = sisa_farm // 3600
                    menit = (sisa_farm % 3600) // 60
                    detik = sisa_farm % 60
                    log("FARM", f"Status Farm: Panen berikutnya dalam {jam}j {menit}m {detik}d", Fore.YELLOW)

                self.watch_daily_ads()
                self.register_or_load()

                sisa_farm = self.check_and_claim_farm()
                wait_sec = 30
                if sisa_farm is not None and sisa_farm > 0:
                    wait_sec = min(sisa_farm, 30)
                    jam = sisa_farm // 3600
                    menit = (sisa_farm % 3600) // 60
                    print(f"[*] Standby memantau panen farm ({jam}j {menit}m lagi)...", end="\r")

                for _ in range(wait_sec):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                log("LOOP", f"Error di loop: {e}", Fore.RED)
                time.sleep(5)

def manual_login():
    print(f"\n{Fore.CYAN}═══ INPUT INIT DATA MANUAL ═══{Style.RESET_ALL}")
    print("Salin query string initData dari DevTools Telegram Web (TonEdge Mini App).")
    init_data = input("\nMasukkan initData: ").strip()
    if not init_data:
        print(f"{Fore.RED}[!] Input tidak boleh kosong.{Style.RESET_ALL}")
        return None
    account = {"init_data": init_data}
    save_config(account)
    print(f"{Fore.GREEN}✓ initData berhasil disimpan ke active_account.json!{Style.RESET_ALL}")
    return account

def main():
    while True:
        cfg = load_config()
        has_init = bool(cfg.get("init_data"))
        user_info = parse_user_from_init_data(cfg.get("init_data", ""))
        user_label = f"@{user_info.get('username')}" if user_info.get('username') else (user_info.get('first_name') or "Belum Ada")
        status_str = f"{user_label} (Siap)" if has_init else "Belum Input"

        print(f"""
{Fore.GREEN}╔════════════════════════════════════════════════════════════╗
║             GRAM EDGE FARM — SMART AUTO BOT                ║
║   Smart Farm Priority • Auto Captcha Solver • Daily Ads    ║
╠════════════════════════════════════════════════════════════╣
║  Akun Aktif : {status_str.ljust(44)}║
╠════════════════════════════════════════════════════════════╣
║  [1] Login / Ganti Init Data Manual                        ║
║  [2] Start Bot                                             ║
║  [0] Keluar                                                ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}""")
        pilih = input("Pilih menu (0-2): ").strip()
        if pilih == "1":
            manual_login()
            input("\nTekan Enter untuk kembali ke menu...")
        elif pilih == "2":
            if not has_init:
                print(f"{Fore.YELLOW}initData belum diinput. Silakan pilih Menu 1 terlebih dahulu.{Style.RESET_ALL}")
                manual_login()
                cfg = load_config()
            if cfg.get("init_data"):
                bot = GramEdgeBot(cfg.get("init_data"))
                try:
                    bot.run_smart_mode()
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}[SHUTDOWN] Bot dihentikan pengguna.{Style.RESET_ALL}")
            input("\nTekan Enter untuk kembali...")
        elif pilih == "0":
            print("Sampai jumpa!")
            break

if __name__ == "__main__":
    main()

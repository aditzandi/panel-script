import os
import sys
import json
import time
from datetime import datetime
import requests

DATA_FILE = "config.json"
BASE_URL = "https://farm.treasuremine.fun/api"

# Jeda waktu aman untuk verifikasi iklan (minimal server 8-10 detik)
AD_WATCH_DELAY = 12

DAILY_AD_NETWORKS = [
    {"id": "adsgramDaily",   "label": "Adsgram Daily",   "limit": 5,  "counterField": "adsgramDailyCountToday",   "reward": 15},
    {"id": "adsgramSpecial", "label": "Special Ads",     "limit": 10, "counterField": "adsgramSpecialCountToday", "reward": 20},
    {"id": "giga",           "label": "GigaPub",         "limit": 10, "counterField": "gigaCountToday",           "reward": 10}
]

def load_config():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def manual_login():
    print("\n--- [1] INPUT INIT DATA MANUAL ---")
    print("Salin query string initData dari Telegram Web.")
    init_data = input("\nMasukkan initData: ").strip()
    
    if not init_data:
        print("[!] Input tidak boleh kosong.")
        return

    config = load_config()
    config["init_data"] = init_data
    save_config(config)
    print("[+] initData berhasil disimpan ke config.json!")

class RedtubeBot:
    def __init__(self, init_data):
        self.init_data = init_data
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://farm.treasuremine.fun",
            "Referer": "https://farm.treasuremine.fun/"
        })

    def post(self, endpoint, payload=None):
        if payload is None:
            payload = {}
        payload["initData"] = self.init_data
        url = f"{BASE_URL}/{endpoint}"
        try:
            res = self.session.post(url, json=payload, timeout=25)
            return res.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def init_user(self):
        res = self.post("user", {"action": "init"})
        if res.get("ok"):
            u = res.get("user", {})
            name = u.get("firstName", "") or u.get("username", "User")
            balance = u.get("rdcBalance", 0)
            streak = u.get("streakCount", 0)
            claims_today = u.get("gameClaimsToday", 0)
            print(f"[+] User: {name} | Saldo: {balance} RDC | Streak: {streak} | Game Claims: {claims_today}/20")
            return res
        else:
            print(f"[-] Gagal init user: {res.get('error')}")
            return None

    def check_and_claim_farm(self):
        """Memeriksa farm dan mengklaim jika sudah siap. Mengembalikan sisa waktu panen terdekat (dalam detik)."""
        farm_state = self.post("earn", {"action": "farmState"})
        if not farm_state.get("ok"):
            return None

        farms = farm_state.get("farms", [])
        now_ts = farm_state.get("now", int(time.time() * 1000))
        min_seconds_left = None

        for f in farms:
            f_id = f.get("id")
            name = f.get("name", f"Farm #{f_id}")
            unlocked = f.get("unlocked", False)
            next_claim = f.get("nextClaimAt")

            if not unlocked:
                continue

            if next_claim is None or now_ts >= next_claim:
                print(f"\n[!] PRIORITAS: Farm [{name}] SIAP PANEN! Langsung memanen...")
                st = self.post("earn", {"action": "farmStart", "farmId": f_id})
                if st.get("ok"):
                    time.sleep(AD_WATCH_DELAY)
                    claim_body = {
                        "action": "farmClaim",
                        "farmId": f_id,
                        "startTime": st.get("startTime"),
                        "signature": st.get("signature")
                    }
                    res = self.post("earn", claim_body)
                    if res.get("ok"):
                        print(f"[+] SUKSES PANEN Farm [{name}]! (+{res.get('reward')} RDC)")
                    else:
                        print(f"[-] Gagal panen: {res.get('error')}")
                else:
                    print(f"[-] Farm start error: {st.get('error')}")
            else:
                sisa_sec = max(0, int((next_claim - now_ts) / 1000))
                if min_seconds_left is None or sisa_sec < min_seconds_left:
                    min_seconds_left = sisa_sec

        return min_seconds_left

    def check_and_spin(self):
        """Cek dan klaim Lucky Spin jika cooldown 2 jam sudah selesai."""
        st = self.post("earn", {"action": "spinStart"})
        if st.get("ok"):
            print(f"\n[*] Lucky Spin tersedia! Memutar spin...")
            time.sleep(AD_WATCH_DELAY)
            res = self.post("earn", {
                "action": "spin",
                "startTime": st.get("startTime"),
                "signature": st.get("signature")
            })
            if res.get("ok"):
                print(f"[+] Spin Berhasil! Reward: {res.get('reward')} RDC")

    def auto_daily_ads(self):
        """Klaim sponsored task dan daily ad networks."""
        # 1. SPONSORED ADS
        sp_state = self.post("earn", {"action": "sponsoredState"})
        if sp_state.get("ok") and not sp_state.get("lockedUntil"):
            count = sp_state.get("count", 0)
            limit = sp_state.get("limit", 10)
            sisa = max(0, limit - count)
            if sisa > 0:
                print(f"\n[*] Mengerjakan {sisa}/{limit} Sponsored Ads...")
                for idx in range(sisa):
                    self.check_and_claim_farm()
                    
                    st = self.post("earn", {"action": "sponsoredStart"})
                    if not st.get("ok"):
                        break
                    time.sleep(AD_WATCH_DELAY)
                    claim = self.post("earn", {
                        "action": "sponsoredClaim",
                        "startTime": st.get("startTime"),
                        "signature": st.get("signature")
                    })
                    if claim.get("ok"):
                        print(f"    [+] Claim Sponsored Ad (+{claim.get('reward')} RDC) - Total: {claim.get('count')}/{limit}")
                    else:
                        break

        # 2. DAILY ADS NETWORK
        u_res = self.post("user", {"action": "init"})
        user = u_res.get("user", {}) if u_res.get("ok") else {}
        cycle_state = self.post("earn", {"action": "adsCycleState"})

        if not cycle_state.get("lockedUntil"):
            for net in DAILY_AD_NETWORKS:
                done = user.get(net["counterField"], 0)
                sisa = max(0, net["limit"] - done)
                if sisa <= 0:
                    continue

                print(f"[*] Mengerjakan Ads [{net['label']}] ({sisa} tersisa)...")
                for i in range(sisa):
                    self.check_and_claim_farm()

                    st = self.post("earn", {"action": "adStart", "network": net["id"]})
                    if not st.get("ok"):
                        break
                    time.sleep(AD_WATCH_DELAY)
                    claim = self.post("earn", {
                        "action": "claimAdReward",
                        "network": net["id"],
                        "startTime": st.get("startTime"),
                        "signature": st.get("signature"),
                        "viewMs": AD_WATCH_DELAY * 1000
                    })
                    if claim.get("ok"):
                        print(f"    [+] Sukses Claim {net['label']} (+{claim.get('reward')} RDC) - {claim.get('countToday')}/{claim.get('dailyLimit')}")
                    else:
                        break

    def play_one_game_round(self):
        """Memainkan 1 sesi game (125 detik)."""
        st = self.post("earn", {"action": "gameStart"})
        if not st.get("ok"):
            return False, st.get("error")

        start_time = st.get("startTime")
        signature = st.get("signature")

        print("\n[*] Game ronde sedang berjalan (125 detik server-side)...")
        for s in range(125, 0, -5):
            print(f"    Sisa waktu gameplay: {s}s ...", end="\r")
            time.sleep(5)

        print("\n[*] Gameplay selesai! Mengambil reward game...")
        ad_tok = self.post("earn", {"action": "gameAdStart"})
        if not ad_tok.get("ok"):
            return False, ad_tok.get("error")

        time.sleep(AD_WATCH_DELAY)
        claim_res = self.post("earn", {
            "action": "gameClaim",
            "startTime": start_time,
            "signature": signature,
            "adStartTime": ad_tok.get("startTime"),
            "adSignature": ad_tok.get("signature")
        })

        if claim_res.get("ok"):
            print(f"[+] Sukses Klaim Game Reward: +{claim_res.get('reward')} RDC!")
            return True, None
        else:
            return False, claim_res.get("error")

    def run_smart_mode(self):
        """Mode Pintar: Terus memantau farm, panen saat siap, sambil mengisi waktu dengan Daily Ads & Game."""
        print("\n" + "="*50)
        print("     SMART BOT AKTIF (FARM PRIORITY + ADS & GAME)")
        print("="*50)
        
        try:
            while True:
                # 1. Prioritas Utama: Panen Farm
                sisa_farm = self.check_and_claim_farm()
                if sisa_farm is not None:
                    jam = sisa_farm // 3600
                    menit = (sisa_farm % 3600) // 60
                    detik = sisa_farm % 60
                    print(f"[*] Status Panen: Sisa waktu panen berikutnya {jam}j {menit}m {detik}d")

                # 2. Cek Lucky Spin (jika sudah 2 jam)
                self.check_and_spin()

                # 3. Kerjakan Daily Ads jika ada yang belum selesai
                self.auto_daily_ads()

                # 4. Cek apakah limit game hari ini masih ada
                u_res = self.post("user", {"action": "init"})
                user = u_res.get("user", {}) if u_res.get("ok") else {}
                game_claims = user.get("gameClaimsToday", 0)

                if game_claims < 20:
                    print(f"\n[*] Memainkan game untuk mengisi waktu ({game_claims}/20 claims hari ini)...")
                    ok, err = self.play_one_game_round()
                    if not ok and err and "daily_max" in str(err):
                        print("[!] Limit harian game tercapai.")
                else:
                    # Jika ads dan game sudah selesai, bot standby memantau sisa panen
                    sisa_farm = self.check_and_claim_farm()
                    if sisa_farm is not None and sisa_farm > 0:
                        wait_sec = min(sisa_farm, 30)
                        jam = sisa_farm // 3600
                        menit = (sisa_farm % 3600) // 60
                        print(f"[*] Semua tugas harian selesai. Siaga memantau panen ({jam}j {menit}m lagi)...", end="\r")
                        time.sleep(wait_sec)
                    else:
                        time.sleep(10)

        except KeyboardInterrupt:
            print("\n[!] Smart Bot dihentikan pengguna.")

def main_menu():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("="*50)
        print("     REDTUBE SMART BOT - FARM PRIORITY & ADS")
        print("="*50)
        print("1. Login / Ganti Init Data Manual")
        print("2. Start Bot")
        print("3. Keluar")
        print("="*50)
        pilihan = input("Pilih menu (1/2/3): ").strip()

        if pilihan == "1":
            manual_login()
            input("\nTekan Enter untuk kembali ke menu...")
        elif pilihan == "2":
            config = load_config()
            init_data = config.get("init_data")
            if not init_data:
                print("\n[!] initData belum ada! Silakan login di menu 1.")
                input("Tekan Enter...")
                continue
            bot = RedtubeBot(init_data)
            bot.init_user()
            bot.run_smart_mode()
            input("\nTekan Enter untuk kembali...")
        elif pilihan == "3":
            print("Sampai jumpa!")
            sys.exit(0)
        else:
            print("Pilihan tidak valid.")
            time.sleep(1)

if __name__ == "__main__":
    main_menu()

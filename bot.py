#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HERO RPG (Knight Realm: Chest Hero) - Termux Standalone Single File
Semua modul (Config, AdsEngine, Bot) digabung menjadi 1 file utuh.
Bisa dijalankan langsung di Termux HP tanpa repot import file lain.
"""

import os
import sys
import time
import json
import random
import re
import logging
import urllib.parse
import requests

# ==============================================================================
# 1. KONFIGURASI BOT
# ==============================================================================
USER_AGENT = "Mozilla/5.0 (Linux; Android 14; SM-S918B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.230 Mobile Safari/537.36 Telegram-Android/10.9.1"

# File sesi lokal untuk menyimpan init_data antar-restart
SESSION_FILE = "session.json"

def load_saved_init_data():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("init_data", "").strip()
        except Exception:
            pass
    return ""

def save_init_data_to_file(new_init):
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump({"init_data": new_init.strip()}, f, indent=2)
        return True
    except Exception as e:
        log.error(f"Gagal menyimpan session.json: {e}")
        return False

INIT_DATA = load_saved_init_data()

CONFIG = {
    "AUTO_OPEN_CHEST": True,
    "CHEST_TIERS_TO_OPEN": ["t4", "t3", "t2", "t1"],
    "AUTO_EQUIP_BETTER": True,
    "AUTO_SELL_WORSE": True,
    "AUTO_HUNT": True,
    "HUNT_KILLS_PER_BATCH": 1,
    "HUNT_ROUNDS": 100,
    "HUNT_DELAY": 0.65,
    "AUTO_FORGE_ANVIL": True,
    "AUTO_UPGRADE_STAT": True,
    "MIN_COINS_RESERVE": 1000,
    "MAX_STAT_COST": 200000,
    "AUTO_ARENA": True,
    "ARENA_TARGET_EASIEST": True,
    "AUTO_BOSS_ATTACK": True,
    "AUTO_TON_MAP": True,
    "AUTO_CLAIM_OFFLINE": True,
    "AUTO_CLAIM_DAILY": True,
    "AUTO_CLAIM_QUESTS": True,
    "AUTO_CLAIM_TUTORIAL": True,
    "AUTO_CLAIM_CLAN": True,
    "AUTO_CLAIM_BOSS": True,
    "ACTION_DELAY": 0.8,
    "LOOP_DELAY": 10
}

# ==============================================================================
# LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("HeroRPG-Termux")


# ==============================================================================
# 2. ADS ENGINE (Simulasi Nonton Iklan Adsgram Tanpa Browser)
# ==============================================================================
class AdsEngine:
    def __init__(self, init_data=None):
        self.init_data = init_data if init_data else INIT_DATA
        self.adv_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-S918B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.230 Mobile Safari/537.36 Telegram-Android/10.9.1',
            'Referer': 'https://makeyoutask.com/',
            'Origin': 'https://makeyoutask.com'
        }

    def _build_adsgram_url(self):
        import base64
        parsed = urllib.parse.parse_qs(self.init_data)
        
        user_str = parsed.get('user', ['{}'])[0]
        tg_id = ""
        try:
            tg_id = str(json.loads(user_str).get('id', ''))
        except Exception:
            pass

        signature = parsed.get('signature', [''])[0]
        auth_date = parsed.get('auth_date', [''])[0]
        query_id = parsed.get('query_id', [''])[0]
        
        # Format Adsgram data_check_string: auth_date, query_id, user di-join newline lalu base64
        check_str = f"auth_date={auth_date}\nquery_id={query_id}\nuser={user_str}"
        data_check = base64.b64encode(check_str.encode('utf-8')).decode('utf-8')
        
        req_id = ''.join([str(random.randint(0, 9)) for _ in range(29)])
        
        params = {
            'envType': 'telegram',
            'blockId': '58363',
            'platform': 'Win32',
            'language': 'id',
            'top_domain': 'makeyoutask.com',
            'signature': signature,
            'data_check_string': data_check,
            'sdk_version': '2.2.5',
            'tg_id': tg_id,
            'tg_platform': 'android',
            'tma_version': '8.0',
            'request_id': req_id
        }
        return 'https://api.adsgram.ai/adv?' + urllib.parse.urlencode(params)

    def claim_one_ad(self, session, csrf_hash, csrf_name="csrf_token_name", kind="main"):
        try:
            r_start = session.post('https://makeyoutask.com/chest/ad_start', data={
                csrf_name: csrf_hash,
                'init_data': self.init_data,
                'kind': kind
            }, timeout=10)
            d_start = r_start.json()
            if d_start.get('csrf_hash'):
                csrf_hash = d_start['csrf_hash']

            adv_url = self._build_adsgram_url()
            r_adv = requests.get(adv_url, headers=self.adv_headers, timeout=10)
            if r_adv.status_code != 200:
                log.warning(f"Gagal mengambil banner Adsgram: HTTP {r_adv.status_code}")
                return False, csrf_hash

            banners = r_adv.json().get('banners', [])
            if not banners:
                log.warning("Tidak ada banner Adsgram yang dikembalikan.")
                return False, csrf_hash

            trackings = banners[0].get('banner', {}).get('trackings', [])
            track_map = {t['name']: t['value'] for t in trackings}

            if 'render' in track_map:
                requests.get(track_map['render'], headers=self.adv_headers, timeout=10)
            
            time.sleep(random.uniform(0.3, 0.7))

            if 'show' in track_map:
                requests.get(track_map['show'], headers=self.adv_headers, timeout=10)

            watch_duration = random.uniform(12.5, 14.2)
            time.sleep(watch_duration)

            if 'reward' in track_map:
                requests.get(track_map['reward'], headers=self.adv_headers, timeout=10)

            time.sleep(random.uniform(1.8, 2.6))

            r_rew = session.post('https://makeyoutask.com/chest/ad_reward', data={
                csrf_name: csrf_hash,
                'init_data': self.init_data,
                'kind': kind
            }, timeout=10)
            d_rew = r_rew.json()
            if d_rew.get('csrf_hash'):
                csrf_hash = d_rew['csrf_hash']

            if d_rew.get('status'):
                log.info(f"✅ Iklan ({kind}) BERHASIL DIKLAIM! Status: {d_rew.get('message', 'OK')} | TON Ads: {d_rew.get('m_count', 0)}/10")
                return True, csrf_hash
            else:
                log.warning(f"Klaim ad_reward ditolak: {d_rew.get('message')}")
                return False, csrf_hash
        except Exception as e:
            log.error(f"Error claim_one_ad: {e}")
            return False, csrf_hash


# ==============================================================================
# 3. HERO RPG BOT ENGINE
# ==============================================================================
class HeroRPGBot:
    def __init__(self, init_data=None):
        self.base_url = "https://makeyoutask.com"
        self.init_data = init_data if init_data else INIT_DATA
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/chest/",
            "X-Requested-With": "XMLHttpRequest"
        })
        self.csrf_name = "csrf_token_name"
        self.csrf_hash = ""
        self.player_data = {}
        self.equipped_data = {}
        self.ton_data = {"total": 0.0, "balance": 0.0, "earned": 0.0, "min": 0.2}
        self.is_running = False
        self.telegram_user = self._parse_telegram_user()
        self.ads_engine = AdsEngine(self.init_data)

    def set_init_data(self, new_init_data):
        self.init_data = new_init_data.strip()
        self.telegram_user = self._parse_telegram_user()
        self.ads_engine = AdsEngine(self.init_data)

    def _parse_telegram_user(self):
        parsed = urllib.parse.parse_qs(self.init_data)
        user_json_str = parsed.get("user", ["{}"])[0]
        try:
            return json.loads(user_json_str)
        except Exception:
            return {}

    def _update_csrf(self, res_data):
        if isinstance(res_data, dict):
            if res_data.get("csrf_hash"):
                self.csrf_hash = res_data["csrf_hash"]
            if res_data.get("csrf_name"):
                self.csrf_name = res_data["csrf_name"]

    def post(self, endpoint, extra_data=None):
        url = f"{self.base_url}{endpoint}"
        payload = {
            self.csrf_name: self.csrf_hash,
            "init_data": self.init_data
        }
        if extra_data:
            payload.update(extra_data)
        
        try:
            res = self.session.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                self._update_csrf(data)
                return data
            else:
                log.warning(f"Request ke {endpoint} gagal HTTP {res.status_code}")
                return None
        except Exception as e:
            log.error(f"Error saat POST ke {endpoint}: {e}")
            return None

    def get_csrf_token(self):
        try:
            log.info("Mengambil halaman utama & CSRF Token...")
            res = self.session.get(f"{self.base_url}/chest/", timeout=15)
            if res.status_code == 200:
                match = re.search(r'"csrf_name"\s*:\s*"([^"]+)",\s*"csrf_hash"\s*:\s*"([^"]+)"', res.text)
                if match:
                    self.csrf_name = match.group(1)
                    self.csrf_hash = match.group(2)
                    return True
                match_hash = re.search(r'"csrf_hash"\s*:\s*"([^"]+)"', res.text)
                if match_hash:
                    self.csrf_hash = match_hash.group(1)
                    return True
            return False
        except Exception as e:
            log.error(f"Gagal mengambil token CSRF: {e}")
            return False

    def init_session(self):
        if not self.init_data:
            log.info("Data login (init_data) belum terisi.")
            print("\n" + "="*50)
            print("🔑 SILAKAN INPUT / PASTE init_data TELEGRAM ANDA:")
            print("="*50)
            input_data = input("init_data: ").strip()
            if input_data:
                self.set_init_data(input_data)
            else:
                log.error("Data login tidak boleh kosong!")
                return False

        if not self.get_csrf_token():
            log.warning("Gagal parsing CSRF token dari halaman awal, mencoba login langsung...")

        u_name = self.telegram_user.get("first_name", "Player")
        u_handle = f"@{self.telegram_user.get('username')}" if self.telegram_user.get('username') else ""
        log.info(f"Otentikasi Akun ({u_name} | {u_handle})...")

        # Login via auth_telegram resmi
        res = self.post("/chest/auth_telegram")
        if not res or not res.get("status"):
            log.error(f"Gagal otentikasi akun: {res.get('message') if res else 'No Response'}")
            return False

        self.player_data = res.get("player", {})
        self.equipped_data = res.get("equipped_data", {})
        
        # Ambil saldo TON riil dari endpoint ton_hud game
        ton_hud = self.post("/chest/ton_hud")
        if ton_hud and ton_hud.get("status"):
            self.ton_data["total"] = float(ton_hud.get("total", 0.0))
        else:
            w_st = self.post("/chest/wallet_state")
            if w_st and w_st.get("status"):
                self.ton_data["total"] = float(w_st.get("balance", w_st.get("earned", 0.0)))
        
        lvl = self.player_data.get("hero_level", self.player_data.get("level", 1))
        stg = f"{self.player_data.get('stage', 1)}-{self.player_data.get('sub_stage', 1)}"
        gs = f"{self.equipped_data.get('total_gs', 0):,}"
        gold = f"{int(self.player_data.get('coins', 0)):,}"
        ton_bal = f"{self.ton_data.get('total', 0.0):.6f}"

        log.info(f"Login Sukses! Hero Lv.{lvl} | Stage {stg} | GS: {gs} | Gold: {gold} | 💎 TON: {ton_bal}")
        return True

    def claim_all_rewards(self):
        log.info("--- [AUTO CLAIM] Mengecek Seluruh Reward & Misi ---")
        # Welcome & Daily Login
        w_res = self.post("/chest/welcome_status")
        if w_res and w_res.get("status"):
            daily = w_res.get("daily", {})
            if daily.get("available"):
                c_d = self.post("/chest/welcome_claim", {"type": "daily"})
                if c_d and c_d.get("status"):
                    log.info(f"📅 Daily Login Reward berhasil diklaim! (+{c_d.get('coins', 0):,} Gold)")
                time.sleep(CONFIG.get("ACTION_DELAY", 1))

        if CONFIG.get("AUTO_CLAIM_QUESTS"):
            q_res = self.post("/chest/quest_state")
            if q_res and q_res.get("status"):
                quests = q_res.get("quests", [])
                for q in quests:
                    idx = q.get("idx")
                    title = q.get("title", f"Quest {idx}")
                    done = q.get("done", False)
                    claimed = q.get("claimed", False)
                    if done and not claimed:
                        qc_res = self.post("/chest/quest_claim", {"idx": idx})
                        if qc_res and qc_res.get("status"):
                            log.info(f"🏆 Quest Selesai Diklaim: [{title}]!")
                        time.sleep(CONFIG.get("ACTION_DELAY", 1))

        if CONFIG.get("AUTO_CLAIM_CLAN"):
            c_res = self.post("/chest/clan_claim")
            if c_res and c_res.get("status"):
                log.info(f"🛡️ Hadiah Clan diklaim! {c_res.get('reward', {})}")
                time.sleep(CONFIG.get("ACTION_DELAY", 1))

        if CONFIG.get("AUTO_CLAIM_BOSS"):
            b_res = self.post("/chest/boss_state")
            if b_res and b_res.get("status") and b_res.get("claim"):
                boss_id = b_res["claim"].get("boss_id")
                if boss_id:
                    bc_res = self.post("/chest/boss_claim", {"boss_id": boss_id})
                    if bc_res and bc_res.get("status"):
                        log.info("👹 Hadiah World Boss berhasil diklaim!")
                    time.sleep(CONFIG.get("ACTION_DELAY", 1))

    def ensure_ton_gate(self):
        ad_st = self.post("/chest/ad_state")
        if not ad_st:
            return

        m_count = ad_st.get("m_count", 0)
        m_open = ad_st.get("m_open", False)

        # HANYA TONTON IKLAN JIKA GERBANG MATI / PAUSED (MONSTER GA MENGHASILKAN TON)
        if not m_open:
            log.warning(f"🚨 [GERBANG TON MATI / PAUSED!] TON Drop = 0. Menonton iklan agar TON aktif kembali...")
            
            while self.is_running:
                st_now = self.post("/chest/ad_state")
                if not st_now:
                    time.sleep(3)
                    continue

                is_op = st_now.get("m_open", False)
                cd = st_now.get("cooldown", 0)
                cnt = st_now.get("m_count", 0)

                if is_op:
                    log.info(f"🎉 GERBANG TON TELAH AKTIF (Ads: {cnt}/10)! Drop TON kembali mengalir, lanjut farming!")
                    break

                if cd > 0:
                    log.info(f"⏳ Cooldown server iklan: {cd} detik... Menunggu agar Gerbang TON bisa diaktifkan kembali.")
                    time.sleep(min(cd, 5))
                    continue

                log.info("📺 Memulai tontonan iklan untuk mengaktifkan kembali drop TON...")
                ok, self.csrf_hash = self.ads_engine.claim_one_ad(self.session, self.csrf_hash, self.csrf_name, kind="main")
                if not ok:
                    time.sleep(3)
        else:
            # Gerbang sedang aktif (monster masih menghasilkan TON), jadi TIDAK PERLU nonton iklan!
            log.info(f"✨ Gerbang TON sedang AKTIF (Ads: {m_count}/10). Monster masih menjatuhkan TON, gas farming terus!")

        if ad_st.get("t4_left", 0) > 0 and ad_st.get("t4_has", 0) == 0:
            log.info(f"🎁 Mengambil Peti T4 Sakti harian (Sisa: {ad_st.get('t4_left')}/15)...")
            ok_t4, self.csrf_hash = self.ads_engine.claim_one_ad(self.session, self.csrf_hash, self.csrf_name, kind="chest")
            if ok_t4:
                log.info("📦 Peti T4 Sakti berhasil masuk inventori!")

    def run_hunt(self):
        if not CONFIG.get("AUTO_HUNT"):
            return
        
        rounds = CONFIG.get("HUNT_ROUNDS", 100)
        kills_per_round = CONFIG.get("HUNT_KILLS_PER_BATCH", 1)
        hunt_delay = CONFIG.get("HUNT_DELAY", 0.65)
        log.info(f"--- [AUTO HUNT INSTANT 1-HIT] Membasmi Monster ({rounds} Monster Berturut-turut) ---")

        for r in range(rounds):
            # Cek status gerbang TON secara berkala tiap 5 kill
            if r % 5 == 0 and r > 0:
                ad_chk = self.post("/chest/ad_state")
                if ad_chk:
                    is_open = ad_chk.get("m_open", False)
                    # HANYA pause hunt dan nonton iklan jika gerbang benar-benar MATI (monster ga ada TON)
                    if not is_open:
                        log.warning("⚠️ DROP TON BERHENTI / PAUSE! Menghentikan kill monster sementara untuk menonton iklan...")
                        self.ensure_ton_gate()
                        log.info(f"⏩ Drop TON aktif kembali, melanjutkan farming monster (Kill #{r+1}/{rounds})!")

            h_res = self.post("/chest/hunt_kill", {"kills": kills_per_round})
            if h_res and h_res.get("status"):
                if h_res.get("blocked"):
                    log.warning(f"⚔️ Monster Stage {h_res.get('stage')}-{h_res.get('sub_stage')} terlalu kuat! Mereset posisi respawn...")
                    self.post("/chest/hunt_kill", {"is_death": 1})
                    time.sleep(1)
                    break

                stage = h_res.get("stage")
                sub_stage = h_res.get("sub_stage")
                coins = h_res.get("coins", 0)
                exp = h_res.get("hero_exp")
                exp_req = h_res.get("hero_exp_req")
                hero_lvl = h_res.get("hero_level")
                gate = h_res.get("gate", {})
                gate_str = f" | 📺 Ads: {gate.get('ads')}/{gate.get('max')}" if gate else ""
                ton_drop = h_res.get("ton", 0)
                if ton_drop > 0:
                    self.ton_data["total"] = float(self.ton_data.get("total", 0.0)) + float(ton_drop)

                if h_res.get("hero_leveled_up"):
                    log.info(f"🎉 HERO LEVEL UP -> Lv.{hero_lvl}!")
                
                ton_val = f"{self.ton_data['total']:.6f}"
                log.info(f"⚡ Kill #{r+1}: Stage {stage}-{sub_stage} MATI INSTAN! | Gold: {coins:,} | EXP: {exp}/{exp_req} | 💎 TON: {ton_val}{gate_str}")
            else:
                break
            
            time.sleep(hunt_delay)

    def run_arena(self):
        if not CONFIG.get("AUTO_ARENA"):
            return

        ar_res = self.post("/chest/arena_state")
        if not ar_res or not ar_res.get("status"):
            return

        free_left = ar_res.get("free_left", 0)
        if free_left <= 0:
            return

        log.info(f"--- [ARENA PVP] Menghabiskan {free_left} Tiket Free Arena ---")
        while free_left > 0:
            opponents = ar_res.get("opponents", [])
            if not opponents:
                break

            target = min(opponents, key=lambda x: int(x.get("gs", x.get("power", 999999999))))
            opp_id = target.get("id")
            opp_name = target.get("name", "Opponent")
            opp_power = target.get("gs", target.get("power", 0))
            
            log.info(f"⚔️ Duel PvP melawan: [{opp_name}] (GS: {opp_power:,})...")
            att_res = self.post("/chest/arena_fight", {"opp_id": opp_id})
            if att_res and att_res.get("status"):
                won = att_res.get("win", False)
                pts = att_res.get("points", 0)
                delta = att_res.get("delta", 0)
                if won:
                    log.info(f"🏆 MENANG Duel Arena! Points: {pts} (+{delta}) | Hadiah Gold: +{att_res.get('gold', 0):,}")
                else:
                    log.info(f"💀 Kalah Duel Arena. Points: {pts} ({delta})")
                free_left = att_res.get("free_left", free_left - 1)
            else:
                free_left -= 1
            time.sleep(CONFIG.get("ACTION_DELAY", 1))

    def run_boss_attack(self):
        if not CONFIG.get("AUTO_BOSS_ATTACK"):
            return

        b_res = self.post("/chest/boss_state")
        if not b_res or not b_res.get("status"):
            return

        boss = b_res.get("boss", {})
        attacks_left = b_res.get("attacks_left", 0)
        boss_name = boss.get("name", "World Boss")

        if attacks_left > 0:
            log.info(f"--- [WORLD BOSS] Menyerang Bos Dunia: [{boss_name}] ({attacks_left} Kesempatan) ---")
            for _ in range(attacks_left):
                att_res = self.post("/chest/boss_attack")
                if att_res and att_res.get("status"):
                    dmg = att_res.get("dmg", 0)
                    rem_hp = att_res.get("rem_hp", 0)
                    log.info(f"Serang Boss: {dmg:,} Damage | Sisa HP: {rem_hp:,}")
                else:
                    break
                time.sleep(CONFIG.get("ACTION_DELAY", 1))

    def run_ton_map(self):
        if not CONFIG.get("AUTO_TON_MAP"):
            return

        map_st = self.post("/chest/map_state")
        if not map_st or not map_st.get("status"):
            return

        entries = map_st.get("entries", 0)
        run = map_st.get("run", 0)
        if entries > 0 or run > 0:
            log.info(f"--- [TON MAP DUNGEON] Memasuki Dungeon TON (Entries: {entries}) ---")
            ent_res = self.post("/chest/map_enter")
            if ent_res and ent_res.get("status"):
                log.info("Berhasil masuk TON MAP! Membasmi monster khusus penghasil TON...")
                for _ in range(5):
                    kill_res = self.post("/chest/map_kill", {"kills": 1})
                    if kill_res and kill_res.get("status"):
                        ton_earn = kill_res.get("ton", 0)
                        log.info(f"Monster TON Map kalah! Hadiah: +{ton_earn} TON Coin!")
                    else:
                        break
                    time.sleep(1)
                self.post("/chest/map_exit")

    def open_chests(self):
        if not CONFIG.get("AUTO_OPEN_CHEST"):
            return

        tiers = CONFIG.get("CHEST_TIERS_TO_OPEN", ["t4", "t3", "t2", "t1"])
        log.info(f"--- [AUTO OPEN CHESTS & GEAR EQUIP] Memeriksa & Membuka Peti ---")

        for tier in tiers:
            while True:
                open_res = self.post("/chest/open", {"chest_type": tier})
                if not open_res or not open_res.get("status"):
                    break

                rem_chests = open_res.get("rem_chests", 0)
                item = open_res.get("item", {})
                diff = open_res.get("diff", 0)
                item_name = item.get("item_name", "Unknown")
                slot = item.get("slot", "")
                tier_item = item.get("tier", 1)
                total_gs = item.get("total_gs", 0)
                sell_val = item.get("sell_coin", 0)

                log.info(f"Buka Peti {tier.upper()} (Sisa: {rem_chests}) -> [{item_name}] ({slot.upper()} T{tier_item} | {total_gs} GS) | Diff: {'+' if diff > 0 else ''}{diff} GS")

                time.sleep(CONFIG.get("ACTION_DELAY", 0.8))

                if diff > 0 and CONFIG.get("AUTO_EQUIP_BETTER"):
                    eq_res = self.post("/chest/equip")
                    if eq_res and eq_res.get("status"):
                        log.info(f"==> ⚡ [EQUIP BERHASIL] {item_name} terpasang! GearScore Naik +{diff} GS!")
                        if eq_res.get("item"):
                            self.equipped_data.setdefault("slots", {})[slot] = eq_res["item"]
                        if eq_res.get("total_gs"):
                            self.equipped_data["total_gs"] = eq_res["total_gs"]
                else:
                    if CONFIG.get("AUTO_SELL_WORSE"):
                        sl_res = self.post("/chest/sell")
                        if sl_res and sl_res.get("status"):
                            log.info(f"==> 💰 [SELL] Gear dilebur jadi +{sell_val} Gold (Total: {sl_res.get('new_coins', 0):,})")

                time.sleep(CONFIG.get("ACTION_DELAY", 0.8))

    def forge_gear_anvil(self):
        if not CONFIG.get("AUTO_FORGE_ANVIL"):
            return

        log.info("--- [ANVIL FORGE] Menempa & Meningkatkan (+) Level Armor/Weapon ---")
        slots = ["boots", "pauldron", "ring", "helmet", "belt", "weapon", "pads", "gloves", "necklace", "shield"]
        
        for s in slots:
            forge_res = self.post("/chest/anvil_upgrade", {"slot": s})
            if forge_res and forge_res.get("status"):
                new_coins = forge_res.get("new_coins", 0)
                log.info(f"🔨 Sukses Menempa [{s.upper()}]! GearScore meningkat! Sisa Gold: {new_coins:,}")
            elif forge_res and forge_res.get("message"):
                msg = forge_res.get("message", "")
                if "Not enough Gold" in msg:
                    log.info(f"ℹ️ Tempa [{s.upper()}]: {msg}")
            time.sleep(CONFIG.get("ACTION_DELAY", 0.8))

    def upgrade_stats(self):
        if not CONFIG.get("AUTO_UPGRADE_STAT"):
            return

        log.info("--- [TRAINING STATS] Meningkatkan Atribut Hero (STR/DEF/HP) ---")
        min_reserve = CONFIG.get("MIN_COINS_RESERVE", 1000)
        stats = ["str", "def", "hp"]
        
        for stat in stats:
            for _ in range(5):
                up_res = self.post("/chest/upgrade_stat", {"stat": stat})
                if up_res and up_res.get("status"):
                    lvl = up_res.get("new_level", 0)
                    rem_coins = up_res.get("rem_coins", 0)
                    log.info(f"💪 Stat [{stat.upper()}] Naik Level! Sisa Gold: {rem_coins:,}")
                    if rem_coins < min_reserve:
                        return
                else:
                    break
                time.sleep(CONFIG.get("ACTION_DELAY", 0.8))

    def run_cycle(self):
        log.info("==================================================")
        log.info("       MEMULAI SIKLUS POWERFUL HERO RPG")
        log.info("==================================================")
        self.ensure_ton_gate()
        self.claim_all_rewards()
        self.run_hunt()
        self.run_arena()
        self.run_boss_attack()
        self.run_ton_map()
        self.open_chests()
        self.forge_gear_anvil()
        self.upgrade_stats()
        self.claim_all_rewards()

        log.info("==================================================")
        log.info("            SIKLUS SELESAI DENGAN SUKSES")
        log.info("==================================================")

    def start(self, continuous=True):
        self.is_running = True
        if not self.init_session():
            log.error("Inisialisasi bot gagal!")
            self.is_running = False
            return

        while self.is_running:
            try:
                self.run_cycle()
            except Exception as e:
                log.error(f"Error siklus: {e}", exc_info=True)

            if not continuous:
                break

            loop_delay = CONFIG.get("LOOP_DELAY", 10)
            log.info(f"Menunggu {loop_delay} detik untuk siklus farming berikutnya...")
            time.sleep(loop_delay)


# ==============================================================================
# 4. ENTRY POINT & MENU INTERAKTIF
# ==============================================================================
def input_init_data():
    print("\n" + "="*50)
    print("🔑 MASUKKAN / PASTE init_data TELEGRAM ANDA:")
    print("="*50)
    raw = input("init_data: ").strip()
    if raw:
        if save_init_data_to_file(raw):
            print("✅ Data login berhasil disimpan ke session.json!")
            return raw
    else:
        print("⚠️ Input kosong.")
    return None

def main():
    while True:
        current_init = load_saved_init_data()
        user_info = "Belum Ada (Silakan Input)"
        if current_init:
            try:
                parsed = urllib.parse.parse_qs(current_init)
                u = json.loads(parsed.get("user", ["{}"])[0])
                user_info = f"{u.get('first_name', 'Player')} (@{u.get('username', '-')})"
            except Exception:
                user_info = "Tersimpan (Format Khusus)"

        print("\n" + "="*50)
        print("   ⚔️ HERO RPG BOT (STANDALONE & MULTI-ACCOUNT) ⚔️")
        print("="*50)
        print(f"Akun Terpilih: {user_info}")
        print("-"*50)
        print("1. Masukkan / Ganti init_data")
        print("2. Start Bot (Jalankan Otomasi)")
        print("3. Keluar")
        print("="*50)
        
        choice = input("Pilih menu [1-3]: ").strip()
        
        if choice == "1":
            input_init_data()
        elif choice == "2":
            saved = load_saved_init_data()
            if not saved:
                print("\n⚠️ Data login belum ada! Silakan pilih menu 1 terlebih dahulu.")
                continue
            bot = HeroRPGBot(init_data=saved)
            bot.start(continuous=True)
            break
        elif choice == "3":
            print("Keluar dari bot. Sampai jumpa!")
            sys.exit(0)
        else:
            print("Pilihan tidak valid, silakan ketik 1, 2, atau 3.")

if __name__ == "__main__":
    main()

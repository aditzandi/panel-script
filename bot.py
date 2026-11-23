import time
import re
import json
import logging
import requests
import urllib.parse
from config import INIT_DATA, CONFIG, USER_AGENT
from ads_engine import AdsEngine
try:
    from ad_watcher import ChromeAdWatcher
except ImportError:
    ChromeAdWatcher = None

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("HeroRPGBot")

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
        self.ad_watcher = None
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

    def init_session(self):
        if not self.init_data or not self.init_data.strip():
            log.warning("Data login (init_data) masih kosong!")
            print("\n" + "="*50)
            print(" [LOGIN] Masukkan init_data Telegram WebApp Anda:")
            print("="*50)
            inp = input("init_data: ").strip()
            if not inp:
                log.error("init_data tidak boleh kosong!")
                return False
            self.set_init_data(inp)
            # Simpan juga ke config.py untuk kemudahan berikutnya
            try:
                with open("config.py", "r", encoding="utf-8") as f:
                    cfg_text = f.read()
                cfg_text = re.sub(r'INIT_DATA\s*=\s*".*?"', f'INIT_DATA = "{inp}"', cfg_text)
                with open("config.py", "w", encoding="utf-8") as f:
                    f.write(cfg_text)
            except Exception:
                pass

        log.info("Mengambil halaman utama & CSRF Token...")
        try:
            r = self.session.get(f"{self.base_url}/chest/", timeout=15)
            m_name = re.search(r'csrfName\s*=\s*[\x22\x27]([^\x22\x27]+)', r.text)
            m_hash = re.search(r'csrfHash\s*=\s*[\x22\x27]([^\x22\x27]+)', r.text)
            if m_name:
                self.csrf_name = m_name.group(1)
            if m_hash:
                self.csrf_hash = m_hash.group(1)
        except Exception as e:
            log.error(f"Gagal mengambil CSRF awal: {e}")
            return False

        user_id = str(self.telegram_user.get("id", ""))
        first_name = self.telegram_user.get("first_name", "")
        username = self.telegram_user.get("username", "")

        auth_payload = {
            "telegram_id": user_id,
            "first_name": first_name,
            "username": username,
            "src": ""
        }
        log.info(f"Otentikasi Akun ({first_name} | @{username})...")
        auth_res = self.post("/chest/auth_telegram", auth_payload)
        if auth_res and auth_res.get("status"):
            self.player_data = auth_res.get("player", {})
            self.equipped_data = auth_res.get("equipped_data", {})
            coins = int(self.player_data.get("coins", 0))
            stage = self.player_data.get("stage", 1)
            sub_stage = self.player_data.get("sub_stage", 1)
            hero_lvl = self.player_data.get("hero_level", 1)
            total_gs = self.equipped_data.get("total_gs", 0)
            
            # Ambil data TON terkini
            w_res = self.post("/chest/wallet_state")
            if w_res and w_res.get("status"):
                self.ton_data["balance"] = float(w_res.get("balance", 0.0))
                self.ton_data["earned"] = float(w_res.get("earned", 0.0))
                self.ton_data["min"] = float(w_res.get("min", 0.2))
            th_res = self.post("/chest/ton_hud")
            if th_res and th_res.get("status"):
                self.ton_data["total"] = float(th_res.get("total", 0.0))

            ton_str = f"{self.ton_data['total']:.6f}"
            log.info(f"Login Sukses! Hero Lv.{hero_lvl} | Stage {stage}-{sub_stage} | GS: {total_gs:,} | Gold: {coins:,} | 💎 TON: {ton_str}")
            return True
        else:
            log.error(f"Login Gagal! Response: {auth_res}")
            return False

    def claim_all_rewards(self):
        log.info("--- [AUTO CLAIM] Mengecek Seluruh Reward & Misi ---")
        
        # 1. Offline & Daily Reward
        if CONFIG.get("AUTO_CLAIM_OFFLINE") or CONFIG.get("AUTO_CLAIM_DAILY"):
            w_res = self.post("/chest/welcome_status")
            if w_res and w_res.get("status"):
                if w_res.get("offline"):
                    off_res = self.post("/chest/welcome_claim", {"type": "offline"})
                    if off_res and off_res.get("status"):
                        log.info(f"🎁 Offline Reward berhasil di-claim! Total Gold: {off_res.get('coins', 0):,}")
                    time.sleep(CONFIG.get("ACTION_DELAY", 1))

                daily = w_res.get("daily", {})
                if daily.get("available"):
                    d_res = self.post("/chest/welcome_claim", {"type": "daily"})
                    if d_res and d_res.get("status"):
                        log.info(f"🎁 Daily Login Day {daily.get('day')} berhasil di-claim! Total Gold: {d_res.get('coins', 0):,}")
                    time.sleep(CONFIG.get("ACTION_DELAY", 1))

        # 2. Tutorial Claim
        if CONFIG.get("AUTO_CLAIM_TUTORIAL"):
            t_res = self.post("/chest/tut_claim")
            if t_res and t_res.get("status"):
                log.info("🎁 Tutorial Reward berhasil diklaim!")
                time.sleep(CONFIG.get("ACTION_DELAY", 1))

        # 3. Quests Claim
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

        # 4. Clan Claim
        if CONFIG.get("AUTO_CLAIM_CLAN"):
            c_res = self.post("/chest/clan_claim")
            if c_res and c_res.get("status"):
                reward = c_res.get("reward", {})
                log.info(f"🛡️ Hadiah Clan diklaim! {reward}")
                time.sleep(CONFIG.get("ACTION_DELAY", 1))

        # 5. World Boss Claim
        if CONFIG.get("AUTO_CLAIM_BOSS"):
            b_res = self.post("/chest/boss_state")
            if b_res and b_res.get("status") and b_res.get("claim"):
                boss_id = b_res["claim"].get("boss_id")
                if boss_id:
                    bc_res = self.post("/chest/boss_claim", {"boss_id": boss_id})
                    if bc_res and bc_res.get("status"):
                        log.info("👹 Hadiah World Boss berhasil diklaim!")
                    time.sleep(CONFIG.get("ACTION_DELAY", 1))

        # 6. Auto Trigger Iklan (Sudah ditangani AdsEngine cerdas di ensure_ton_gate)
        pass

    def ensure_ton_gate(self):
        """Prioritas tertinggi: memastikan gerbang TON selalu aktif (10/10 atau aktif)."""
        ad_st = self.post("/chest/ad_state")
        if not ad_st:
            return

        m_count = ad_st.get("m_count", 0)
        m_open = ad_st.get("m_open", False)

        # Jika gerbang TON belum aktif (0 detik tersisa) atau iklan belum maksimal
        if not m_open or m_count < 10:
            log.info(f"🚨 [PRIORITAS GERBANG TON] Status Gerbang: {'AKTIF' if m_open else 'MATI'} | Ads: {m_count}/10")
            log.info("⏳ Menghentikan semua tugas lain untuk memprioritaskan iklan Gerbang TON...")
            while self.is_running:
                ok, self.csrf_hash = self.ads_engine.claim_one_ad(self.session, self.csrf_hash, self.csrf_name, kind="main")
                time.sleep(1)
                # Cek status terbaru
                st_now = self.post("/chest/ad_state")
                if not st_now:
                    break
                cnt = st_now.get("m_count", 0)
                is_op = st_now.get("m_open", False)
                cd = st_now.get("cooldown", 0)
                if not ok:
                    # Jika ada cooldown server (misal cooldown > 0 detik)
                    if cd > 0:
                        log.info(f"⏳ Iklan TON cooldown {cd} detik. Lanjut farming sampai cooldown selesai!")
                    elif is_op:
                        log.info(f"ℹ️ Gerbang TON sudah AKTIF (Ads: {cnt}/10). Lanjut tugas!")
                    break
                if cnt >= 10:
                    log.info(f"🎯 Gerbang TON telah MAKSIMAL (Ads: {cnt}/10)! Selesai prioritas TON.")
                    break

        # Jatah Peti Sakti Tier 4
        if ad_st.get("t4_left", 0) > 0 and ad_st.get("t4_has", 0) == 0:
            log.info(f"🎁 Mengambil Peti T4 Sakti harian (Sisa: {ad_st.get('t4_left')}/15)...")
            ok_t4, self.csrf_hash = self.ads_engine.claim_one_ad(self.session, self.csrf_hash, self.csrf_name, kind="chest")
            if ok_t4:
                log.info("📦 Peti T4 Sakti berhasil masuk inventori!")

    def run_hunt(self):
        if not CONFIG.get("AUTO_HUNT"):
            return
        
        rounds = CONFIG.get("HUNT_ROUNDS", 25)
        kills_per_round = CONFIG.get("HUNT_KILLS_PER_BATCH", 1)
        hunt_delay = CONFIG.get("HUNT_DELAY", 0.65)
        log.info(f"--- [AUTO HUNT INSTANT 1-HIT] Membasmi Monster ({rounds} Monster Berturut-turut) ---")

        for r in range(rounds):
            # Cek status cooldown iklan TON setiap 5 kill
            if r % 5 == 0 and r > 0:
                ad_chk = self.post("/chest/ad_state")
                if ad_chk:
                    m_cnt = ad_chk.get("m_count", 0)
                    cd = ad_chk.get("cooldown", 0)
                    is_open = ad_chk.get("m_open", False)
                    # Jika cooldown sudah 0 detik DAN iklan TON belum penuh (10/10), SEGERA STOP HUNT!
                    if cd == 0 and m_cnt < 10:
                        log.warning(f"🚨 [COOLDOWN TON SELESAI!] Iklan Gerbang TON siap diklik (Ads: {m_cnt}/10). Menghentikan hunt sementara...")
                        self.ensure_ton_gate()
                        log.info(f"⏩ Iklan TON telah diamankan, melanjutkan farming monster (Kill #{r+1}/{rounds})!")
                    elif not is_open:
                        log.warning("⚠️ Gerbang TON MATI! Menghentikan hunt untuk prioritas iklan TON...")
                        self.ensure_ton_gate()
                        log.info(f"⏩ Gerbang TON aktif kembali, melanjutkan farming monster (Kill #{r+1}/{rounds})!")

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
                
                # Cek di tengah hunt jika gate mendadak mati (ads 0/10 atau m_open false)
                if gate and (gate.get('ads', 1) == 0 or not gate.get('open', True)):
                    log.warning("⚠️ Gerbang TON habis di tengah pertempuran! Menghentikan hunt sementara untuk prioritas TON...")
                    self.ensure_ton_gate()
                    log.info("⏩ Gerbang TON sudah diamankan, melanjutkan farming monster!")
                
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

            valid_opps = sorted(opponents, key=lambda x: int(x.get("gs", 9999999)))
            target = valid_opps[0]

            opp_id = target.get("id")
            opp_name = target.get("name", "Unknown")
            opp_gs = target.get("gs", 0)

            f_res = self.post("/chest/arena_fight", {"opp_id": opp_id})
            if f_res and f_res.get("status"):
                win = f_res.get("win", False)
                gold = f_res.get("earned_coins", 0)
                log.info(f"Duel vs [{opp_name}] (GS {opp_gs:,}): {'🏆 MENANG' if win else '❌ KALAH'} | +{gold} Gold")
            else:
                break

            time.sleep(CONFIG.get("ACTION_DELAY", 1.2))
            ar_res = self.post("/chest/arena_state")
            if not ar_res or not ar_res.get("status"):
                break
            free_left = ar_res.get("free_left", 0)

    def run_boss_attack(self):
        if not CONFIG.get("AUTO_BOSS_ATTACK"):
            return

        b_res = self.post("/chest/boss_state")
        if b_res and b_res.get("status") and b_res.get("active"):
            boss_info = b_res.get("boss", {})
            boss_name = boss_info.get("name", "World Boss")
            log.info(f"--- [WORLD BOSS] Menyerang Bos Dunia: [{boss_name}] ---")
            for _ in range(3):
                atk_res = self.post("/chest/boss_attack")
                if atk_res and atk_res.get("status"):
                    dmg = atk_res.get("dmg", 0)
                    rem_hp = atk_res.get("boss_hp", 0)
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

                # Equip Jika GS Lebih Tinggi
                if diff > 0 and CONFIG.get("AUTO_EQUIP_BETTER"):
                    eq_res = self.post("/chest/equip")
                    if eq_res and eq_res.get("status"):
                        log.info(f"==> ⚡ [EQUIP BERHASIL] {item_name} terpasang! GearScore Naik +{diff} GS!")
                        if eq_res.get("item"):
                            self.equipped_data.setdefault("slots", {})[slot] = eq_res["item"]
                        if eq_res.get("total_gs"):
                            self.equipped_data["total_gs"] = eq_res["total_gs"]
                else:
                    # Jual Menjadi Gold Tambahan
                    if CONFIG.get("AUTO_SELL_WORSE"):
                        sl_res = self.post("/chest/sell")
                        if sl_res and sl_res.get("status"):
                            log.info(f"==> 💰 [SELL] Gear dilebur jadi +{sell_val} Gold (Total: {sl_res.get('new_coins', 0):,})")

                time.sleep(CONFIG.get("ACTION_DELAY", 0.8))

    def forge_gear_anvil(self):
        if not CONFIG.get("AUTO_FORGE_ANVIL"):
            return

        log.info("--- [ANVIL FORGE] Menempa & Meningkatkan (+) Level Armor/Weapon ---")
        slots = ["weapon", "ring", "necklace", "helmet", "pauldron", "pads", "gloves", "boots", "shield", "belt"]
        
        for s in slots:
            forge_res = self.post("/chest/anvil_upgrade", {"slot": s})
            if forge_res and forge_res.get("status"):
                new_coins = forge_res.get("new_coins", 0)
                log.info(f"🔨 Sukses Menempa [{s.upper()}]! GearScore meningkat! Sisa Gold: {new_coins:,}")
            elif forge_res and forge_res.get("message") and "Not enough Gold" in forge_res["message"]:
                # Gold tidak cukup untuk biaya tempa berikutnya
                break
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
                    new_coins = up_res.get("new_coins", 0)
                    log.info(f"💪 Stat [{stat.upper()}] Naik Level! Sisa Gold: {new_coins:,}")
                    if new_coins < min_reserve:
                        break
                else:
                    break
                time.sleep(CONFIG.get("ACTION_DELAY", 0.8))

    def run_cycle(self):
        log.info("==================================================")
        log.info("       MEMULAI SIKLUS POWERFUL HERO RPG")
        log.info("==================================================")
        # 1. PRIORITAS UTAMA: GERBANG TON
        self.ensure_ton_gate()

        # 2. Klaim Hadiah & Misi
        self.claim_all_rewards()

        # 3. Farming Monster & Gold Intensif
        self.run_hunt()

        # 3. Duel Arena PvP
        self.run_arena()

        # 4. Serang World Boss
        self.run_boss_attack()

        # 5. Ekspedisi Dungeon TON Map (Jika Ada Tiket)
        self.run_ton_map()

        # 6. Buka Peti & Optimasi Armor
        self.open_chests()

        # 7. Tempa Armor & Senjata di Anvil (Memanfaatkan Gold)
        self.forge_gear_anvil()

        # 8. Latih Atribut STR/DEF/HP (Memanfaatkan Gold)
        self.upgrade_stats()

        # 9. Cek kembali quest yang selesai
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

            loop_sec = CONFIG.get("LOOP_DELAY", 10)
            log.info(f"Menunggu {loop_sec} detik untuk siklus farming berikutnya...")
            for _ in range(loop_sec):
                if not self.is_running:
                    break
                time.sleep(1)

    def stop(self):
        self.is_running = False
        log.info("Bot dihentikan oleh user.")

if __name__ == "__main__":
    bot = HeroRPGBot()
    bot.start(continuous=True)

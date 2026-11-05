import time
import sys
import json
import os
import requests
import re
from bs4 import BeautifulSoup

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[1;31m"
C_GREEN = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_BLUE = "\033[1;34m"
C_PURPLE = "\033[1;35m"
C_CYAN = "\033[1;36m"
C_WHITE = "\033[1;37m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def msg(text, is_final=False):
    if is_final:
        sys.stdout.write("\r\033[K" + text + "\n")
        return
    sys.stdout.write("\r\033[K" + text)
    sys.stdout.flush()

def print_banner(wallet="$0.00000", energy="N/A", solver_name="N/A", api_balance="N/A"):
    clear_screen()
    print(f"{C_CYAN}{C_BOLD}╔══════════════════════════════════════════════════════╗")
    print("║                      MINITASKY                       ║")
    print("╠══════════════════════════════════════════════════════╣")
    print("║ Author       : AHD1905                               ║")
    print("║ Grup         : ScriptyXsouu                          ║")
    print("║ Partner      : BONCEL❤️                              ║")
    print("╟──────────────────────────────────────────────────────╢")
    print(f"║ Wallet       : {wallet:<37}║")
    print(f"║ Energy       : {energy:<37}║")
    print(f"║ Solver       : {solver_name:<37}║")
    print(f"║ Balance      : {api_balance:<37}║")
    print(f"╚══════════════════════════════════════════════════════╝{C_RESET}\n")

config_file = "config.json"

def load_config():
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config_data):
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=4)

def extract_reward_from_response(response, default_reward="0.00000"):
    """Ekstraksi reward per task, fallback ke nilai default jika gagal"""
    html_text = response.text
    try:
        data = response.json()
        for key in ("reward", "amount", "earned", "message", "msg", "success"):
            if key in data and data[key]:
                val = str(data[key])
                m = re.search(r"\$?([0-9]+\.[0-9]+)", val)
                if m:
                    return m.group(1)
    except Exception:
        pass
    match_video = re.search(r"\+\s*\$([0-9]+\.[0-9]+)", html_text, re.I)
    if match_video:
        return match_video.group(1)
    return default_reward

def fetch_live_data(active_apikey="", cookie="", user_agent=""):
    wallet = "$0.00000"
    energy = "N/A"
    solver_display = "N/A"
    api_bal = "N/A"

    solver_display = "MBAH YONO"

    if cookie:
        try:
            headers = {
                "User-Agent": user_agent or "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
                "Cookie": cookie,
            }
            res_dash = requests.get("https://minitasky.com/dashboard", headers=headers, timeout=10)
            dash_html = res_dash.text
            match_bal = re.search(r"MAIN\s+BALANCE[\s\S]*?\$([0-9\.]+)", dash_html, re.IGNORECASE)
            if match_bal:
                wallet = "$" + match_bal.group(1)
            else:
                match_bal2 = re.search(r"\$([0-9]+\.[0-9]{2,})", dash_html)
                if match_bal2:
                    wallet = "$" + match_bal2.group(1)

            res_faucet = requests.get("https://minitasky.com/faucet", headers=headers, timeout=10)
            f_html = res_faucet.text
            soup_faucet = BeautifulSoup(f_html, "html.parser")

            energy_elem = soup_faucet.find(string=re.compile("Energy", re.I))
            if energy_elem:
                parent = energy_elem.find_parent()
                if parent:
                    badge = parent.find_next(string=re.compile(r"^\s*\d+(\.\d+)?\s*$"))
                    if badge:
                        energy = badge.strip()
                    else:
                        match_num = re.search(r"\b(\d+(?:\.\d+)?)\b", parent.get_text())
                        if match_num:
                            energy = match_num.group(1)

            if energy == "N/A":
                match_eng = re.search(r"Energy[^<>\d]*(\d+(?:\.\d+)?)", f_html, re.IGNORECASE)
                if match_eng:
                    energy = match_eng.group(1)
        except Exception:
            pass

    if active_apikey:
        try:
            res_api = requests.get(
                "https://api.waryono.my.id/balance.php",
                params={"apikey": active_apikey},
                timeout=10,
            )
            data = res_api.json()
            if "balance" in data:
                api_bal = str(data["balance"])
        except Exception:
            pass

    return wallet, energy, solver_display, api_bal

def input_config_menu():
    config = load_config()
    print_banner()
    apikey_war = input(f"{C_YELLOW}Masukkan API Key Waryono: {C_WHITE}").strip()
    if apikey_war:
        config["apikey_waryono"] = apikey_war

    cookie = input(f"{C_YELLOW}Masukkan Cookie Minitasky: {C_WHITE}").strip()
    if cookie:
        config["cookie"] = cookie

    user_agent = input(f"{C_YELLOW}Masukkan User-Agent (Opsional): {C_WHITE}").strip()
    if user_agent:
        config["user_agent"] = user_agent

    save_config(config)
    print(f"\n{C_GREEN}[✔] Konfigurasi lengkap berhasil disimpan!{C_RESET}")
    input(f"\n{C_YELLOW}Tekan Enter untuk kembali...{C_RESET}")

def reset_config():
    print_banner()
    confirm = input(f"{C_RED}Yakin ingin mereset seluruh konfigurasi? (y/n): {C_WHITE}").strip().lower()
    if confirm == "y":
        if os.path.exists(config_file):
            os.remove(config_file)
        print(f"\n{C_GREEN}[✔] Konfigurasi berhasil direset!{C_RESET}")
    else:
        print(f"\n{C_YELLOW}[!] Reset dibatalkan.{C_RESET}")
    input(f"\n{C_YELLOW}Tekan Enter untuk kembali...{C_RESET}")

def bot_working_panel(sub_choice):
    config = load_config()

    active_apikey = config.get("apikey_waryono", "")

    saved_cookie = config.get("cookie", "")
    saved_user_agent = config.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36")

    if not saved_cookie or not active_apikey:
        w, e, s, b = fetch_live_data(active_apikey, saved_cookie, saved_user_agent)
        print_banner(w, e, s, b)
        print(f"{C_RED}[!] Konfigurasi belum lengkap! Harap isi melalui menu Input Config.{C_RESET}\n")
        input(f"{C_YELLOW}Tekan Enter untuk kembali...{C_RESET}")
        return

    session = requests.Session()
    session.headers.update({
        "User-Agent": saved_user_agent,
        "Cookie": saved_cookie,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.6,en;q=0.5",
    })

    def refresh_banner():
        w, e, s, b = fetch_live_data(active_apikey, saved_cookie, saved_user_agent)
        print_banner(w, e, s, b)

        try:
            val_e = float(e) if e != "N/A" else 1.0
        except ValueError:
            val_e = 1.0

        if val_e <= 0:
            print(f"{C_RED}Energy Habis!")
            print("Kerjakan task PTC/VIDEO/SHORTLINKS untuk mendapatkan energi tambahan!")
            input(f"Klik ENTER untuk kembali ke panel Kerja!{C_RESET}")

    def check_api():
        try:
            session.get("https://minitasky.com/api/get_notifications.php")
        except Exception:
            pass

    def solve_turnstile(sitekey, pageurl, max_retries=3):
        api_base = "https://api.waryono.my.id"
        for attempt in range(1, max_retries + 1):
            msg(f"{C_YELLOW}⚡ Solving Turnstile [Waryono] ({attempt}/{max_retries})...{C_RESET}")
            try:
                payload = {"apikey": active_apikey, "methods": "turnstile", "domain": pageurl, "sitekey": sitekey, "action": "", "cdata": ""}
                res = requests.post(f"{api_base}/in.php", json=payload)
                json_req = res.json()
                if not json_req or json_req.get("status") != 1:
                    time.sleep(2)
                    continue

                task_id = json_req.get("request")
                for _ in range(30):
                    time.sleep(3)
                    poll_res = requests.get(f"{api_base}/res.php", params={"apikey": active_apikey, "id": task_id, "action": "get", "json": 1})
                    json_poll = poll_res.json()
                    if json_poll and json_poll.get("status") == 1:
                        return json_poll.get("request")
            except Exception:
                pass
            time.sleep(3)
        return None

    def check_faucet_status():
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                res = session.get("https://minitasky.com/faucet", timeout=15)
                html = res.text
                energy_match = re.search(r"Energy\D+(\d+(?:\.\d+)?)", html, re.IGNORECASE)
                energy_count = float(energy_match.group(1)) if energy_match else 1.0
                is_locked = bool(re.search("Faucet Locked!", html, re.IGNORECASE) or re.search(r"Watch \d+ PTC Ads", html, re.IGNORECASE) or energy_count <= 0)
                time_left = 0
                match_time = re.search(r"let\s+timeLeft\s*=\s*(\d+)", html)
                if match_time:
                    time_left = int(match_time.group(1))
                return {"locked": is_locked, "energy": energy_count, "time_left": time_left, "html": html}
            except requests.exceptions.RequestException:
                if attempt == max_retries:
                    msg(f"{C_RED}✖ Gagal memeriksa status faucet setelah {max_retries} kali percobaan.{C_RESET}", is_final=True)
                    return {"locked": False, "energy": 1.0, "time_left": 0, "html": ""}
                msg(f"{C_YELLOW}⚠ Koneksi terputus (Connection Reset), mencoba ulang status faucet ({attempt}/{max_retries})...{C_RESET}")
                time.sleep(3)
        return {"locked": False, "energy": 1.0, "time_left": 0, "html": ""}

    def run_tap_game():
        url = "https://minitasky.com/tap-game"
        for attempt_task in range(1, 3):
            msg(f"{C_YELLOW}🎮 TAP GAME: Membuka Tap Game ({attempt_task})...{C_RESET}")
            try:
                res = session.get(url)
                html = res.text
                match_taps = re.search(r"TODAY\'S\s+TAPS[\s\S]*?(\d+)\s*/\s*(\d+)", html, re.IGNORECASE)
                if match_taps:
                    current_taps = int(match_taps.group(1))
                    max_taps = int(match_taps.group(2))
                    msg(f"{C_CYAN}ℹ Tap Status: {current_taps} / {max_taps} Taps hari ini.{C_RESET}", is_final=True)
                    if current_taps >= max_taps:
                        msg(f"{C_YELLOW}ℹ Tap Game sudah mencapai batas harian (400/400)!{C_RESET}", is_final=True)
                        return "LIMIT_REACHED"

                csrf_match = re.search(r'const\s+CSRF_TOKEN\s*=\s*[\'"]([^\'"]+)[\'"]', html)
                cycle_match = re.search(r'const\s+CYCLE_TOKEN\s*=\s*[\'"]([^\'"]+)[\'"]', html)
                taps_per_cycle_match = re.search(r"const\s+TAPS_PER_CYCLE\s*=\s*(\d+)", html)

                csrf_token = csrf_match.group(1) if csrf_match else ""
                cycle_token = cycle_match.group(1) if cycle_match else ""
                taps_per_cycle = taps_per_cycle_match.group(1) if taps_per_cycle_match else "5"

                sitekey = "0x4AAAAAACLoyBgrDeh_Bv0q"
                match_key = re.search(r"sitekey:\s*\'([^\']+)\'", html)
                if match_key:
                    sitekey = match_key.group(1)

                cf_token = ""
                if match_key or "cf-turnstile" in html:
                    msg(f"{C_YELLOW}⚡ TAP GAME: Turnstile terdeteksi, meminta solver...{C_RESET}")
                    cf_token = solve_turnstile(sitekey, url)
                    if not cf_token:
                        msg(f"{C_RED}✖ TAP GAME: Gagal solve captcha.{C_RESET}", is_final=True)
                        time.sleep(2)
                        continue

                form_data = {
                    "cf-turnstile-response": cf_token,
                    "action": "credit_cycle",
                    "csrf_token": csrf_token,
                    "cycle_token": cycle_token,
                    "taps": taps_per_cycle,
                    "website_url": "",
                    "ghost_tap_trap": "",
                }

                verify_res = session.post(url, data=form_data, headers={"Referer": url, "Origin": "https://minitasky.com"})

                rew = extract_reward_from_response(verify_res, default_reward="0.00005")
                msg(f"{C_GREEN}{C_BOLD}✅️ SUKSES - {rew}{C_RESET}", is_final=True)
                return "SUCCESS"
            except Exception:
                time.sleep(2)
        return "SUCCESS"

    failed_iframe_ads = set()
    iframe_empty_count = 0

    def run_ptc_iframe_single():
        nonlocal iframe_empty_count
        msg(f"{C_YELLOW}🔍 PTC IFRAME: Scanning ads...{C_RESET}")
        try:
            res = session.get("https://minitasky.com/ptc/")
            soup_iframe = BeautifulSoup(res.text, "html.parser")
            urls = []
            ad_cards = soup_iframe.find_all("div", class_=lambda x: x and ("ad-card" in x or "bg-white" in x or "rounded" in x))

            for card in ad_cards:
                btn_link = card.find("a", href=True)
                if not btn_link:
                    continue
                href = btn_link["href"]
                match_id = re.search(r"id=(\d+)", href)
                if match_id and match_id.group(1) not in failed_iframe_ads:
                    urls.append(href)

            if not urls:
                for a_tag in soup_iframe.find_all("a", href=True):
                    href = a_tag["href"]
                    match_id = re.search(r"id=(\d+)", href)
                    if match_id and match_id.group(1) not in failed_iframe_ads and href not in urls:
                        urls.append(href)

            urls = list(set(urls))
            if not urls:
                iframe_empty_count += 1
                if iframe_empty_count < 3:
                    time.sleep(2)
                    return "RETRY"
                return "NO_ADS"

            iframe_empty_count = 0
            url_path = urls[0]
            match_id_num = re.search(r"id=(\d+)", url_path)
            if not match_id_num:
                return "RETRY"

            ad_id_iframe = match_id_num.group(1)
            if ad_id_iframe in failed_iframe_ads:
                return "RETRY"

            check_api()
            id_url = f"https://minitasky.com/ptc/view_ad?id={ad_id_iframe}"

            msg(f"{C_BLUE}🌐 PTC IFRAME: Loading ID {ad_id_iframe}...{C_RESET}", is_final=True)
            res_ad = session.get(id_url)
            if "No ads available" in res_ad.text or "Invalid ad" in res_ad.text or "Expired" in res_ad.text:
                failed_iframe_ads.add(ad_id_iframe)
                return "RETRY"

            match_time = re.search(r"let\s+timeLeft\s*=\s*(\d+)", res_ad.text)
            time_left = int(match_time.group(1)) if match_time else 5

            match_token = re.search(r'name="token"\s+value="([^"]+)"', res_ad.text)
            match_adid = re.search(r'name="ad_id"\s+value="([^"]+)"', res_ad.text)
            match_sitekey = re.search(r"sitekey:\s*\'([^\']+)\'", res_ad.text)

            token = match_token.group(1) if match_token else ""
            ad_id = match_adid.group(1) if match_adid else ad_id_iframe
            sitekey = match_sitekey.group(1) if match_sitekey else "0x4AAAAAACLoyBgrDeh_Bv0q"

            for s in range(time_left, 0, -1):
                msg(f"{C_YELLOW}⏳ PTC {ad_id}: Waiting {s}s...{C_RESET}")
                time.sleep(1)
            print()

            cf_token = solve_turnstile(sitekey, id_url)
            if not cf_token:
                msg(f"{C_RED}✖ PTC IFRAME {ad_id}: Captcha error{C_RESET}", is_final=True)
                failed_iframe_ads.add(str(ad_id))
                return "RETRY"

            post_data = {
                "token": token,
                "ad_id": str(ad_id),
                "tab_away_seconds": "0",
                "ghost_btn_te": "",
                "website": "",
                "email_confirm": "",
                "url_field": "",
                "cf-turnstile-response": cf_token,
            }

            post_res = session.post(id_url, data=post_data, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": id_url,
                "Origin": "https://minitasky.com",
                "X-Requested-With": "XMLHttpRequest",
            })

            failed_iframe_ads.add(str(ad_id))

            rew = extract_reward_from_response(post_res, default_reward="0.00010")
            msg(f"{C_GREEN}{C_BOLD}✅️ SUKSES - {rew}{C_RESET}", is_final=True)
            return "SUCCESS"
        except Exception:
            return "RETRY"

    failed_window_ads = set()

    def run_ptc_window_single():
        msg(f"{C_YELLOW}🔍 PTC WINDOW: Scanning ads...{C_RESET}", is_final=True)
        try:
            win_res = session.get("https://minitasky.com/ptc/window_ads")
            soup = BeautifulSoup(win_res.text, "html.parser")
            match_global_token = re.search(r'let\s+token\s*=\s*[\'"]([^\'"]+)[\'"]', win_res.text)
            global_token = match_global_token.group(1) if match_global_token else ""

            view_btns = soup.find_all("a", class_="view-window-btn")
            valid_btn = None
            for b in view_btns:
                if b.get("data-id") not in failed_window_ads:
                    valid_btn = b
                    break

            if not valid_btn:
                return "NO_ADS"

            btn = valid_btn
            check_api()
            ad_id = btn.get("data-id")
            seconds = int(btn.get("data-seconds", "10"))

            if ad_id:
                start_url = f"https://minitasky.com/ptc/window_ads?start_ad={ad_id}"
                msg(f"{C_BLUE}🌐 PTC WINDOW: Loading ID {ad_id} ({seconds}s)...{C_RESET}", is_final=True)
                ad_page = session.get(start_url)

                match_token = re.search(r'name="token"\s+value="([^"]+)"', ad_page.text)
                token = match_token.group(1) if match_token else global_token
                match_sitekey = re.search(r"sitekey:\s*\'([^\']+)\'", ad_page.text)
                sitekey = match_sitekey.group(1) if match_sitekey else "0x4AAAAAACLoyBgrDeh_Bv0q"

                for s in range(seconds, 0, -1):
                    msg(f"{C_YELLOW}⏳ PTC WINDOW {ad_id}: Waiting {s}s...{C_RESET}")
                    time.sleep(1)

                cf_token = solve_turnstile(sitekey, start_url)
                if not cf_token:
                    failed_window_ads.add(str(ad_id))
                    return "RETRY"

                post_data = {
                    "token": token,
                    "ad_id": str(ad_id),
                    "tab_away_seconds": "0",
                    "ghost_btn_te": "",
                    "website": "",
                    "email_confirm": "",
                    "url_field": "",
                    "cf-turnstile-response": cf_token,
                }

                post_res = session.post("https://minitasky.com/ptc/window_ads", data=post_data, headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": start_url,
                    "Origin": "https://minitasky.com",
                    "X-Requested-With": "XMLHttpRequest",
                })

                failed_window_ads.add(str(ad_id))

                rew = extract_reward_from_response(post_res, default_reward="0.00010")
                msg(f"{C_GREEN}{C_BOLD}✅️ SUKSES - {rew}{C_RESET}", is_final=True)
                return "SUCCESS"
            return "NO_ADS"
        except Exception:
            return "RETRY"

    failed_video_ads = set()

    def watch_single_video(ad_id):
        check_api()
        page_url = f"https://minitasky.com/watch_video?id={ad_id}"

        msg(f"{C_BLUE}🎥 VIDEO: Loading ID {ad_id}...{C_RESET}", is_final=True)
        res = session.get(page_url, headers={
            "Referer": "https://minitasky.com/earn_video",
            "User-Agent": saved_user_agent,
            "Cookie": saved_cookie,
        })
        html = res.text

        if "Please login first" in html or "login" in res.url or "No ads available" in html:
            failed_video_ads.add(str(ad_id))
            return False

        match_duration = re.search(r"const\s+duration\s*=\s*(\d+)", html, re.IGNORECASE)
        duration = int(match_duration.group(1)) if match_duration else 10

        match_adid = re.search(r'id=["\']ad_id["\']\s+value=["\']([^"\']+)["\']', html, re.IGNORECASE)
        ad_id_val = match_adid.group(1) if match_adid else str(ad_id)

        match_token = re.search(r'id=["\']watch_token["\']\s+value=["\']([^"\']+)["\']', html, re.IGNORECASE) or re.search(r'name=["\']token["\']\s+value=["\']([^"\']+)["\']', html, re.IGNORECASE)
        token = match_token.group(1) if match_token else ""

        match_sitekey = re.search(r"sitekey:\s*\'([^\']+)\'", html)
        sitekey = match_sitekey.group(1) if match_sitekey else "0x4AAAAAACLoyBgrDeh_Bv0q"

        if not token:
            failed_video_ads.add(str(ad_id))
            return False

        for s in range(duration, 0, -1):
            msg(f"{C_YELLOW}⏳ VIDEO {ad_id}: Watching {s}s...{C_RESET}")
            time.sleep(1)
        print()

        cf_token = solve_turnstile(sitekey, page_url)
        if not cf_token:
            msg(f"{C_RED}✖ VIDEO {ad_id}: Captcha error{C_RESET}", is_final=True)
            failed_video_ads.add(str(ad_id))
            return False

        post_url = "https://minitasky.com/ajax_verify_video"

        multipart_data = {
            "ad_id": (None, str(ad_id_val)),
            "token": (None, token),
            "cf-turnstile-response": (None, cf_token),
            "website": (None, ""),
            "email_confirm": (None, ""),
            "url_field": (None, ""),
            "ghost_btn_te": (None, ""),
        }

        post_res = session.post(post_url, files=multipart_data, headers={
            "Referer": page_url,
            "Origin": "https://minitasky.com",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": saved_cookie,
            "User-Agent": saved_user_agent,
        })

        failed_video_ads.add(str(ad_id))

        rew = extract_reward_from_response(post_res, default_reward="0.00010")
        msg(f"{C_GREEN}{C_BOLD}✅️ SUKSES - {rew}{C_RESET}", is_final=True)
        return True

    def run_video_task():
        msg(f"{C_YELLOW}🔍 VIDEO: Scanning list...{C_RESET}", is_final=True)
        try:
            res = session.get("https://minitasky.com/earn_video", headers={
                "Referer": "https://minitasky.com/dashboard",
                "User-Agent": saved_user_agent,
                "Cookie": saved_cookie,
            })
            html = res.text

            if "Please login first" in html or "login" in res.url:
                msg(f"{C_RED}[!] Sesi / Cookie Minitasky kedaluarsa!{C_RESET}", is_final=True)
                return False

            matches = re.findall(r'href=["\'](?:watch_video\.php|watch_video)\?id=(\d+)["\']', html, re.IGNORECASE)
            ids = [m for m in matches if m not in failed_video_ads]
            ids = list(dict.fromkeys(ids))

            if not ids:
                msg(f"{C_YELLOW}ℹ VIDEO: No videos available{C_RESET}", is_final=True)
                return False

            for ad_id in ids:
                watch_single_video(ad_id)
                time.sleep(2)
            return True
        except Exception:
            return False

    def run_faucet_loop():
        url = "https://minitasky.com/faucet"
        sitekey = "0x4AAAAAACLoyBgrDeh_Bv0q"

        for attempt_faucet in range(1, 3):
            msg(f"{C_BLUE}🚰 Faucet: Memuat ulang halaman ({attempt_faucet})...{C_RESET}", is_final=True)
            check_api()

            res = None
            max_net_retries = 3
            for net_attempt in range(1, max_net_retries + 1):
                try:
                    res = session.get(url, timeout=15)
                    break
                except requests.exceptions.RequestException:
                    if net_attempt == max_net_retries:
                        msg(f"{C_RED}✖ Gagal memuat halaman faucet setelah {max_net_retries} kali percobaan.{C_RESET}", is_final=True)
                        return False
                    msg(f"{C_YELLOW}⚠ Koneksi terputus, mencoba ulang muat halaman faucet ({net_attempt}/{max_net_retries})...{C_RESET}")
                    time.sleep(3)

            if not res:
                return False

            html = res.text

            if "Faucet Locked" in html or ("Watch" in html and "PTC Ads" in html):
                msg(f"{C_RED}✖ FAUCET: Terkunci atau butuh nonton PTC Ads terlebih dahulu.{C_RESET}", is_final=True)
                return False

            last_step_token = ""
            shared_step_token = ""
            failed_steps = False

            for current_step in range(1, 4):
                match_ts = re.search(r'name=["\']step_ts_token["\']\s+value=["\']([^"\']*)["\']', html, re.IGNORECASE)
                if match_ts:
                    last_step_token = match_ts.group(1)

                if current_step == 1:
                    msg(f"{C_YELLOW}⚡ Solver: Meminta token Turnstile untuk Step 1...{C_RESET}", is_final=True)
                    shared_step_token = solve_turnstile(sitekey, url)
                    if not shared_step_token:
                        failed_steps = True
                        break
                    last_step_token = shared_step_token
                elif shared_step_token:
                    last_step_token = shared_step_token

                for s in range(11, 0, -1):
                    msg(f"{C_YELLOW}⏳ Faucet (Step {current_step}/3): Waiting {s}s...{C_RESET}")
                    time.sleep(1)

                msg(f"{C_BLUE}🔄 Faucet: Submitting Step {current_step}/3...{C_RESET}", is_final=True)
                step_payload = {"next_step": str(current_step), "step_ts_token": last_step_token}
                res = session.post(url, data=step_payload, headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": url,
                    "Origin": "https://minitasky.com",
                })
                html = res.text
                match_next_ts = re.search(r'name=["\']step_ts_token["\']\s+value=["\']([^"\']*)["\']', html, re.IGNORECASE)
                if match_next_ts and match_next_ts.group(1):
                    last_step_token = match_next_ts.group(1)
                time.sleep(2)

            if failed_steps:
                continue

            res_final = session.get(url)
            html = res_final.text
            match_token = re.search(r'name="claim_token"\s+(?:id="form_claim_token"\s+)?value="([^"]+)"', html)
            if not match_token:
                continue
            claim_token = match_token.group(1)
            match_key = re.search(r"sitekey:\s*\'([^\']+)\'", html)
            if match_key:
                sitekey = match_key.group(1)

            cf_token = solve_turnstile(sitekey, url)
            if not cf_token:
                continue

            post_data = {
                "claim_faucet": "1",
                "claim_token": claim_token,
                "step_ts_token": last_step_token,
                "website_url_trap": "",
                "cf-turnstile-response": cf_token,
            }

            msg(f"{C_BLUE}🎁 Faucet: Submitting final claim...{C_RESET}", is_final=True)

            max_retries = 3
            post_res = None
            for attempt_rc in range(1, max_retries + 1):
                try:
                    post_res = session.post(url, data=post_data, headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": url,
                        "Origin": "https://minitasky.com",
                    }, timeout=15)
                    break
                except requests.exceptions.RequestException:
                    if attempt_rc == max_retries:
                        msg(f"{C_RED}✖ Gagal terhubung ke server setelah {max_retries} kali percobaan.{C_RESET}", is_final=True)
                        return False
                    msg(f"{C_YELLOW}⚠ Koneksi terputus, mencoba ulang ({attempt_rc}/{max_retries})...{C_RESET}")
                    time.sleep(3)

            rew = extract_reward_from_response(post_res, default_reward="0.0006")
            msg(f"{C_GREEN}{C_BOLD}✅️ SUKSES - {rew}{C_RESET}", is_final=True)
            return True

        return False

    loop_count = 0
    try:
        while True:
            loop_count += 1
            refresh_banner()

            msg(f"{C_CYAN}🔄 [LOOP #{loop_count}] Menjalankan task...{C_RESET}", is_final=True)
            cooldown_to_wait = 15

            if sub_choice == "1":
                faucet_status = check_faucet_status()
                if faucet_status["energy"] <= 0 or faucet_status["locked"]:
                    print(f"\n{C_RED}Energy Habis!")
                    print("Kerjakan task PTC/VIDEO/SHORTLINKS untuk mendapatkan energi tambahan!")
                    input(f"Klik ENTER untuk kembali ke panel Kerja!{C_RESET}")
                elif faucet_status["time_left"] > 0:
                    cooldown_to_wait = faucet_status["time_left"]
                    msg(f"{C_YELLOW}⏳ Faucet Cooldown ({cooldown_to_wait}s). Menjalankan Tap Game...{C_RESET}", is_final=True)
                    run_tap_game()
                else:
                    run_faucet_loop()
                    run_tap_game()

            elif sub_choice == "2":
                msg(f"{C_YELLOW}🚀 Menjalankan Semua Task PTC (Iframe & Window)...{C_RESET}", is_final=True)
                while run_ptc_iframe_single() != "NO_ADS":
                    time.sleep(1)
                while run_ptc_window_single() != "NO_ADS":
                    time.sleep(1)
                msg(f"{C_GREEN}✔ Semua Task PTC Selesai!{C_RESET}", is_final=True)
                input(f"\n{C_YELLOW}Tekan Enter untuk kembali ke menu...{C_RESET}")
                return

            elif sub_choice == "3":
                while run_video_task():
                    time.sleep(2)
                msg(f"{C_GREEN}✔ Semua Task Video Selesai!{C_RESET}", is_final=True)
                input(f"\n{C_YELLOW}Tekan Enter untuk kembali ke menu...{C_RESET}")
                return

            refresh_banner()
            msg(f"{C_PURPLE}😴 Loop #{loop_count} selesai. Menunggu {cooldown_to_wait} detik...{C_RESET}", is_final=True)
            for s in range(cooldown_to_wait, 0, -1):
                msg(f"{C_YELLOW}⏳ Cooldown: {s}s...{C_RESET}")
                time.sleep(1)
            print()
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[!] Panel dihentikan. Kembali ke menu...{C_RESET}")
        time.sleep(1.5)
        return

def main():
    while True:
        config = load_config()
        print_banner()
        print(f" {C_GREEN}1.{C_RESET} Run Waryono")
        print(f" {C_GREEN}2.{C_RESET} Input Config (Full Setup)")
        print(f" {C_RED}3.{C_RESET} Reset Config")
        print("----------------------------------------------------")
        print(f" {C_YELLOW}0.{C_RESET} Exit")
        print("====================================================\n")

        choice = input(f"{C_YELLOW}Pilih menu API [0-3]: {C_WHITE}").strip()

        if choice == "1":
            active_apikey = config.get("apikey_waryono", "")
            saved_cookie = config.get("cookie", "")
            saved_ua = config.get("user_agent", "")

            while True:
                w, e, s, b = fetch_live_data(active_apikey, saved_cookie, saved_ua)
                print_banner(w, e, s, b)

                try:
                    val_e = float(e) if e != "N/A" else 1.0
                except ValueError:
                    val_e = 1.0

                if val_e <= 0:
                    print(f"{C_RED}Energy Habis!")
                    print("Kerjakan task PTC/VIDEO/SHORTLINKS untuk mendapatkan energi tambahan!")
                    input(f"Klik ENTER untuk kembali ke panel Kerja!{C_RESET}")

                print(f" {C_GREEN}1.{C_RESET} Faucet & Taptap")
                print(f" {C_GREEN}2.{C_RESET} All PTC (Window & Iframe)")
                print(f" {C_GREEN}3.{C_RESET} Video Task")
                print("----------------------------------------------------")
                print(f" {C_YELLOW}0.{C_RESET} Back to Main Menu")
                print("====================================================\n")

                sub_choice = input(f"{C_YELLOW}Pilih panel kerja [0-3]: {C_WHITE}").strip()
                if sub_choice == "0":
                    break
                elif sub_choice in ("1", "2", "3"):
                    bot_working_panel(sub_choice)
                else:
                    print(f"{C_RED}Pilihan tidak valid!{C_RESET}")
                    time.sleep(1)

        elif choice == "2":
            input_config_menu()
        elif choice == "3":
            reset_config()
        elif choice == "0":
            clear_screen()
            print(f"{C_CYAN}Terima kasih telah menggunakan bot, Kapten Caplung! Sampai jumpa.{C_RESET}\n")
            sys.exit(0)
        else:
            print(f"{C_RED}Pilihan tidak valid!{C_RESET}")
            time.sleep(1.5)

if __name__ == "__main__":
    main()

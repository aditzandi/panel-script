#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nocid.fun — Faucet + Exploration + PTC + Smart
Engine: SOUU ENGINE v2.1
By Dev MoneyMaker_w
"""

import os
import sys
import re
import json
import time
import random
import threading
import signal
from urllib.parse import urljoin, urlencode, quote

try:
    import requests
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    print("Install dulu: pip install requests")
    sys.exit(1)

# ═══════════════════ NEON COLORS ═══════════════════
def _c(n): return f"\033[38;5;{n}m"

RED    = _c(196)
GRN    = _c(46)
YEL    = _c(226)
BLU    = _c(39)
MAG    = _c(201)
CYN    = _c(51)
WHT    = _c(231)
AQUA   = _c(87)
ORG    = _c(208)
PINK   = _c(207)
PURPLE = _c(129)
GRAY   = _c(245)

RST = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CLR = "\r\x1b[2K"

# ═══════════════════ CONFIG ═══════════════════
host       = "https://nocid.fun"
solver_in  = "https://api.waryono.my.id/in.php"
solver_res = "https://api.waryono.my.id/res.php"

DEFAULT_SITEKEY = "0x4AAAAAAFM9xBJmJP4fWnqp"
DEFAULT_UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36")

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config_nocid.json")
COOKIE_FILE = os.path.join(BASE_DIR, "cookies_nocid.json")

SEP = "=" * 62
SEP_LINE = "-" * 62

ERROR_LABELS = {
    'ERROR_CAPTCHA_UNSOLVABLE': 'Captcha unsolvable',
    'ERROR_CAPTCHA_TIMEOUT': 'Captcha timeout',
    'ERROR_ZERO_BALANCE': 'Waryono balance habis',
    'ERROR_WRONG_USER_KEY': 'Waryono apikey salah',
    'ERROR_KEY_DOES_NOT_EXIST': 'Waryono apikey tidak ditemukan',
    'ERROR_RATE_LIMIT': 'Rate limit',
    'ERROR_NO_SLOT_AVAILABLE': 'Slot penuh',
    'ERROR_SOLVER_OFFLINE': 'Solver offline',
    'ERROR_INTERNAL_SERVER': 'Server error',
}

STOP_SIGNAL = False
API_KEY = ''

# ═══════════════════ SESSION ═══════════════════
SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': DEFAULT_UA,
    'Accept-Encoding': 'gzip, deflate',
})
SESSION.verify = False


def save_cookies():
    try:
        data = []
        for c in SESSION.cookies:
            data.append({
                'name': c.name,
                'value': c.value,
                'domain': c.domain or '',
                'path': c.path or '/',
            })
        with open(COOKIE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def load_cookies():
    if not os.path.exists(COOKIE_FILE):
        return
    try:
        with open(COOKIE_FILE) as f:
            data = json.load(f)
        for c in data:
            try:
                SESSION.cookies.set(
                    c['name'], c['value'],
                    domain=c.get('domain', ''),
                    path=c.get('path', '/'),
                )
            except Exception:
                pass
    except Exception:
        pass


load_cookies()

# ═══════════════════ UTILS ═══════════════════
def now():
    return time.strftime('%H:%M:%S')


def clear():
    os.system('clear' if os.name == 'posix' else 'cls')


def ts():
    return f"{GRAY}[{now()}]{RST}"


def log(tag, msg, detail="", color=CYN):
    tag_str = f"{color}[{tag:<6}]{RST}"
    if detail:
        sys.stdout.write(f"{ts()} {tag_str} {msg} {GRAY}| {detail}{RST}\n")
    else:
        sys.stdout.write(f"{ts()} {tag_str} {msg}\n")
    sys.stdout.flush()


def print_sep():
    print(f"{CYN}{SEP}{RST}")


def print_sep_line():
    print(f"{CYN}{SEP_LINE}{RST}")


def print_banner_main():
    print(f"{CYN}{SEP}{RST}")
    print(f"{BOLD}{GRN}{'SOUU ENGINE | AUTO SMART':^62}{RST}")
    print(f"{CYN}{SEP}{RST}")


def format_cd(seconds):
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}m {s:02d}s remaining"


def print_cycle_summary(faucet_claims, ptc_ok, ptc_fail,
                        faucet_reward, ptc_reward,
                        caving_status=""):
    print_sep_line()
    print(f"{BOLD}{MAG}{'CYCLE SUMMARY':^62}{RST}")
    print_sep_line()
    print(f"{CYN}[FAUCET] Claims  : {GRN}{faucet_claims}{RST}")
    if caving_status:
        print(f"{CYN}[CAVING] Status  : {WHT}{caving_status}{RST}")
    print(f"{CYN}[PTC   ] Success : {GRN}{ptc_ok}{RST} {GRAY}|{RST} "
          f"{RED}Failed: {ptc_fail}{RST}")
    print(f"{CYN}[REWARD] Faucet  : {GRN}+{faucet_reward} NCDT{RST}")
    print(f"{CYN}[REWARD] PTC     : {GRN}+{ptc_reward} NCDT{RST}")
    print(f"{CYN}[REWARD] Total   : {BOLD}{GRN}+{faucet_reward + ptc_reward} NCDT{RST}")
    print(f"{CYN}{SEP}{RST}")


# ═══════════════════ PROGRESS BAR ═══════════════════
def timer(seconds, label=""):
    wait = int(seconds)
    if wait <= 0:
        return
    width = 20
    start = time.time()
    while True:
        if STOP_SIGNAL:
            break
        elapsed = int(time.time() - start)
        remaining = max(0, wait - elapsed)
        pct = int((elapsed / wait) * 100) if wait else 100
        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        tf = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

        filled = int(width * pct / 100)
        bar = "█" * filled + "░" * (width - filled)

        sys.stdout.write(
            f"{CLR}    {CYN}{label} {RST}"
            f"[{GRN}{bar}{RST}] {YEL}{pct:>3}%{RST} {WHT}{tf}{RST}"
        )
        sys.stdout.flush()

        if remaining <= 0:
            break
        time.sleep(0.2)

    sys.stdout.write(CLR + " " * 80 + CLR)
    sys.stdout.flush()


# ═══════════════════ CONFIG ═══════════════════
def get_config():
    if not os.path.exists(CONFIG_FILE):
        clear()
        print(f"{CYN}{SEP}{RST}")
        print(f"{BOLD}{YEL}{'SETUP CONFIG':^62}{RST}")
        print(f"{CYN}{SEP}{RST}")
        print(f"{CYN}│ {YEL}Email / Username : {WHT}", end="")
        email = input().strip()
        print(f"{CYN}│ {YEL}Password         : {WHT}", end="")
        password = input().strip()
        print(f"{CYN}│ {YEL}API Key (Waryono) : {WHT}", end="")
        apikey = input().strip()
        print(f"{CYN}│ {YEL}User-Agent (Enter) : {WHT}", end="")
        ua = input().strip() or DEFAULT_UA
        print_sep()

        cfg = {
            "email": email,
            "password": password,
            "apikey": apikey,
            "user_agent": ua,
        }
        save_config(cfg)
        print(f"{GRN}✓ Config disimpan -> {CONFIG_FILE}{RST}")
        time.sleep(2)
        return cfg

    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        if not cfg.get('user_agent'):
            cfg['user_agent'] = DEFAULT_UA
        return cfg
    except Exception:
        return {"email": "", "password": "", "apikey": "",
                "user_agent": DEFAULT_UA}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ═══════════════════ HTTP ═══════════════════
def build_headers(ua, referer='', ajax=False):
    h = {
        'User-Agent': ua,
        'Accept-Language': 'en-US,en;q=0.9',
        'Upgrade-Insecure-Requests': '1',
    }
    if ajax:
        h['Accept'] = 'application/json'
        h['X-Requested-With'] = 'XMLHttpRequest'
    else:
        h['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    if referer:
        h['Referer'] = referer
    return h


def request(method, url, headers=None, body=None, follow_redirect=True, timeout=45):
    h = dict(headers) if headers else {}
    try:
        if body is not None:
            resp = SESSION.request(method, url, headers=h, data=body,
                                   allow_redirects=follow_redirect, timeout=timeout)
        else:
            resp = SESSION.request(method, url, headers=h,
                                   allow_redirects=follow_redirect, timeout=timeout)
        return {
            'status': resp.status_code,
            'headers': dict(resp.headers),
            'body': resp.text,
            'url': resp.url,
            'location': resp.headers.get('location', ''),
        }
    except Exception as e:
        return {'status': 0, 'headers': {}, 'body': '', 'error': str(e),
                'url': url, 'location': ''}


# ═══════════════════ SOLVER ═══════════════════
def map_error(raw):
    if not raw:
        return 'Unknown error'
    up = str(raw).upper()
    for k, v in ERROR_LABELS.items():
        if k in up:
            return v
    m = re.search(r'ERROR_[A-Z_]+', up)
    if m:
        return m.group(0)
    return str(raw)[:60]


def solve_turnstile(apikey, sitekey, domain=host):
    if not apikey:
        return {'error': 'apikey kosong'}

    payload = {
        "apikey":  apikey,
        "methods": "turnstile",
        "domain":  domain,
        "sitekey": sitekey,
        "json":    1,
    }
    try:
        r = requests.post(solver_in, json=payload, timeout=30, verify=False)
        j = r.json()
    except Exception as e:
        return {"error": f"solver_reply: {str(e)[:60]}"}

    if j.get('status') != 1:
        return {"error": map_error(j.get('request', 'unknown'))}

    task_id = j['request']
    start = time.time()

    while time.time() - start < 180:
        if STOP_SIGNAL:
            return {'error': 'stopped'}
        time.sleep(3)
        try:
            r = requests.get(solver_res,
                             params={"apikey": apikey, "action": "get",
                                     "id": task_id, "json": 1},
                             timeout=15, verify=False)
            j2 = r.json()
        except Exception:
            continue

        if j2.get('status') == 1:
            return {"token": j2['request']}
        if j2.get('request') == 'CAPCHA_NOT_READY':
            continue
        return {"error": map_error(j2.get('request', 'unknown'))}

    return {"error": "TIMEOUT_SOLVE"}


# ═══════════════════ CSRF & LOGIN ═══════════════════
def extract_csrf(html):
    if not html:
        return None
    m = re.search(r'window\.__F\s*=\s*\{[^}]*?csrf\s*:\s*"([^"]+)"', html, re.I)
    if m: return m.group(1)
    m = re.search(r'<input[^>]+name="csrf"[^>]*value="([^"]+)"', html, re.I)
    if m: return m.group(1)
    m = re.search(r'"csrf"\s*:\s*"([^"]+)"', html, re.I)
    if m: return m.group(1)
    return None


def extract_sitekey(html):
    if html:
        m = re.search(r'data-sitekey="([^"]+)"', html, re.I)
        if m: return m.group(1)
        m = re.search(r'sitekey\s*[:=]\s*["\']([^"\']+)', html, re.I)
        if m: return m.group(1)
    return DEFAULT_SITEKEY


def is_logged_in(html):
    if not html:
        return False
    return ('nocid.fun/logout' in html
            or 'class="me-out"' in html
            or 'id="minePoolCard"' in html)


def get_csrf_from_anywhere(cfg):
    ua = cfg['user_agent']
    for url in [f"{host}/login", f"{host}/", f"{host}/room"]:
        r = request('GET', url, headers=build_headers(ua, f"{host}/"))
        body = r['body']
        csrf = extract_csrf(body)
        logged = is_logged_in(body)
        if csrf:
            return {'csrf': csrf, 'logged_in': logged, 'html': body, 'url': url}

        if r['status'] in (301, 302, 303, 307, 308) and r['location']:
            loc = r['location']
            if not loc.startswith('http'):
                loc = host + loc
            r2 = request('GET', loc, headers=build_headers(ua, url))
            csrf2 = extract_csrf(r2['body'])
            if csrf2:
                return {'csrf': csrf2, 'logged_in': is_logged_in(r2['body']),
                        'html': r2['body'], 'url': loc}
    return None


def do_login(cfg):
    global API_KEY
    API_KEY = cfg.get('apikey', '')

    got = get_csrf_from_anywhere(cfg)
    if not got:
        return {'error': 'Gak dapet csrf dari manapun'}

    csrf = got['csrf']
    html = got['html']
    sitekey = extract_sitekey(html)

    if got['logged_in']:
        return {'ok': True, 'csrf': csrf, 'already': True}

    log("LOGIN", "Solving turnstile...", "", YEL)
    solv = solve_turnstile(cfg['apikey'], sitekey, host)
    if 'error' in solv:
        return {'error': f"solver: {solv['error']}"}
    ts_token = solv['token']
    log("LOGIN", "Turnstile solved", "", GRN)

    post_data = urlencode({
        'csrf': csrf,
        'login': cfg['email'],
        'password': cfg['password'],
        'g-recaptcha-response': ts_token,
    })

    headers = {
        'Host': 'nocid.fun',
        'Origin': host,
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': cfg['user_agent'],
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'{host}/',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
    }

    r = request('POST', f'{host}/login', body=post_data, headers=headers,
                follow_redirect=False)
    body = r['body']

    if is_logged_in(body):
        new_csrf = extract_csrf(body)
        return {'ok': True, 'csrf': new_csrf or csrf}

    if re.search(r'"ok"\s*:\s*true', body):
        new_csrf = extract_csrf(body)
        return {'ok': True, 'csrf': new_csrf or csrf}

    if r['status'] in (301, 302, 303) and r['location']:
        loc = r['location']
        if not loc.startswith('http'):
            loc = host + loc
        if '/login' not in loc:
            return {'ok': True, 'csrf': csrf, 'redirect': loc}

    if 'nocid.fun/room' in body or 'id="minePoolCard"' in body:
        new_csrf = extract_csrf(body)
        return {'ok': True, 'csrf': new_csrf or csrf}

    m = re.search(r'"msg"\s*:\s*"([^"]+)"', body)
    if m:
        return {'error': m.group(1)}

    return {'error': 'Login gagal — respon unknown'}


def ensure_login(cfg):
    log("LOGIN", "Checking session...", "", CYN)
    res = do_login(cfg)
    if 'error' in res:
        log("LOGIN", "Failed", res['error'], RED)
        return False
    if res.get('already'):
        log("LOGIN", "Session valid", "cookie OK", GRN)
    else:
        log("LOGIN", "Login success", "", GRN)
    save_cookies()
    return True


# ═══════════════════ BALANCE ═══════════════════
def get_balance(cfg):
    r = request('GET', f'{host}/api/stats', headers={
        'User-Agent': cfg['user_agent'],
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'{host}/earn/taskwall',
    })
    try:
        j = json.loads(r['body'])
    except Exception:
        return None
    if not j.get('ok'):
        return None
    return {
        'usdt': j.get('balance', '0'),
        'ncdt': float(j.get('balance_key', 0) or 0),
        'hashrate': j.get('hashrate', '?'),
    }


def print_balance(cfg, label=""):
    b = get_balance(cfg)
    if not b:
        log("BALANCE", "Failed to fetch", "", RED)
        return None
    detail = f"USDT={b['usdt']} | Hashrate={b['hashrate']}"
    log("BALANCE", f"{GRN}{b['ncdt']:.8f} NCDT{RST}", detail, GRN)
    return b


# ═══════════════════ FAUCET ═══════════════════
def get_faucet_status(cfg):
    r = request('GET', f'{host}/earn/faucet',
                headers=build_headers(cfg['user_agent'], f'{host}/room'))
    html = r['body']
    if not is_logged_in(html):
        return {'error': 'not_logged_in'}
    m = re.search(r'var\s+left\s*=\s*(\d+)', html)
    left = int(m.group(1)) if m else 0
    return {'ready': left == 0, 'cooldown': left, 'html': html}


def do_faucet_claim(cfg):
    fa = get_faucet_status(cfg)
    if 'error' in fa:
        return {'status': fa['error'], 'msg': 'Cookie expired'}

    if not fa['ready']:
        return {'status': 'cooldown', 'wait': fa['cooldown']}

    html = fa['html']
    csrf = extract_csrf(html)
    if not csrf:
        return {'status': 'parse', 'msg': 'No csrf'}

    sitekey = extract_sitekey(html)

    log("CAPTCHA", "Faucet turnstile...", "", YEL)
    solv = solve_turnstile(cfg['apikey'], sitekey, host)
    if 'error' in solv:
        return {'status': 'solver', 'msg': solv['error']}
    log("CAPTCHA", "Solved", "", GRN)

    post_data = urlencode({
        'csrf': csrf,
        'g-recaptcha-response': solv['token'],
    })

    headers = {
        'Host': 'nocid.fun',
        'Origin': host,
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'User-Agent': cfg['user_agent'],
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'{host}/earn/faucet',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
    }

    r = request('POST', f'{host}/api/faucet', body=post_data, headers=headers)

    try:
        j = json.loads(r['body'])
    except Exception:
        return {'status': 'parse', 'msg': 'Respon bukan JSON'}

    if j.get('ok'):
        return {
            'status': 'ok',
            'reward': j.get('reward', 0),
            'next_in': int(j.get('next_in', 300)),
        }

    msg = j.get('msg', 'Unknown error')
    if 'wait' in msg.lower() or 'cooldown' in msg.lower() or j.get('next_in'):
        sec = int(j.get('next_in', 0))
        if sec <= 0:
            m = re.search(r'(\d+)', msg)
            if m:
                sec = int(m.group(1))
        if sec <= 0:
            sec = 60
        return {'status': 'cooldown', 'wait': sec}

    return {'status': 'error', 'msg': msg}


# ═══════════════════ PTC ═══════════════════
def _clean_title(t):
    if not t:
        return "?"
    t = re.sub(r'<[^>]+>', '', t)
    t = t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    t = t.replace('&quot;', '"').replace('&#039;', "'").replace('&#39;', "'")
    t = t.replace('\\/', '/').replace('\\"', '"')
    t = re.sub(r'\s+', ' ', t).strip()
    return t or "?"


def parse_ptc_tasks(html):
    tasks = []
    if not html:
        return tasks

    for chunk in html.split('<div class="witem witem--sm"'):
        skey_m = re.search(r'data-skey="([^"]+)"', chunk)
        key_m = re.search(r'data-key="([^"]+)"', chunk)
        if not skey_m or not key_m:
            continue
        skey = skey_m.group(1)
        reward = key_m.group(1)

        title = "?"
        m = re.search(r'<div class="witem-t">(.*?)</div>', chunk, re.DOTALL)
        if m:
            inner = re.sub(r'<img[^>]+>', '', m.group(1))
            title = _clean_title(inner)

        if skey.startswith('platform:'):
            ad_id = skey.split(':', 1)[1]
            sec_m = re.search(r'data-seconds="(\d+)"', chunk)
            seconds = int(sec_m.group(1)) if sec_m else 10
            tasks.append({'type': 'platform', 'id': ad_id, 'seconds': seconds,
                          'reward': reward, 'title': title})
    return tasks


def fetch_taskwall_ptc(cfg):
    r = request('GET', f'{host}/api/taskwall?type=ptc&limit=0', headers={
        'User-Agent': cfg['user_agent'],
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'{host}/earn/taskwall/all-ptc',
    })
    if r['status'] != 200:
        return []
    try:
        j = json.loads(r['body'])
    except Exception:
        return []
    if not j.get('ok'):
        return []
    return parse_ptc_tasks(j.get('html', ''))


def process_platform_ptc(task, csrf, cfg):
    ad_id = task['id']
    seconds = task['seconds']
    title = task['title'][:48]
    reward = task['reward']

    log("PTC", f"{WHT}{title}{RST}", f"{seconds}s | +{reward}", CYN)

    start_body = f"csrf={quote(csrf)}&action=start&ad={quote(ad_id)}"
    r = request('POST', f'{host}/api/ptc', body=start_body, headers={
        'Host': 'nocid.fun', 'Origin': host,
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'User-Agent': cfg['user_agent'],
        'Accept': 'application/json',
        'X-Requested-With': 'fetch',
        'Referer': f'{host}/earn/taskwall/all-ptc',
    })

    try:
        j = json.loads(r['body'])
    except Exception:
        log("PTC", "Start parse fail", "", RED)
        return False

    if not j.get('ok'):
        log("PTC", "Start failed", j.get('msg', ''), RED)
        return False

    ad_url = j.get('url')
    if ad_url:
        try:
            requests.get(ad_url, headers={'User-Agent': cfg['user_agent']},
                         timeout=10, verify=False)
        except Exception:
            pass

    timer(seconds + 2, "PTC view ")

    if STOP_SIGNAL:
        return False

    log("CAPTCHA", "PTC turnstile...", "", YEL)
    solv = solve_turnstile(cfg['apikey'], DEFAULT_SITEKEY, host)
    if 'error' in solv:
        log("CAPTCHA", "Failed", solv['error'], RED)
        return False
    log("CAPTCHA", "Solved", "", GRN)

    claim_body = (f"csrf={quote(csrf)}&action=claim&ad={quote(ad_id)}"
                  f"&g-recaptcha-response={quote(solv['token'])}")
    r = request('POST', f'{host}/api/ptc', body=claim_body, headers={
        'Host': 'nocid.fun', 'Origin': host,
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'User-Agent': cfg['user_agent'],
        'Accept': 'application/json',
        'X-Requested-With': 'fetch',
        'Referer': f'{host}/earn/taskwall/all-ptc',
    })

    try:
        j = json.loads(r['body'])
    except Exception:
        log("PTC", "Claim parse fail", "", RED)
        return False

    if j.get('ok'):
        r2 = j.get('reward', reward)
        log("CLAIM", f"SUCCESS | +{r2} NCDT", f"{title[:25]}", GRN)
        return True

    log("CLAIM", "FAILED", j.get('msg', ''), RED)
    return False


# ═══════════════════ EXPLORATION (CAVING) ═══════════════════
def parse_caving_state(html_text):
    heroes = []
    m_h = re.search(r'data-heroes="([^"]+)"', html_text)
    if m_h:
        try:
            import html as html_lib
            heroes = json.loads(html_lib.unescape(m_h.group(1)))
        except Exception:
            pass

    active_runs = []
    slot_matches = re.finditer(r'<div[^>]*class="[^"]*cv-slot[^"]*"([^>]*)>', html_text)
    for sm in slot_matches:
        attrs = sm.group(1)
        run_id = re.search(r'data-cv-run="([^"]+)"', attrs)
        left = re.search(r'data-left="([^"]+)"', attrs)
        total = re.search(r'data-total="([^"]+)"', attrs)
        cave = re.search(r'data-cave="([^"]+)"', attrs)
        if run_id:
            active_runs.append({
                'run_id': run_id.group(1),
                'left': int(left.group(1)) if left and left.group(1).isdigit() else 0,
                'total': int(total.group(1)) if total and total.group(1).isdigit() else 0,
                'cave': cave.group(1) if cave else 'Unknown',
            })

    available_caves = []
    cave_matches = re.finditer(
        r'<button[^>]*data-cv-enter="([^"]+)"[^>]*data-name="([^"]+)"[^>]*data-min="([^"]+)"[^>]*data-hp="([^"]+)"',
        html_text
    )
    for cm in cave_matches:
        available_caves.append({
            'id': cm.group(1),
            'name': cm.group(2),
            'min': int(cm.group(3)),
            'hp': int(cm.group(4))
        })

    return {
        'heroes': heroes,
        'active_runs': active_runs,
        'caves': available_caves
    }


def fetch_caving_state(csrf, cfg, tab="caves"):
    headers = build_headers(cfg.get('ua', DEFAULT_UA),
                            referer=f'{host}/exploration', ajax=True)
    headers.update({
        'Accept': 'application/json',
        'X-Requested-With': 'fetch',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': host
    })
    body = urlencode({'act': 'state', 'csrf': csrf, 'tab': tab})
    r = request('POST', f'{host}/api/caving', headers=headers, body=body)
    try:
        j = json.loads(r['body'])
        return j
    except Exception:
        return {'ok': False, 'msg': 'Failed to parse caving state'}


def do_caving_claim(run_id, csrf, cfg):
    headers = build_headers(cfg.get('ua', DEFAULT_UA),
                            referer=f'{host}/exploration', ajax=True)
    headers.update({
        'Accept': 'application/json',
        'X-Requested-With': 'fetch',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': host
    })
    body = urlencode({'act': 'claim', 'run': run_id, 'csrf': csrf, 'tab': 'caves'})
    r = request('POST', f'{host}/api/caving', headers=headers, body=body)
    try:
        j = json.loads(r['body'])
        return j
    except Exception:
        return {'ok': False, 'msg': 'Failed to parse claim response'}


def do_caving_start(hero_id, cave_id, hp_cost, csrf, cfg):
    headers = build_headers(cfg.get('ua', DEFAULT_UA),
                            referer=f'{host}/exploration', ajax=True)
    headers.update({
        'Accept': 'application/json',
        'X-Requested-With': 'fetch',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': host
    })
    body = urlencode({
        'act': 'start',
        'hero': hero_id,
        'cave': cave_id,
        'double': '0',
        'hp': hp_cost,
        'csrf': csrf,
        'tab': 'caves'
    })
    r = request('POST', f'{host}/api/caving', headers=headers, body=body)
    try:
        j = json.loads(r['body'])
        return j
    except Exception:
        return {'ok': False, 'msg': 'Failed to parse start response'}


def process_caving_round(csrf, cfg):
    """
    Menjalankan 1 putaran pengecekan caving (exploration):
    1. Cek state: claim ekspedisi yang sudah selesai (left <= 0).
    2. Kirim explorer yang idle/ready ke cave yang sesuai HP-nya.
    Returns:
      {
         'claimed': int,
         'started': int,
         'min_left': int or None,
         'log_msg': str
      }
    """
    res = {'claimed': 0, 'started': 0, 'min_left': None, 'log_msg': ''}

    st_resp = fetch_caving_state(csrf, cfg)
    if not st_resp.get('ok') or 'html' not in st_resp:
        res['log_msg'] = st_resp.get('msg', 'Failed to fetch caving state')
        return res

    state = parse_caving_state(st_resp['html'])

    # 1. Pengecekan Claim untuk ekspedisi aktif yang sudah selesai
    for run in state['active_runs']:
        if run['left'] <= 0:
            log("CAVING", "CLAIMING...", f"Run {run['run_id']} ({run['cave']})", YEL)
            cl_resp = do_caving_claim(run['run_id'], csrf, cfg)
            if cl_resp.get('ok'):
                res['claimed'] += 1
                loot_list = cl_resp.get('loot', [])
                if loot_list:
                    loot_str = ", ".join([f"{l.get('name', 'Item')}x{l.get('qty', 1)}" for l in loot_list])
                    log("CAVING", f"{GRN}CLAIMED{RST}", loot_str, GRN)
                else:
                    log("CAVING", f"{GRN}CLAIMED{RST}", cl_resp.get('msg', 'Rewards collected'), GRN)
            else:
                log("CAVING", "Claim fail", cl_resp.get('msg', ''), RED)
        else:
            if res['min_left'] is None or run['left'] < res['min_left']:
                res['min_left'] = run['left']

    # Jika baru saja claim, perbarui state agar hero status kembali idle
    if res['claimed'] > 0:
        time.sleep(1)
        st_resp = fetch_caving_state(csrf, cfg)
        if st_resp.get('ok') and 'html' in st_resp:
            state = parse_caving_state(st_resp['html'])

    # 2. Kirim explorer yang siap/idle
    heroes = state.get('heroes', [])
    caves = state.get('caves', [])

    # Urutkan cave dari yang membutuhkan HP terkecil ke terbesar
    caves.sort(key=lambda x: x['hp'])

    for h in heroes:
        uhid = h.get('uhid')
        name = h.get('name', 'Explorer')
        hp = h.get('hp', 0)
        busy = h.get('busy', '')

        if busy:
            log("CAVING", f"{WHT}{name}{RST}", f"Busy in {busy}", GRAY)
            continue

        # Cari cave yang cocok dengan HP explorer
        suitable_cave = None
        for c in reversed(caves):
            if hp >= c['hp']:
                suitable_cave = c
                break

        if suitable_cave:
            log("CAVING", f"Starting trip...", f"{name} -> {suitable_cave['name']}", CYN)
            start_resp = do_caving_start(uhid, suitable_cave['id'], suitable_cave['hp'], csrf, cfg)
            if start_resp.get('ok'):
                res['started'] += 1
                log("CAVING", f"{GRN}STARTED{RST}", start_resp.get('msg', f"Left for {suitable_cave['name']}"), GRN)
                trip_secs = suitable_cave['min'] * 60
                if res['min_left'] is None or trip_secs < res['min_left']:
                    res['min_left'] = trip_secs
            else:
                log("CAVING", "Start fail", start_resp.get('msg', ''), RED)
        else:
            log("CAVING", f"{WHT}{name}{RST}", f"HP {hp} (need HP or waiting regen)", YEL)

    # Cek ulang min_left dari active_runs jika ada
    for run in state['active_runs']:
        if run['left'] > 0:
            if res['min_left'] is None or run['left'] < res['min_left']:
                res['min_left'] = run['left']

    return res


def auto_caving_only(cfg):
    print_banner_main()
    if not ensure_login(cfg):
        return

    print_sep_line()
    print_balance(cfg, "start")

    cycle = 0
    total_claimed = 0
    total_started = 0

    while not STOP_SIGNAL:
        cycle += 1
        print_sep()

        got = get_csrf_from_anywhere(cfg)
        if not got:
            log("CAVING", "No csrf", "Retry in 30s", RED)
            timer(30, "Wait ")
            continue

        csrf = got['csrf']
        res = process_caving_round(csrf, cfg)
        total_claimed += res['claimed']
        total_started += res['started']

        wait = res['min_left']
        if wait is None or wait <= 0:
            wait = 60
        else:
            wait = min(wait + 5, 300)

        log("ENGINE", "WAIT", f"Next check in {format_cd(wait)}", GRAY)
        timer(wait, "Wait ")

    print_sep()
    print(f"{BOLD}{MAG}{'FINAL SUMMARY':^62}{RST}")
    print_sep()
    print(f"{CYN}Cycles    : {WHT}{cycle}{RST}")
    print(f"{CYN}Claimed   : {GRN}{total_claimed}{RST}")
    print(f"{CYN}Started   : {GRN}{total_started}{RST}")
    print_sep()
    print_balance(cfg, "final")
    print_sep()


# ═══════════════════ AUTO SMART ═══════════════════
def auto_smart(cfg):
    print_banner_main()

    if not ensure_login(cfg):
        return

    print_sep_line()
    print_balance(cfg, "start")

    cycle = 0
    total_faucet = 0
    total_caving_claim = 0
    total_caving_start = 0
    total_ptc_ok = 0
    total_ptc_fail = 0
    total_faucet_reward = 0
    total_ptc_reward = 0

    while not STOP_SIGNAL:
        cycle += 1
        print_sep()

        # ── FAUCET ──
        fa = get_faucet_status(cfg)
        faucet_ok = False
        faucet_reward = 0
        faucet_cd = 0
        faucet_ready = False

        if 'error' in fa:
            if fa['error'] == 'not_logged_in':
                log("FAUCET", "Cookie expired, re-login...", "", YEL)
                if not ensure_login(cfg):
                    timer(60, "Retry login ")
                    continue
            else:
                log("FAUCET", "Check error", fa['error'], RED)

        elif fa['ready']:
            faucet_ready = True
            log("FAUCET", f"{GRN}READY{RST}", "", GRN)
            log("CLAIM", "PROCESSING...", "", YEL)
            res = do_faucet_claim(cfg)

            if res['status'] == 'ok':
                faucet_ok = True
                faucet_reward = res.get('reward', 0)
                total_faucet += 1
                total_faucet_reward += faucet_reward
                faucet_cd = res.get('next_in', 300)
                log("CLAIM", f"{GRN}SUCCESS{RST}", f"+{faucet_reward} NCDT", GRN)

                b = get_balance(cfg)
                if b:
                    log("BALANCE", f"{GRN}{b['ncdt']:.8f} NCDT{RST}",
                        "", GRN)
            elif res['status'] == 'cooldown':
                faucet_cd = res.get('wait', 60)
                log("FAUCET", "Cooldown", format_cd(faucet_cd), YEL)
            else:
                log("FAUCET", "Claim failed", res.get('msg', ''), RED)
        else:
            faucet_cd = fa['cooldown']
            log("FAUCET", "COOLDOWN", format_cd(faucet_cd), YEL)

        # ── EXPLORATION (CAVING) ──
        caving_res = {'claimed': 0, 'started': 0, 'min_left': None}
        got_csrf = get_csrf_from_anywhere(cfg)
        if got_csrf:
            csrf = got_csrf['csrf']
            try:
                caving_res = process_caving_round(csrf, cfg)
                total_caving_claim += caving_res['claimed']
                total_caving_start += caving_res['started']
            except Exception as e:
                log("CAVING", "Error", str(e)[:50], RED)
        else:
            log("CAVING", "No csrf", "", RED)

        # ── PTC ──
        got = got_csrf or get_csrf_from_anywhere(cfg)
        ptc_ok = 0
        ptc_fail = 0
        ptc_reward_cycle = 0

        if got:
            csrf = got['csrf']
            tasks = fetch_taskwall_ptc(cfg)

            if tasks:
                print()
                print_sep_line()
                print(f"{CYN}[PTC] Available Tasks : {GRN}{len(tasks)}{RST}")
                print_sep_line()
                print()

                for i, t in enumerate(tasks, 1):
                    if STOP_SIGNAL:
                        break
                    log(f"PTC {i:02d}/{len(tasks):02d}",
                        f"{WHT}{t['title'][:48]}{RST}", "", CYN)
                    try:
                        if process_platform_ptc(t, csrf, cfg):
                            ptc_ok += 1
                            try:
                                ptc_reward_cycle += float(t['reward'])
                            except Exception:
                                pass
                        else:
                            ptc_fail += 1
                    except Exception as e:
                        log("PTC", "Error", str(e)[:50], RED)
                        ptc_fail += 1

                    if i < len(tasks):
                        print()

                total_ptc_ok += ptc_ok
                total_ptc_fail += ptc_fail
                total_ptc_reward += ptc_reward_cycle

                b = get_balance(cfg)
                if b:
                    log("BALANCE", f"{GRN}{b['ncdt']:.8f} NCDT{RST}",
                        "", GRN)
            else:
                log("PTC", "NO TASKS", "Nothing available", YEL)
        else:
            log("PTC", "No csrf", "", RED)

        # ── SUMMARY (hanya kalau ada yang dikerjain) ──
        caving_acted = caving_res['claimed'] > 0 or caving_res['started'] > 0
        did_something = faucet_ok or ptc_ok > 0 or ptc_fail > 0 or caving_acted
        if did_something:
            print()
            c_desc = []
            if caving_res['claimed'] > 0:
                c_desc.append(f"{caving_res['claimed']} claimed")
            if caving_res['started'] > 0:
                c_desc.append(f"{caving_res['started']} started")
            c_str = ", ".join(c_desc) if c_desc else "Active"
            print_cycle_summary(
                1 if faucet_ok else 0,
                ptc_ok, ptc_fail,
                faucet_reward, ptc_reward_cycle,
                caving_status=c_str
            )

        # ── WAIT LOGIC ──
        nothing_done = (not faucet_ok) and (ptc_ok == 0)

        if nothing_done:
            # Kalau gak ada PTC dan faucet cooldown → tunggu faucet ready full
            if faucet_cd > 0:
                wait = faucet_cd + 5
                log("ENGINE", "IDLE", f"Wait faucet ready: {format_cd(faucet_cd)}", GRAY)
                timer(wait, "Idle ")
            else:
                # Faucet ready tapi gagal? → tunggu 60s retry
                log("ENGINE", "IDLE", "Retry in 60s", GRAY)
                timer(60, "Idle ")
        elif not faucet_ready and ptc_ok > 0:
            # Habis PTC, faucet masih cooldown → tunggu faucet
            wait = faucet_cd + 5 if faucet_cd > 0 else 30
            log("ENGINE", "WAIT", f"Next cycle in {wait}s", GRAY)
            timer(wait, "Wait ")
        else:
            # Baru selesai faucet claim, kemungkinan ada PTC berikutnya
            wait = 15
            timer(wait, "Next cycle ")

    # Final summary
    print()
    print_sep()
    print(f"{BOLD}{MAG}{'FINAL SUMMARY':^62}{RST}")
    print_sep()
    print(f"{CYN}Cycles      : {WHT}{cycle}{RST}")
    print(f"{CYN}Faucet      : {GRN}{total_faucet} claims (+{total_faucet_reward} NCDT){RST}")
    print(f"{CYN}Caving      : {GRN}{total_caving_claim} claimed | {total_caving_start} started{RST}")
    print(f"{CYN}PTC         : {GRN}{total_ptc_ok} ok{RST} {RED}| {total_ptc_fail} fail{RST}")
    print(f"{CYN}PTC reward  : {GRN}+{total_ptc_reward} NCDT{RST}")
    print_sep()
    b = get_balance(cfg)
    if b:
        print(f"{CYN}Final NCDT  : {GRN}{b['ncdt']:.8f}{RST}")
    print_sep()


# ═══════════════════ MENU ═══════════════════
def show_banner(cfg):
    clear()
    print_sep()
    print(f"{BOLD}{GRN}{'SOUU ENGINE | AUTO SMART':^62}{RST}")
    print(f"{BOLD}{MAG}{'By Dev MoneyMaker_w':^62}{RST}")
    print_sep()
    print(f"{CYN}[SITE]{RST} nocid.fun")
    print(f"{CYN}[ENGN]{RST} Faucet + Exploration + PTC + Smart")
    print_sep()
    print(f"{CYN}[MAIL]{RST} {WHT}{cfg.get('email', '?')}{RST}")
    ak = cfg.get('apikey', '')
    ak_disp = ak[:12] + '...' if len(ak) > 15 else ak
    print(f"{CYN}[KEY ]{RST} {WHT}{ak_disp}{RST}")
    print_sep()


def show_menu(cfg):
    show_banner(cfg)
    print()
    print(f" {GRN}[1]{RST} {BOLD}{YEL}Auto Smart Bot{RST} {GRAY}(Faucet + Exploration + PTC){RST}")
    print()
    print(f" {GRN}[2]{RST} Test login")
    print(f" {GRN}[3]{RST} Edit config")
    print(f" {CYN}[C]{RST} Check Balance")
    print(f" {RED}[0]{RST} Exit")
    print_sep()
    print()


def auto_faucet_only(cfg):
    print_banner_main()
    if not ensure_login(cfg):
        return

    print_sep_line()
    print_balance(cfg, "start")

    claim = 0
    fail_streak = 0

    while not STOP_SIGNAL:
        print_sep()

        res = do_faucet_claim(cfg)
        st = res['status']

        if st == 'ok':
            claim += 1
            next_in = res.get('next_in', 600)
            log("CLAIM", f"{GRN}SUCCESS{RST}",
                f"+{res.get('reward', 0)} NCDT | Total: {claim}", GRN)
            print_balance(cfg, "after")
            fail_streak = 0
            save_cookies()
            log("ENGINE", "WAIT", f"Next claim in {next_in}s", GRAY)
            timer(next_in + 5, "Wait ")
        elif st == 'cooldown':
            log("FAUCET", "COOLDOWN", format_cd(res.get('wait', 60)), YEL)
            timer(res.get('wait', 60) + 2, "Cooldown ")
        elif st == 'not_logged_in':
            log("FAUCET", "Cookie expired", "re-login", YEL)
            if not ensure_login(cfg):
                timer(60, "Retry ")
        else:
            fail_streak += 1
            log("CLAIM", "FAILED", res.get('msg', ''), RED)
            if fail_streak >= 5:
                timer(60, "Retry ")
                fail_streak = 0
            else:
                time.sleep(5)


def auto_ptc_only(cfg):
    print_banner_main()
    if not ensure_login(cfg):
        return

    print_sep_line()
    print_balance(cfg, "start")

    cycle = 0
    total_ok = 0

    while not STOP_SIGNAL:
        cycle += 1
        print_sep()

        got = get_csrf_from_anywhere(cfg)
        if not got:
            log("PTC", "No csrf", "", RED)
            timer(30, "Retry ")
            continue
        csrf = got['csrf']

        tasks = fetch_taskwall_ptc(cfg)
        if not tasks:
            log("PTC", "NO TASKS", "Waiting 60s...", YEL)
            timer(60, "Wait ")
            continue

        print_sep_line()
        print(f"{CYN}[PTC] Available Tasks : {GRN}{len(tasks)}{RST}")
        print_sep_line()
        print()

        ok = fail = 0
        for i, t in enumerate(tasks, 1):
            if STOP_SIGNAL:
                break
            log(f"PTC {i:02d}/{len(tasks):02d}",
                f"{WHT}{t['title'][:48]}{RST}", "", CYN)
            try:
                if process_platform_ptc(t, csrf, cfg):
                    ok += 1
                else:
                    fail += 1
            except Exception as e:
                log("PTC", "Error", str(e)[:50], RED)
                fail += 1
            if i < len(tasks):
                print()

        total_ok += ok
        print_sep()
        log("CYCLE", f"{GRN}{ok} ok{RST} {RED}| {fail} fail{RST}",
            f"Total: {total_ok}", GRN)
        print_sep()
        print_balance(cfg, "after")

        log("ENGINE", "WAIT", "30s before next PTC cycle", GRAY)
        timer(30, "Wait ")

    print_sep()
    print(f"{BOLD}{MAG}{'FINAL SUMMARY':^62}{RST}")
    print_sep()
    print(f"{CYN}Cycles    : {WHT}{cycle}{RST}")
    print(f"{CYN}Total OK  : {GRN}{total_ok}{RST}")
    print_sep()
    print_balance(cfg, "final")
    print_sep()


def menu_loop():
    global STOP_SIGNAL, API_KEY

    cfg = get_config()
    API_KEY = cfg.get('apikey', '')

    while True:
        STOP_SIGNAL = False
        show_menu(cfg)
        choice = input(f" {CYN}❯ Pilih: {RST}").strip().upper()

        if choice == '0':
            print(f"\n{GRN}Bye bos.{RST}")
            sys.exit(0)

        elif choice == '1':
            auto_smart(cfg)
            input(f"{CYN}Press enter...{RST}")

        elif choice == '2':
            if ensure_login(cfg):
                print_sep_line()
                print_balance(cfg, "check")
            input(f"{CYN}Press enter...{RST}")

        elif choice == '3':
            try:
                os.unlink(CONFIG_FILE)
            except Exception:
                pass
            cfg = get_config()
            API_KEY = cfg.get('apikey', '')

        elif choice == 'C':
            if ensure_login(cfg):
                print_sep_line()
                print_balance(cfg, "check")
            input(f"{CYN}Press enter...{RST}")

        else:
            log("MENU", "Invalid choice", choice, RED)
            time.sleep(1.5)


# ═══════════════════ MAIN ═══════════════════
def main():
    def on_sigint(sig, frame):
        global STOP_SIGNAL
        if STOP_SIGNAL:
            sys.exit(0)
        STOP_SIGNAL = True
        sys.stdout.write(CLR + '\n')
        log("ENGINE", "Stopped by user", "Ctrl+C", YEL)
        time.sleep(0.3)
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, on_sigint)
    except Exception:
        pass

    menu_loop()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write(CLR)
        print(f"\n{YEL}Interrupted.{RST}")
    except Exception as e:
        sys.stdout.write(CLR)
        print(f"{RED}💥 {e}{RST}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

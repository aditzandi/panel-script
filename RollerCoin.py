#!/usr/bin/env python3
# Rollercoin bot — 24/7 Gacor Edition (Auto-Electricity, PPS Priority, Continuous Loop)
import asyncio, base64, hashlib, json, os, random, re, sys, time
import shutil
from datetime import datetime, timezone

try:
    import aiohttp
    import websockets
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ImportError as e:
    print(f"Missing dep: {e}\nInstall: pip install aiohttp websockets pycryptodome")
    sys.exit(1)

HOST = "https://rollercoin.com"
DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, "config.json")
AUTO_REFRESH_MIN = 12

N_CYAN   = "\x1b[38;5;51m"
N_PINK   = "\x1b[38;5;201m"
N_GREEN  = "\x1b[38;5;46m"
N_YELLOW = "\x1b[38;5;226m"
N_BLUE   = "\x1b[38;5;39m"
N_ORANGE = "\x1b[38;5;208m"
N_PURPLE = "\x1b[38;5;129m"
N_RED    = "\x1b[38;5;203m"
N_WHITE  = "\x1b[38;5;231m"
N_GRAY   = "\x1b[38;5;245m"
RST      = "\x1b[0m"
BOLD     = "\x1b[1m"

RED = N_RED; GRN = N_GREEN; YEL = N_YELLOW; BLU = N_BLUE
WHT = N_WHITE; ABU = N_GRAY; CYN = N_CYAN; ORG = N_ORANGE; MAG = N_PURPLE

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*m')
vlen_ = lambda s: len(ANSI_REGEX.sub("", s))

STOP = False
sleep = lambda ms: asyncio.sleep(ms / 1000)
ts = lambda: time.strftime("%H:%M:%S")
rand = lambda a, b: random.randint(a, b)
randF = lambda a, b: random.uniform(a, b)

def clear():
    sys.stdout.write("\x1b[2J\x1b[3J\x1b[H")
    sys.stdout.flush()

def fmt_num(n):
    try:
        if isinstance(n, (int, float)):
            return f"{int(n):,}"
        v = int(str(n).replace(",", "").strip() or 0)
        return f"{v:,}"
    except (TypeError, ValueError):
        return str(n)

def maskEmail(e):
    if not e or "@" not in e:
        return e or "-"
    u, d = e.split("@", 1)
    return u[:4] + "****@" + d

def genFingerprint():
    return os.urandom(16).hex()

# ═══════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════
class Dashboard:
    def __init__(self):
        self.state = {
            "email": "",
            "ua": False,
            "bearer": False,
            "profile": {"name": "-", "power": 0, "miners": 0},
            "task": {"current": "idle", "progress": 0, "total": 0, "elapsed": 0, "status": "idle"},
            "session": {"start": None, "wins": 0, "losses": 0, "earned": 0, "games": 0},
            "logs": [],
        }
        self.paused = False
        self._task = None
        self.W = 80
        self.INNER = 78

    def addLog(self, msg, tag="i"):
        icons = {"i": "»", "ok": "✓", "er": "✗", "wr": "⚠", "in": "●", "dbg": "⚙", "or": "◆"}
        colors = {"i": N_CYAN, "ok": N_GREEN, "er": N_RED, "wr": N_YELLOW,
                  "in": N_BLUE, "dbg": N_PURPLE, "or": N_ORANGE}
        self.state["logs"].append({
            "ts": ts(), "icon": icons.get(tag, "»"),
            "color": colors.get(tag, N_WHITE), "msg": str(msg)
        })
        if len(self.state["logs"]) > 250:
            self.state["logs"].pop(0)

    def set(self, updates):
        self.state.update(updates)

    def setProfile(self, p):
        self.state["profile"] = p

    def startSession(self):
        if not self.state["session"]["start"]:
            self.state["session"] = {"start": time.time(), "wins": 0, "losses": 0, "earned": 0, "games": 0}

    def bumpWin(self, reward):
        self.state["session"]["wins"] += 1
        self.state["session"]["games"] += 1
        try:
            self.state["session"]["earned"] += int(reward or 0)
        except (TypeError, ValueError):
            pass

    def bumpLoss(self):
        self.state["session"]["losses"] += 1
        self.state["session"]["games"] += 1

    def _runtime(self):
        if not self.state["session"]["start"]:
            return "00:00:00"
        s = int(time.time() - self.state["session"]["start"])
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"

    def _pulse(self):
        colors = [N_CYAN, N_BLUE, N_PURPLE, N_PINK, N_CYAN]
        return colors[int(time.time() * 2.5) % len(colors)]

    def _pad(self, s, n):
        v = vlen_(s)
        return s + " " * (n - v) if v < n else s

    def _fit(self, s, n):
        if vlen_(s) <= n:
            return s
        out, vis, i = "", 0, 0
        max_len = n - 1
        while i < len(s) and vis < max_len:
            if s[i] == "\x1b":
                end = s.find("m", i)
                if end > -1:
                    out += s[i:end + 1]
                    i = end + 1
                    continue
            out += s[i]
            vis += 1
            i += 1
        return out + "…" + RST

    def _row(self, content):
        fitted = self._fit(" " + content, self.INNER)
        padded = self._pad(fitted, self.INNER)
        return f"{N_CYAN}║{RST}{padded}{N_CYAN}║{RST}"

    def _bar(self, pct, width, color):
        filled = max(0, min(width, round(pct * width)))
        empty = width - filled
        return f"{color}{'█' * filled}{N_GRAY}{'░' * empty}{RST}"

    def render(self):
        if self.paused:
            return
        try:
            cols = shutil.get_terminal_size().columns
        except Exception:
            cols = 80
        self.W = max(min(cols, 110), 64)
        self.INNER = self.W - 2

        lines = []
        top = lambda: f"{N_CYAN}╔{'═' * self.INNER}╗{RST}"
        mid = lambda: f"{N_CYAN}╠{'═' * self.INNER}╣{RST}"
        bot = lambda: f"{N_CYAN}╚{'═' * self.INNER}╝{RST}"

        lines.append(top())
        titleTxt = "⚡ ROLLERCOIN BOT"
        titleSub = f"{N_GRAY}· 24/7 GACOR DAEMON"
        ver = f"{N_GREEN}v24.7-PRO{RST}"
        leftPart = f"{N_CYAN}{titleTxt}{RST} {titleSub}{RST}"
        gap = self.INNER - vlen_(leftPart) - vlen_(ver) - 2
        lines.append(self._row(f"{leftPart}{' ' * max(0, gap)}{ver}"))
        lines.append(mid())

        emailStat = (f"{N_GREEN}{maskEmail(self.state.get('email', ''))}{RST}"
                     if self.state.get("email") else f"{N_RED}✗ NONE{RST}")
        uaStat = f"{N_GREEN}✓ SET{RST}" if self.state["ua"] else f"{N_RED}✗ NONE{RST}"
        connStat = f"{N_GREEN}◉ 24/7 RUNNING{RST}" if self.state["profile"]["name"] != "-" else f"{N_YELLOW}○ CONNECTING{RST}"

        colW = (self.INNER - 4) // 2
        lpad = lambda v: self._pad(v, colW)

        auth_hdr = f"{N_PURPLE}┌─ AUTH {'─' * (colW - 8)}┐{RST}  {N_PURPLE}┌─ STATUS {'─' * (colW - 10)}┐{RST}"
        auth_r1  = f"{N_PURPLE}│{RST} {lpad('Email  : ' + emailStat)} {N_PURPLE}│{RST}  {N_PURPLE}│{RST} {lpad('Conn   : ' + connStat)} {N_PURPLE}│{RST}"
        auth_r2  = f"{N_PURPLE}│{RST} {lpad('UA     : ' + uaStat)} {N_PURPLE}│{RST}  {N_PURPLE}│{RST} {lpad('Mode   : PPS Priority (Direct)')} {N_PURPLE}│{RST}"
        auth_ftr = f"{N_PURPLE}└{'─' * colW}┘{RST}  {N_PURPLE}└{'─' * colW}┘{RST}"

        lines.append(self._row(auth_hdr))
        lines.append(self._row(auth_r1))
        lines.append(self._row(auth_r2))
        lines.append(self._row(auth_ftr))
        lines.append(mid())

        s = self.state["session"]
        lines.append(self._row(f"{N_BLUE}▸ SESSION STATS (24H){RST}"))
        lines.append(self._row(
            f"  {N_GRAY}Runtime{RST} : {N_YELLOW}{self._runtime()}{RST}   "
            f"{N_GRAY}Wins{RST}: {N_GREEN}{s['wins']}{RST}   "
            f"{N_GRAY}Losses{RST}: {N_RED}{s['losses']}{RST}   "
            f"{N_GRAY}Games{RST}: {N_CYAN}{s['games']}{RST}"
        ))
        lines.append(self._row(
            f"  {N_GRAY}Earned Hash Power{RST} : {N_GREEN}+{fmt_num(s['earned'])}{RST} GH/s"
        ))
        lines.append(mid())

        p = self.state["profile"]
        lines.append(self._row(f"{N_GREEN}▸ PROFILE & MINING{RST}"))
        lines.append(self._row(
            f"  {N_GRAY}User{RST}   : {N_YELLOW}{p['name']}{RST}   "
            f"{N_GRAY}Total Power{RST}: {N_CYAN}{fmt_num(p['power'])}{RST}   "
            f"{N_GRAY}Miners{RST}: {N_PINK}{fmt_num(p['miners'])}{RST}"
        ))
        lines.append(mid())

        t = self.state["task"]
        pct = min(1, t["elapsed"] / t["total"]) if t["total"] > 0 else 0
        pctPct = round(pct * 100)
        barW = max(20, self.INNER - 28)
        barColor = self._pulse() if t["status"] == "running" else N_GRAY
        bar = self._bar(pct, barW, barColor)
        icon = f"{N_GREEN}▶{RST}" if t["status"] == "running" else f"{N_GRAY}○{RST}"
        elapsedStr = f"{int(t['elapsed']) // 60:02d}:{int(t['elapsed']) % 60:02d}"
        totalStr = f"{int(t['total']) // 60:02d}:{int(t['total']) % 60:02d}"
        lines.append(self._row(f"{N_ORANGE}▸ CURRENT TASK{RST}"))
        lines.append(self._row(f"  {icon} {self._fit(t['current'], self.INNER - 6)}"))
        lines.append(self._row(f"  [{bar}] {N_YELLOW}{pctPct:>3}%{RST}  {N_GRAY}{elapsedStr}/{totalStr}{RST}"))
        lines.append(mid())

        reserved = len(lines) + 3
        try:
            termRows = shutil.get_terminal_size().lines
        except Exception:
            termRows = 40
        logCount = max(4, min(10, termRows - reserved - 2))
        recent = self.state["logs"][-logCount:]

        lines.append(self._row(f"{N_PINK}▸ RECENT LOGS{RST}"))
        for i in range(logCount):
            if i >= len(recent):
                lines.append(self._row(""))
                continue
            l = recent[i]
            maxMsg = self.INNER - 18
            msg = l["msg"]
            if len(msg) > maxMsg:
                msg = msg[:maxMsg - 1] + "…"
            lines.append(self._row(f"  {N_GRAY}[{l['ts']}]{RST} {l['color']}{l['icon']}{RST} {msg}"))
        lines.append(bot())

        sys.stdout.write("\x1b[H" + "\n".join(lines) + "\x1b[0J")
        sys.stdout.flush()

    async def _render_loop(self):
        try:
            while not self.paused:
                try:
                    self.render()
                except Exception:
                    pass
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            pass

    def start(self):
        if self._task:
            return
        sys.stdout.write("\x1b[2J\x1b[3J\x1b[H\x1b[?25l")
        self._task = asyncio.create_task(self._render_loop())

    def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
        sys.stdout.write("\x1b[?25h")

    def pause(self):
        self.paused = True
        self.stop()
        sys.stdout.write("\x1b[2J\x1b[3J\x1b[H\x1b[?25h")

    def resume(self):
        sys.stdout.write("\x1b[2J\x1b[3J\x1b[H")
        self.paused = False
        self.start()


dashboard = Dashboard()

# ═══════════════════════════════════════════════════════════════
#  LOG / TIMER
# ═══════════════════════════════════════════════════════════════
def log(msg, tag="i"):
    dashboard.addLog(msg, tag)

async def tmr(seconds, label="Waiting..."):
    total = int(seconds)
    if total < 1:
        return
    start = time.time()

    def update():
        elapsed = min(time.time() - start, total)
        dashboard.set({
            "task": {"current": label, "progress": elapsed / total, "total": total,
                     "elapsed": elapsed, "status": "running"}
        })

    update()
    while not STOP:
        if time.time() - start >= total:
            break
        update()
        await asyncio.sleep(0.15)
    dashboard.set({
        "task": {"current": "idle", "progress": 0, "total": 0, "elapsed": 0, "status": "idle"}
    })

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
def defaultConfig():
    return {
        "userAgent": "", "email": "", "fingerprint": "",
        "access_token": "", "refresh_token": "", "csrf_token": "",
        "hamster": True, "game": True, "merge": False, "auto_electricity": True, "auto_quests": True,
        "proxy": False, "max_level_game": 10, "win_per_level": 8,
        "time_game": 24, # 24 hours non-stop default
        "selected_games": [14, 11, 4, 2, 6, 10, 9, 12, 13, 15, 3, 5, 8, 1, 7], # Ordered by PPS priority
        "delay_loop": 30, "delay_account_switch": 10,
    }

def loadConfig():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return {**defaultConfig(), **json.load(f)}
    except Exception:
        return defaultConfig()

def saveConfig(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

async def _async_input(prompt):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt).strip())

# ═══════════════════════════════════════════════════════════════
#  ENCRYPTION
# ═══════════════════════════════════════════════════════════════
def generateConstructed(uid):
    digits = [int(c) for c in str(uid) if c.isdigit()]
    s = sum(digits)
    n = sorted(digits)
    prefix = list(str(uid)[:len(n)])
    return "".join(str(x) for x in n) + "".join(prefix) + str(s)

def encryptData(plaintext, uid):
    constructed = generateConstructed(uid)
    key = hashlib.md5(constructed.encode("utf-8")).hexdigest()
    iv = b"dYQ9R99bkKLsLHad"
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv)
    padded = pad(plaintext.encode("utf-8"), 16)
    return base64.b64encode(cipher.encrypt(padded)).decode("ascii")

# ═══════════════════════════════════════════════════════════════
#  HTTP (Direct Connection, Robust Timeouts & Auto 401 Recovery)
# ═══════════════════════════════════════════════════════════════
accessToken = ""
refreshToken = ""
csrfToken = ""
userAgent = ""
savedEmail = ""
_session = None

async def getSession():
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=25, connect=10)
        _session = aiohttp.ClientSession(timeout=timeout)
    return _session

async def api(method, endpoint, body=None, retry_auth=True):
    global accessToken
    session = await getSession()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {accessToken}",
        "csrf-token": csrfToken,
        "Referer": HOST + "/game",
        "User-Agent": userAgent,
    }
    url = f"{HOST}/{endpoint.lstrip('/')}"
    try:
        async with session.request(method, url, headers=headers, json=body) as r:
            if r.status == 401 and retry_auth:
                log("Token 401 Unauthorized → auto-refreshing...", "wr")
                refreshed = await refreshTokenFlow(quiet=True)
                if refreshed:
                    return await api(method, endpoint, body=body, retry_auth=False)
            text = await r.text()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"success": False, "error": text[:100]}
    except asyncio.TimeoutError:
        return {"success": False, "error": "HTTP Request Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}

# ═══════════════════════════════════════════════════════════════
#  EMAIL LOGIN + OTP
# ═══════════════════════════════════════════════════════════════
async def loginFetch(endpoint, body):
    session = await getSession()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": HOST,
        "Referer": HOST + "/sign-in",
    }
    if userAgent:
        headers["User-Agent"] = userAgent
    try:
        async with session.post(HOST + endpoint, headers=headers, json=body) as r:
            text = await r.text()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"success": False, "error": text[:120]}
    except Exception as e:
        return {"success": False, "error": str(e)[:120]}

async def emailLogin():
    global userAgent, accessToken, refreshToken, savedEmail, csrfToken

    cfg = loadConfig()
    userAgent = cfg.get("userAgent", "") or ""
    if not userAgent:
        userAgent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        cfg["userAgent"] = userAgent
        saveConfig(cfg)

    dashboard.pause()
    clear()
    print(f"{WHT}  📧 Login Email + OTP{RST}")
    print(f"{WHT}  ───────────────────{RST}\n")

    cur = maskEmail(cfg.get("email", "")) if cfg.get("email") else "not set"
    clr = GRN if cfg.get("email") else RED
    print(f"  {CYN}◉{RST} {ABU}Current email{RST} : {clr}{cur}{RST}\n")

    inp = await _async_input(f"  {YEL}▸{RST} {WHT}Email{RST} : ")
    email = inp or cfg.get("email", "")
    if not email or "@" not in email:
        log("Invalid email. Cancelled.", "wr")
        await asyncio.sleep(1.2)
        return False

    if not cfg.get("fingerprint"):
        cfg["fingerprint"] = genFingerprint()
        saveConfig(cfg)
        log(f"Fingerprint generated: {cfg['fingerprint'][:12]}...", "dbg")

    log("Requesting OTP...", "i")
    d = await loginFetch("/api/auth/email-auth", {
        "mail": email,
        "registrationLanguage": "en",
        "challenge": "",
        "action": "auth",
        "referrer": "",
    })
    if not d.get("success") or not d.get("data"):
        log(f"Send failed: {d.get('error', 'unknown')}", "er")
        await asyncio.sleep(2)
        return False

    user_id = d["data"].get("user_id")
    code_id = d["data"].get("confirm_code_id")
    if not user_id or not code_id:
        log("Server response missing user_id/code_id", "er")
        await asyncio.sleep(2)
        return False

    log(f"OTP sent to {maskEmail(email)} — check Inbox/Spam.", "ok")

    code = await _async_input(f"  {YEL}▸{RST} {WHT}OTP Code{RST} : ")
    if not code:
        log("Cancelled.", "wr")
        await asyncio.sleep(1.2)
        return False

    log("Verifying code...", "i")
    d2 = await loginFetch("/api/auth/validate-auth-code", {
        "user_id": user_id,
        "code_id": code_id,
        "code": code,
        "platform": "web",
    })
    if not d2.get("success") or not d2.get("data") or not d2["data"].get("access_token"):
        log(f"Invalid code: {d2.get('error', 'unknown')}", "er")
        await asyncio.sleep(2)
        return False

    cfg["email"] = email
    cfg["access_token"] = d2["data"]["access_token"]
    cfg["refresh_token"] = d2["data"].get("refresh_token", "")
    saveConfig(cfg)

    savedEmail = email
    accessToken = cfg["access_token"]
    refreshToken = cfg["refresh_token"]
    csrfToken = cfg.get("csrf_token", "")

    log("Login success! Token saved.", "ok")
    await asyncio.sleep(1.0)
    return True

# ═══════════════════════════════════════════════════════════════
#  WEBSOCKET
# ═══════════════════════════════════════════════════════════════
class WSClient:
    def __init__(self, ws):
        self.ws = ws

    async def send(self, data):
        try:
            await self.ws.send(data)
        except Exception:
            pass

    async def recv(self, timeout=45):
        try:
            msg = await asyncio.wait_for(self.ws.recv(), timeout)
        except asyncio.TimeoutError:
            return "TIMEOUT"
        if isinstance(msg, bytes):
            msg = msg.decode("utf-8", errors="replace")
        return msg

    async def close(self):
        try:
            await self.ws.close()
        except Exception:
            pass

    @property
    def open(self):
        try:
            return not self.ws.closed
        except AttributeError:
            return True

async def wsConnect(url):
    ws = await websockets.connect(url, ping_interval=20, ping_timeout=20)
    return WSClient(ws)

# ═══════════════════════════════════════════════════════════════
#  API HELPERS & TOKEN REFRESH
# ═══════════════════════════════════════════════════════════════
async def refreshTokenFlow(quiet=False):
    global accessToken, refreshToken
    if not refreshToken:
        return False
    try:
        session = await getSession()
        async with session.post(
            HOST + "/api/auth/refresh",
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": userAgent},
            json={"refresh_token": refreshToken, "platform": "web"},
            timeout=aiohttp.ClientTimeout(total=15)
        ) as r:
            data = await r.json()
            d = data.get("data", {})
            if d.get("access_token"):
                accessToken = d["access_token"]
                refreshToken = d.get("refresh_token", refreshToken)
                cfg = loadConfig()
                cfg["access_token"] = accessToken
                cfg["refresh_token"] = refreshToken
                saveConfig(cfg)
                if not quiet:
                    log("Token refreshed successfully", "ok")
                return True
    except Exception as e:
        if not quiet:
            log(f"Token refresh error: {e}", "wr")
    return False

_auto_refresh_task = None

async def _auto_refresh_loop():
    while not STOP:
        try:
            await asyncio.sleep(AUTO_REFRESH_MIN * 60)
            if not refreshToken:
                continue
            ok = await refreshTokenFlow(quiet=True)
            if ok:
                log(f"Token auto-refreshed (+{AUTO_REFRESH_MIN}m)", "dbg")
            else:
                log("Auto-refresh token failed — retrying next cycle", "wr")
        except asyncio.CancelledError:
            return
        except Exception:
            pass

def startAutoRefresh():
    global _auto_refresh_task
    if _auto_refresh_task and not _auto_refresh_task.done():
        _auto_refresh_task.cancel()
    _auto_refresh_task = asyncio.create_task(_auto_refresh_loop())

async def getProfile():
    r = await api("GET", "api/profile/user-profile-data")
    if r.get("success") and r.get("data"):
        return r["data"]
    return None

# ═══════════════════════════════════════════════════════════════
#  AUTO ELECTRICITY (BATTERY RECHARGE)
# ═══════════════════════════════════════════════════════════════
async def checkAndRechargeElectricity():
    try:
        # Check current electricity status
        res = await api("GET", "api/electricity/user-electricity")
        if res.get("success") and res.get("data"):
            cells = res.get("data", {}).get("cells", 5)
            if cells < 5:
                log(f"Electricity: {cells}/5 bars → recharging...", "wr")
                recharge = await api("POST", "api/electricity/recharge")
                if recharge.get("success"):
                    log("Electricity successfully recharged! (5/5 bars)", "ok")
                else:
                    log(f"Electricity recharge cooldown: {recharge.get('error', 'active')}", "dbg")
            else:
                log("Electricity full (5/5 bars)", "dbg")
        else:
            # Blind recharge if user-electricity endpoint unavailable
            recharge = await api("POST", "api/electricity/recharge")
            if recharge.get("success"):
                log("Electricity recharged!", "ok")
    except Exception as e:
        log(f"Electricity check: {e}", "dbg")

# ═══════════════════════════════════════════════════════════════
#  AUTO DAILY QUESTS
# ═══════════════════════════════════════════════════════════════
async def checkDailyQuests():
    try:
        res = await api("GET", "api/quests/daily-quests")
        if res.get("success") and res.get("data"):
            quests = res.get("data", {}).get("quests", [])
            claimed_any = False
            for q in quests:
                if q.get("is_completed") and not q.get("is_claimed"):
                    qid = q.get("id") or q.get("_id")
                    title = (q.get("title") or {}).get("en") or "Daily Quest"
                    claim = await api("POST", f"api/quests/claim/{qid}")
                    if claim.get("success"):
                        log(f"Quest Claimed: {title}!", "ok")
                        claimed_any = True
                    await sleep(randF(0.8, 1.5) * 1000)
            if claimed_any:
                log("Completed quests claimed successfully", "ok")
    except Exception as e:
        log(f"Quests check: {e}", "dbg")

# ═══════════════════════════════════════════════════════════════
#  HAMSTER EXPEDITIONS
# ═══════════════════════════════════════════════════════════════
async def hamster():
    log("Hamster: checking pets & expeditions...", "i")
    petsRes = await api("GET", "api/pets/user-pets?type=hamsters&skip=0&limit=20")
    if not petsRes.get("success") or not petsRes.get("data", {}).get("pets"):
        log("No hamsters active", "dbg")
        return
    pets = petsRes["data"]["pets"]
    expRes = await api("GET", "api/expeditions/list")
    expeditions = expRes.get("data", []) if expRes.get("success") else []
    expMap = {e.get("title", {}).get("en", ""): e for e in expeditions}

    userExpRes = await api("GET", "api/expeditions/user-expeditions")
    if userExpRes.get("success") and userExpRes.get("data"):
        for exp in userExpRes["data"]:
            if not exp.get("is_complited"):
                continue
            name = (exp.get("title") or exp.get("expedition_data", {}).get("title") or {}).get("en", "Unknown")
            claim = await api("POST", "api/expeditions/finish",
                              {"users_expeditions_id": exp.get("users_expeditions_id")})
            if claim.get("success"):
                xp = claim.get("data", {}).get("received_xp_amount", 0)
                log(f"Expedition claimed: {name} (+{xp} XP)", "ok")
            await sleep(randF(1.2, 2.5) * 1000)

    for pet in pets:
        title = (pet.get("title") or {}).get("en", "Hamster")
        pts = pet.get("skills_points_to_distribute", 0) or 0
        inExp = pet.get("is_in_expedition")
        level = pet.get("level", 0)
        if not inExp and pts >= 3:
            bp = pts // 3
            if bp > 0:
                up = await api("POST", "api/pets/update-charachteristics", {
                    "users_pets_id": pet.get("users_pets_id"),
                    "charachteristics": {"strength": bp, "health": bp, "luck": bp}
                })
                if up.get("success"):
                    log(f"Upgraded {title} Lv.{level} (+{bp} all stats)", "ok")
                await sleep(randF(1.0, 2.0) * 1000)
        if inExp or not pet.get("next_expedition_date"):
            continue
        try:
            expTime = datetime.fromisoformat(pet["next_expedition_date"].replace("Z", "+00:00"))
            if expTime > datetime.now(timezone.utc):
                mins = int((expTime - datetime.now(timezone.utc)).total_seconds() // 60)
                log(f"{title} cooldown {mins}m", "dbg")
                continue
        except Exception:
            pass
        sel = "Deep Forest" if level <= 15 else ("Tousland" if level <= 35 else "Snowlit Avenue")
        exp = expMap.get(sel)
        if not exp:
            continue
        start = await api("POST", "api/expeditions/start", {
            "expeditions_id": exp.get("id"),
            "users_pets_ids": [pet.get("users_pets_id")],
            "used_abilities_codes": [],
        })
        if start.get("success"):
            log(f"Expedition started: {title} → {sel}", "ok")
        await sleep(randF(1.5, 3.0) * 1000)

# ═══════════════════════════════════════════════════════════════
#  GAME DEFINITIONS & ACCURATE TIME TABLES (ALL 15 GAMES)
# ═══════════════════════════════════════════════════════════════
GAME_NAMES = {
    1: "Coin Click", 2: "Token Blaster", 3: "Flappy Rocket", 4: "Cryptonoid",
    5: "Coin Match", 6: "Crypto Hamster", 7: "2048 Coin", 8: "Coin Flip",
    9: "Dr. Hamster", 10: "Token Surfer: Snow Ride", 11: "Lambo Rider",
    12: "Hamster Climber", 13: "Coin Fisher", 14: "Mission Hampossible",
    15: "Crypto Hex",
}

REWARD_TABLE = {
    1:  {1:1200,2:1200,3:1200,4:1200,5:1440,6:1440,7:1440,8:1440,9:1680,10:1680},
    2:  {1:6552,2:7224,3:7722,4:8400,5:8961,6:9540,7:10062,8:10647,9:11232,10:14040},
    3:  {1:2376,2:2592,3:2730,4:2940,5:3150,6:3360,7:3570,8:3780,9:3990,10:4200},
    4:  {1:6768,2:6912,3:7200,4:7488,5:7632,6:7920,7:10944,8:11136,9:11520,10:11712},
    5:  {1:2160,2:2196,3:2232,4:2646,5:2688,6:2730,7:2772,8:2814,9:2856,10:3126},
    6:  {1:6090,2:6492,3:6906,4:7332,5:7770,6:8226,7:8688,8:9168,9:9654,10:10152},
    7:  {1:1008,2:1071,3:1134,4:1197,5:1260,6:1323,7:1386,8:1449,9:1512,10:1575},
    8:  {1:1152,2:1152,3:1152,4:1536,5:1608,6:1608,7:1608,8:2010,9:2010,10:2010},
    9:  {1:3012,2:3294,3:3558,4:3804,5:4026,6:4230,7:4410,8:4584,9:4734,10:4866},
    10: {1:3528,2:3822,3:4116,4:4410,5:4704,6:4998,7:5292,8:5586,9:5880,10:6174},
    11: {1:6528,2:6975,3:7425,4:7872,5:8319,6:8769,7:9216,8:9663,9:10113,10:10560},
    12: {1:2550,2:2970,3:3330,4:3720,5:4080,6:4470,7:4860,8:5250,9:5640,10:6000},
    13: {1:2550,2:2970,3:3330,4:3720,5:4080,6:4470,7:4860,8:5250,9:5640,10:6000},
    14: {1:7000,2:8000,3:9000,4:10000,5:11000,6:12000,7:13000,8:14000,9:15000,10:16000},
    15: {1:2550,2:2970,3:3330,4:3720,5:4080,6:4470,7:4860,8:5250,9:5640,10:6000},
}

# Accurate human-like base completion duration per level for ALL games
TIME_TABLE = {
    1:  {1:28, 2:28, 3:28, 4:28, 5:28, 6:28, 7:28, 8:28, 9:28, 10:28},
    2:  {1:34, 2:35, 3:36, 4:38, 5:40, 6:42, 7:42, 8:43, 9:44, 10:45},
    3:  {1:30, 2:32, 3:34, 4:36, 5:38, 6:40, 7:42, 8:44, 9:45, 10:45},
    4:  {1:36, 2:38, 3:40, 4:42, 5:44, 6:46, 7:48, 8:48, 9:50, 10:52},
    5:  {1:28, 2:30, 3:32, 4:34, 5:36, 6:38, 7:40, 8:40, 9:42, 10:44},
    6:  {1:32, 2:34, 3:36, 4:38, 5:40, 6:42, 7:44, 8:45, 9:46, 10:48},
    7:  {1:35, 2:36, 3:38, 4:40, 5:42, 6:44, 7:45, 8:46, 9:48, 10:50},
    8:  {1:22, 2:24, 3:25, 4:26, 5:28, 6:28, 7:30, 8:30, 9:32, 10:32},
    9:  {1:32, 2:34, 3:36, 4:38, 5:40, 6:42, 7:44, 8:45, 9:46, 10:48},
    10: {1:32, 2:34, 3:36, 4:38, 5:40, 6:42, 7:44, 8:45, 9:46, 10:48},
    11: {1:32, 2:34, 3:36, 4:38, 5:40, 6:42, 7:44, 8:45, 9:46, 10:48},
    12: {1:28, 2:30, 3:32, 4:34, 5:36, 6:38, 7:40, 8:42, 9:44, 10:45},
    13: {1:35, 2:32, 3:30, 4:28, 5:25, 6:25, 7:25, 8:25, 9:25, 10:25},
    14: {1:38, 2:38, 3:35, 4:35, 5:32, 6:32, 7:30, 8:30, 9:28, 10:28},
    15: {1:30, 2:34, 3:38, 4:42, 5:46, 6:50, 7:54, 8:58, 9:62, 10:68},
}

def calculatePPS(gnum, lvl):
    reward = REWARD_TABLE.get(gnum, {}).get(lvl, 1000)
    dur = TIME_TABLE.get(gnum, {}).get(lvl, 35)
    return reward / max(dur, 1)

gnumRef = {"v": None}
sessionWinsTracker = {g: {} for g in GAME_NAMES.keys()}

# ═══════════════════════════════════════════════════════════════
#  GACOR GAMEPLAY LOOP (PPS PRIORITY + SMART COOLDOWN)
# ═══════════════════════════════════════════════════════════════
async def playGameBatch(cfg, max_games=25):
    global sessionWinsTracker
    selected = list(cfg.get("selected_games", list(GAME_NAMES.keys())))
    MAX_LEVEL = cfg.get("max_level_game", 10) or 10
    WIN_PER_LEVEL = cfg.get("win_per_level", 8) or 8

    games_played = 0

    while not STOP and games_played < max_games:
        ws = None
        userId = None
        try:
            await refreshTokenFlow(quiet=True)
            ws = await wsConnect(f"wss://ws.rollercoin.com/cmd?token={accessToken}")
            timeouts = 0
            if ws.open:
                await ws.send(json.dumps({"cmd": "profile_data"}))

            while ws.open and not STOP:
                raw = await ws.recv(timeout=35)
                if raw == "TIMEOUT":
                    timeouts += 1
                    if timeouts >= 2:
                        log("WS response timeout → reconnecting...", "wr")
                        break
                    continue
                if not raw:
                    continue
                timeouts = 0

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                cmd = msg.get("cmd")
                cmdval = msg.get("cmdval")

                if cmd == "profile":
                    userId = (cmdval or {}).get("userid")
                    if ws.open:
                        await ws.send(json.dumps({"cmd": "games_data_request"}))

                elif cmd == "games_data_response":
                    games = cmdval or []
                    avail = [g for g in games
                             if g.get("game_number") in selected and g.get("cool_down", 0) == 0]

                    if not avail:
                        # Smart cooldown: Find the exact minimum cooldown among selected games
                        cds = [g.get("cool_down", 0) for g in games
                               if g.get("game_number") in selected and g.get("cool_down", 0) > 0]
                        if cds:
                            s = min(cds) + rand(2, 6) # Wait exact cooldown + human jitter
                            log(f"All selected games on cooldown → waiting {s}s", "wr")
                        else:
                            s = rand(30, 60)
                            log(f"No games available → resting {s}s", "wr")
                        await ws.close()
                        await tmr(s, "Cooldown")
                        return # Return to main daemon to check quests/electricity/hamster

                    # Filter candidates: Only pick games that can yield power
                    cands = []
                    for g in avail:
                        gnum = g.get("game_number")
                        lvl = int((g.get("level") or {}).get("level", 0))
                        w = (sessionWinsTracker.get(gnum) or {}).get(lvl, 0)
                        if lvl >= MAX_LEVEL and w >= WIN_PER_LEVEL:
                            continue
                        pps = calculatePPS(gnum, lvl)
                        cands.append({"g": g, "lvl": lvl, "w": w, "pps": pps, "gnum": gnum})

                    if not cands:
                        log("All selected games reached target level → waiting 45s", "wr")
                        await ws.close()
                        await tmr(45, "Level Reset Wait")
                        return

                    # GACOR UPGRADE: Sort primarily by PPS (Power Per Second) descending!
                    cands.sort(key=lambda x: x["pps"], reverse=True)
                    chosen = cands[0]
                    gnum = chosen["gnum"]

                    log(f"Selected: {GAME_NAMES.get(gnum, 'Game' + str(gnum))} | Lv.{chosen['lvl']} | ~{chosen['pps']:.1f} PPS", "i")

                    enc = encryptData(json.dumps({"game_number": gnum}), userId)
                    body = await api("POST", f"api/game/encode-start-game-data/{userId}", {"data": enc})

                    # Captcha / Bot Challenge check
                    body_str = str(body).lower()
                    if "captcha" in body_str or "challenge" in body_str or "cf-mitigated" in body_str:
                        log("⚠️ Captcha / Security challenge detected!", "er")
                        log("Cooldown 10 minutes to protect account...", "wr")
                        await ws.close()
                        await tmr(600, "Captcha Protection Pause")
                        return

                    if not body.get("success"):
                        log(f"Game encode start failed: {body.get('error', 'unknown')}", "er")
                        await ws.close()
                        await tmr(rand(6, 12), "Retry Wait")
                        break

                    if ws.open:
                        await ws.send(json.dumps({"cmd": "game_start_request", "cmdval": body.get("data")}))

                elif cmd == "game_start_response":
                    info = cmdval or {}
                    gnum = info.get("game_number")
                    lvl = int((info.get("level") or {}).get("level", 1))
                    gnumRef["v"] = gnum

                    reward = (REWARD_TABLE.get(gnum, {}) or {}).get(lvl, 1000)
                    base_sec = (TIME_TABLE.get(gnum, {}) or {}).get(lvl, 35)

                    # Human-like play time with Gaussian distribution
                    playSec = max(18, int(random.gauss(base_sec, 2.0)))

                    # 10% chance of realistic momentary distraction (human pause)
                    if random.random() < 0.10:
                        distracted = rand(4, 12)
                        log(f"Human pause: {distracted}s", "dbg")
                        await tmr(distracted, "Human Pause")

                    await tmr(playSec, f"Playing {GAME_NAMES.get(gnum, 'Game')} Lv.{lvl} (+{reward} GH/s)")

                    # ALWAYS WIN: Never waste time on intentional loses
                    winStatus = 3
                    power = reward

                    endObj = {
                        "power": power,
                        "time": int(time.time() * 1000),
                        "user_game_id": info.get("user_game_id"),
                        "win_status": winStatus,
                    }
                    encEnd = encryptData(json.dumps(endObj), userId)
                    body = await api("POST", f"api/game/encode-data/{userId}", {"data": encEnd})

                    if not body.get("success"):
                        log(f"Encode end failed: {body.get('error', 'unknown')}", "er")
                        break
                    if not ws.open:
                        log("WS connection dropped before game end", "wr")
                        break

                    await ws.send(json.dumps({"cmd": "game_end_request", "cmdval": body.get("data")}))
                    dashboard.bumpWin(power)
                    games_played += 1
                    log(f"VICTORY: +{fmt_num(power)} GH/s claimed!", "ok")

                elif cmd == "game_finished_accepted":
                    lvl = int((cmdval.get("level") or {}).get("level", 0)) if cmdval else None
                    if lvl is not None and gnumRef["v"] is not None:
                        g = gnumRef["v"]
                        sessionWinsTracker[g] = sessionWinsTracker.get(g) or {}
                        cw = sessionWinsTracker[g].get(lvl, 0)
                        sessionWinsTracker[g][lvl] = cw + 1
                    log("Server verified score successfully", "ok")
                    break

                else:
                    if isinstance(cmd, str) and cmd.startswith("game_"):
                        log(f"[ws] {cmd}", "dbg")

        except asyncio.TimeoutError:
            log("WS timeout encountered", "wr")
        except Exception as e:
            log(f"Game error: {e}", "wr")
        finally:
            if ws:
                await ws.close()

        if STOP:
            break

        # Natural human delay between games (4 to 12s)
        await tmr(randF(4.0, 10.0), "Next Game Prep")

# ═══════════════════════════════════════════════════════════════
#  MENU
# ═══════════════════════════════════════════════════════════════
def showMenu(cfg):
    dashboard.pause()
    try:
        cols = shutil.get_terminal_size().columns
    except Exception:
        cols = 80
    W = max(min(cols, 110), 64)
    INNER = W - 2
    pad = lambda s, n: s + " " * (n - vlen_(s)) if vlen_(s) < n else s
    row = lambda c: f"{N_CYAN}║{RST}{pad(' ' + c, INNER)}{N_CYAN}║{RST}"

    lines = []
    lines.append(f"{N_CYAN}╔{'═' * INNER}╗{RST}")
    lines.append(row(f"{N_PINK}{BOLD}ROLLERCOIN 24/7 GACOR BOT{RST}  {N_GRAY}— CONTROL CENTER{RST}"))
    lines.append(f"{N_CYAN}╠{'═' * INNER}╣{RST}")

    ua = f"{N_GREEN}✓ SET{RST}" if cfg.get("userAgent") else f"{N_RED}✗ NONE{RST}"
    em = f"{N_GREEN}{maskEmail(cfg['email'])}{RST}" if cfg.get("email") else f"{N_RED}✗ NONE{RST}"

    lines.append(row(f"{N_GRAY}Site{RST}    : {N_CYAN}{HOST}{RST}"))
    lines.append(row(f"{N_GRAY}Mode{RST}    : {N_GREEN}PPS Priority Greedy (Direct Connection){RST}"))
    lines.append(row(f"{N_GRAY}UA{RST}      : {ua}"))
    lines.append(row(f"{N_GRAY}Email{RST}   : {em}"))
    lines.append(f"{N_CYAN}╠{'═' * INNER}╣{RST}")
    lines.append(row(f"{N_GREEN}[1]{RST} {N_WHITE}{BOLD}Start 24/7 Gacor Mode (Continuous Auto Loop){RST}"))
    lines.append(row(f"{N_YELLOW}[2]{RST} {N_WHITE}Login Email + OTP{RST}"))
    lines.append(row(f"{N_YELLOW}[3]{RST} {N_WHITE}Set Access Token Manual{RST}"))
    lines.append(row(f"{N_YELLOW}[4]{RST} {N_WHITE}Set User-Agent{RST}"))
    lines.append(row(f"{N_RED}[0]{RST} {N_RED}Exit{RST}"))
    lines.append(f"{N_CYAN}╚{'═' * INNER}╝{RST}")
    print("\n".join(lines))
    return input(f"  {N_YELLOW}▸{RST} {N_WHITE}Option{RST} : ").strip()

# ═══════════════════════════════════════════════════════════════
#  24/7 CONTINUOUS DAEMON ENGINE
# ═══════════════════════════════════════════════════════════════
async def runDaemon(cfg):
    global STOP
    dashboard.startSession()
    dashboard.resume()
    log("🚀 24/7 Gacor Mode aktif! Menjalankan siklus otomatis...", "ok")
    startAutoRefresh()

    cycle = 0
    while not STOP:
        cycle += 1
        log(f"━━━ SIKLUS #{cycle} DIMULAI ━━━", "i")
        try:
            # 1. Update Profile & Sync Power
            prof = await getProfile()
            if not prof and refreshToken:
                log("Token expired → auto refreshing...", "wr")
                if await refreshTokenFlow(quiet=True):
                    prof = await getProfile()

            if prof:
                power_val = prof.get("max_total_power", 0) or 0
                miners_val = prof.get("user_miners_amount", 0) or 0
                try: power_val = int(power_val)
                except Exception: power_val = 0
                try: miners_val = int(miners_val)
                except Exception: miners_val = 0

                dashboard.setProfile({
                    "name": str(prof.get("name") or prof.get("email") or "User"),
                    "power": power_val,
                    "miners": miners_val,
                })
                log(f"Akun: {prof.get('name') or prof.get('email')} | Miners: {miners_val} | Hash: {fmt_num(power_val)}", "ok")

            # 2. Cek & Isi Baterai / Listrik Otomatis
            if cfg.get("auto_electricity", True):
                await checkAndRechargeElectricity()

            # 3. Cek & Klaim Quest Harian
            if cfg.get("auto_quests", True):
                await checkDailyQuests()

            # 4. Hamster Expedition
            if cfg.get("hamster", True):
                await hamster()

            # 5. Main Game Batch Berdasarkan Prioritas PPS
            if cfg.get("game", True):
                await playGameBatch(cfg, max_games=25)

            # 6. Jeda Siklus Manusiawi (Rest 30–60s)
            if not STOP:
                rest = rand(30, 60)
                log(f"Siklus #{cycle} selesai. Rehat sejenak {rest}s...", "i")
                await tmr(rest, f"Rehat Siklus #{cycle}")

        except Exception as e:
            log(f"Kesalahan pada siklus #{cycle}: {e}", "er")
            await tmr(15, "Recovery Pause")

# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY
# ═══════════════════════════════════════════════════════════════
async def main():
    global STOP, accessToken, refreshToken, csrfToken, userAgent, _session, savedEmail

    def sigint_handler():
        global STOP
        if not STOP:
            STOP = True
            log("Menghentikan bot (menyelesaikan sesi)...", "wr")
        else:
            sys.stdout.write("\x1b[?25h")
            sys.stdout.write(f"\n{RED}Program dihentikan paksa.{RST}\n")
            sys.exit(0)

    try:
        import signal
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, sigint_handler)
    except Exception:
        pass

    cfg = loadConfig()
    if cfg.get("email"):
        savedEmail = cfg["email"]

    # Check CLI arguments for headless/daemon launch
    auto_start = "--daemon" in sys.argv or "--start" in sys.argv or "-d" in sys.argv or not sys.stdin.isatty()

    try:
        while True:
            STOP = False
            cfg = loadConfig()
            dashboard.set({
                "ua": bool(cfg.get("userAgent")),
                "bearer": bool(cfg.get("access_token")),
                "email": cfg.get("email", ""),
            })

            choice = "1" if auto_start else showMenu(cfg)
            if not choice:
                continue

            if choice == "0":
                sys.stdout.write("\x1b[?25h")
                clear()
                print(f"{RED}[!] Keluar.{RST}")
                return

            if choice == "1":
                if not cfg.get("userAgent"):
                    log("User-Agent diperlukan (menu 4)", "er")
                    await asyncio.sleep(1.5)
                    auto_start = False
                    continue

                if not cfg.get("access_token") and not cfg.get("refresh_token"):
                    log("Belum ada token — login email terlebih dahulu.", "wr")
                    await asyncio.sleep(1.2)
                    okLogin = await emailLogin()
                    if not okLogin:
                        await asyncio.sleep(1.5)
                        auto_start = False
                        continue
                    cfg = loadConfig()

                accessToken = cfg.get("access_token", "")
                refreshToken = cfg.get("refresh_token", "")
                csrfToken = cfg.get("csrf_token", "")
                userAgent = cfg.get("userAgent", "")
                if cfg.get("email"):
                    savedEmail = cfg["email"]

                # Jalankan 24/7 Daemon Loop tanpa berhenti
                await runDaemon(cfg)
                continue

            if choice == "2":
                await emailLogin()
                continue

            if choice == "3":
                dashboard.pause()
                clear()
                print(f"{WHT}{BOLD}🔑 Pengaturan Access Token{RST}")
                cur = cfg.get("access_token", "")
                cur_str = f"{N_GREEN}{cur[:30]}...{RST}" if cur else f"{N_RED}not set{RST}"
                print(f"{N_GRAY}Current:{RST} {cur_str}")
                at = await _async_input(f"\n  {N_YELLOW}▸{RST} {N_WHITE}Access Token{RST} : ")
                if at:
                    cfg["access_token"] = at
                    accessToken = at
                    rt = await _async_input(f"  {N_YELLOW}▸{RST} {N_WHITE}Refresh Token{RST} : ")
                    if rt:
                        cfg["refresh_token"] = rt
                        refreshToken = rt
                    cs = await _async_input(f"  {N_YELLOW}▸{RST} {N_WHITE}CSRF Token{RST} : ")
                    if cs:
                        cfg["csrf_token"] = cs
                        csrfToken = cs
                    saveConfig(cfg)
                    log("Tokens saved.", "ok")
                else:
                    log("Cancelled.", "wr")
                await asyncio.sleep(0.8)
                continue

            if choice == "4":
                dashboard.pause()
                clear()
                print(f"{N_WHITE}{BOLD}🛠  Pengaturan User-Agent{RST}")
                cur = cfg.get("userAgent", "")
                cur_str = f"{N_GREEN}{cur}{RST}" if cur else f"{N_RED}not set{RST}"
                print(f"{N_GRAY}Current:{RST} {cur_str}")
                ua = await _async_input(f"\n  {N_YELLOW}▸{RST} {N_WHITE}User Agent{RST} : ")
                if ua:
                    cfg["userAgent"] = ua
                    userAgent = ua
                    saveConfig(cfg)
                    log("User-Agent updated.", "ok")
                else:
                    log("Cancelled.", "wr")
                await asyncio.sleep(0.8)
                continue

            log("Pilihan tidak valid.", "er")
            await asyncio.sleep(1)
    finally:
        if _session and not _session.closed:
            await _session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.stdout.write("\x1b[?25h")
        print(f"\n{RED}Program dihentikan.{RST}")
        sys.exit(0)
    except Exception as e:
        sys.stdout.write("\x1b[?25h")
        print(f"{RED}Fatal: {e}{RST}")
        sys.exit(1)

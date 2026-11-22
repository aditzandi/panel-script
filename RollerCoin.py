#!/usr/bin/env python3
# Rollercoin bot — 24/7 Gacor Edition v2 (Smart Swap All Width, Battery Monitor, Season Pass, Parts Scan)
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
AUTO_REFRESH_MIN = 8

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
            "battery": {"pct": -1, "minutes": -1},
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
        # Battery row
        bat = self.state.get("battery", {})
        bpct = bat.get("pct", -1)
        bmin = bat.get("minutes", -1)
        if bpct >= 0:
            bc = N_GREEN if bpct > 50 else (N_YELLOW if bpct > 20 else N_RED)
            bmin_str = f" ({bmin // 60}h {bmin % 60}m sisa)" if bmin > 0 else ""
            bat_bar = self._bar(bpct / 100, 20, bc)
            lines.append(self._row(
                f"  {N_GRAY}Battery{RST}: {bc}{bpct}%{RST} [{bat_bar}]{bmin_str}"
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
        "hamster": True, "game": True, "merge": False, "auto_electricity": True,
        "auto_quests": True, "auto_miners": True, "auto_season_pass": True,
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
    global accessToken, refreshToken, userAgent
    cfg = loadConfig()
    if not refreshToken:
        refreshToken = cfg.get("refresh_token", "")
    if not accessToken:
        accessToken = cfg.get("access_token", "")
    if not userAgent:
        userAgent = cfg.get("userAgent", "")

    if not refreshToken:
        return False
    try:
        session = await getSession()
        async with session.post(
            HOST + "/api/auth/refresh",
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": userAgent, "Origin": HOST, "Referer": HOST + "/game"},
            json={"refresh_token": refreshToken, "platform": "web"},
            timeout=aiohttp.ClientTimeout(total=15)
        ) as r:
            data = await r.json()
            d = data.get("data", {})
            if d.get("access_token"):
                accessToken = d["access_token"]
                refreshToken = d.get("refresh_token", refreshToken)
                cfg["access_token"] = accessToken
                cfg["refresh_token"] = refreshToken
                saveConfig(cfg)
                if not quiet:
                    log("Token refreshed successfully", "ok")
                return True
            else:
                err = data.get("error", "unknown")
                if not quiet:
                    log(f"Token refresh failed: {err}", "wr")
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
    """Cek status baterai/listrik dan recharge jika perlu.
    Mencoba berbagai endpoint yang mungkin digunakan RollerCoin."""
    try:
        # Coba ambil data profil untuk info battery
        prof = await getProfile()
        if prof:
            # RollerCoin menyimpan info baterai di profil
            bat_pct = prof.get("battery_charge_level") or prof.get("battery") or prof.get("electricity_level")
            bat_min = prof.get("battery_minutes_left") or prof.get("electricity_minutes_left") or -1
            if bat_pct is not None:
                try:
                    bat_pct = int(bat_pct)
                    bat_min = int(bat_min) if bat_min and bat_min != -1 else -1
                    dashboard.set({"battery": {"pct": bat_pct, "minutes": bat_min}})
                    if bat_pct < 20:
                        log(f"⚠️ Baterai KRITIS: {bat_pct}%! Mencoba recharge...", "er")
                    elif bat_pct < 50:
                        log(f"Baterai: {bat_pct}% (sisa {bat_min}m)", "wr")
                    else:
                        log(f"Baterai: {bat_pct}% (sisa {bat_min}m)", "dbg")
                except (TypeError, ValueError):
                    pass

        # Coba berbagai endpoint recharge yang mungkin ada
        recharge_endpoints = [
            ("POST", "api/battery/recharge"),
            ("POST", "api/electricity/recharge"),
            ("POST", "api/game/battery/recharge"),
            ("POST", "api/user/electricity/recharge"),
        ]
        for method, ep in recharge_endpoints:
            r = await api(method, ep)
            if r.get("success"):
                log(f"✓ Baterai/Listrik berhasil di-recharge! ({ep})", "ok")
                dashboard.set({"battery": {"pct": 100, "minutes": -1}})
                return
            # Jika bukan 404 / not found (artinya endpoint benar tapi ada kondisi lain)
            err_str = str(r.get("error", "")).lower()
            if "not found" not in err_str and "404" not in err_str and r.get("error"):
                log(f"Recharge cooldown aktif: {r.get('error', '')}", "dbg")
                return  # Endpoint ditemukan, hanya cooldown
    except Exception as e:
        log(f"Electricity check: {e}", "dbg")

# ═══════════════════════════════════════════════════════════════
#  AUTO MERGE PARTS & MINERS DI FORGE
# ═══════════════════════════════════════════════════════════════
async def autoForgeMerge(interactive=False):
    """Auto-merge parts (Uncommon→Rare→Epic→Legendary) DAN miner di Forge.
    Endpoint: POST api/forge/start-crafting
    Body: {"crafting_offer_id": "...", "amount": N}
    """
    total_merges = 0
    try:
        # ── Ambil SEMUA crafting yang sudah memenuhi syarat (is_craftable=true) ──
        forge_res = await api(
            "GET",
            "api/forge/crafting-list?is_craftable=true&group=merge&limit=50"
        )
        craftings = []
        if forge_res.get("success"):
            data = forge_res.get("data") or {}
            craftings = data.get("craftings", [])

        if not craftings:
            if interactive:
                print(f"  {N_YELLOW}ℹ Belum ada resep yang memenuhi syarat merge saat ini.{RST}")
            return 0

        # Pisahkan antara Miner merge dan Part merge
        miner_crafts = []
        part_crafts = []

        for c in craftings:
            res_item = c.get("result", {})
            r_type = res_item.get("type")
            if r_type == "miners":
                miner_crafts.append(c)
            else:
                part_crafts.append(c)

        # ── 1. Eksekusi MERGE MINER Dulu (Prioritas Tertinggi!) ──────────────
        if miner_crafts:
            if interactive:
                print(f"\n  {N_GREEN}{BOLD}⚡ DITEMUKAN {len(miner_crafts)} PASANG MINER YANG SIAP DI-MERGE SEKARANG!{RST}")

            for c in miner_crafts:
                c_id = c.get("_id")
                r_name = c.get("result", {}).get("name", {})
                if isinstance(r_name, dict):
                    r_name = r_name.get("en") or "Miner"
                else:
                    r_name = str(r_name or "Miner")

                # Ambil info fee
                price_info = c.get("price_with_discount") or c.get("price") or {}
                fee_val = (price_info.get("amount", 0) or 0) / 1000000.0
                curr = price_info.get("currency", "RLT")

                if interactive:
                    print(f"  » Merging Miner: {N_YELLOW}{r_name}{RST} (Fee: {fee_val:.4f} {curr})...")

                merge_res = await api("POST", "api/forge/start-crafting", {
                    "crafting_offer_id": c_id,
                    "amount": 1
                })

                if merge_res.get("success"):
                    log(f"✓ BERHASIL MERGE: {r_name} naik level!", "ok")
                    if interactive:
                        print(f"    {N_GREEN}✓ SUKSES BESAR! {r_name} berhasil di-upgrade ke level lebih tinggi!{RST}")
                    total_merges += 1
                else:
                    err = merge_res.get("error") or merge_res.get("message") or "gagal"
                    log(f"Merge {r_name} gagal: {err}", "dbg")
                    if interactive:
                        print(f"    {N_RED}✗ Gagal merge {r_name}: {err}{RST}")
                await sleep(randF(1.5, 2.5) * 1000)

        # ── 2. Eksekusi MERGE PART (Opsional jika ada) ────────────────────────
        if part_crafts:
            if interactive:
                print(f"\n  {N_CYAN}⚒  Merge Parts (Upgrade Kualitas Part):{RST}")

            for c in part_crafts:
                c_id = c.get("_id")
                r_name = c.get("result", {}).get("name", {})
                if isinstance(r_name, dict):
                    r_name = r_name.get("en") or "Part"
                else:
                    r_name = str(r_name or "Part")

                merge_res = await api("POST", "api/forge/start-crafting", {
                    "crafting_offer_id": c_id,
                    "amount": 1
                })

                if merge_res.get("success"):
                    log(f"✓ Merge Part: {r_name} level naik!", "ok")
                    if interactive:
                        print(f"    {N_GREEN}✓ Part {r_name} berhasil di-upgrade ke rarity lebih tinggi!{RST}")
                    total_merges += 1
                await sleep(randF(1.0, 2.0) * 1000)

    except Exception as e:
        log(f"Forge merge error: {e}", "er")
        if interactive:
            print(f"  {N_RED}✗ Error Forge: {e}{RST}")

    if total_merges > 0:
        log(f"✓ Total Forge Merge: {total_merges}x!", "ok")
    return total_merges


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
#  ROOM, RACK & MINER OPTIMIZER
# ═══════════════════════════════════════════════════════════════
async def scanAndOptimizeRoom(interactive=False):
    log("Scanning Room, Racks & Inventory Miners...", "i")
    if interactive:
        print(f"  {N_CYAN}»{RST} Menghubungkan ke profil RollerCoin...")
    prof = await getProfile()
    if not prof:
        msg = "Token login sudah expired / tidak valid. Silakan pilih menu [2] Login Email + OTP terlebih dahulu!"
        log(msg, "er")
        if interactive:
            print(f"  {N_RED}✗ {msg}{RST}")
        return False
    userId = prof.get("id") or prof.get("_id")
    if not userId:
        log("User ID tidak ditemukan", "er")
        return False

    # 1. Ambil data Room & Rak yang sudah terpasang
    if interactive:
        print(f"  {N_CYAN}»{RST} Mengambil layout ruangan (Room Config)...")
    roomRes = await api("GET", f"api/game/room-config/{userId}")
    if not roomRes.get("success") or not roomRes.get("data"):
        msg = f"Gagal mengambil room config: {roomRes.get('error', 'unknown')}"
        log(msg, "er")
        if interactive:
            print(f"  {N_RED}✗ {msg}{RST}")
        return False

    roomData = roomRes.get("data", {})
    racks = roomData.get("racks", [])
    placed_miners = roomData.get("miners", [])

    info_room = f"Room: {len(racks)} Rak terpasang | {len(placed_miners)} Miner aktif di rak"
    log(info_room, "ok")
    if interactive:
        print(f"  {N_GREEN}✓{RST} {info_room}")

    # 2. Ambil data Miner di Inventory
    invRes = await api("GET", "api/game/inventory?itemType=miner&type=miner&skip=0&limit=100")
    inv_miners = (invRes.get("data") or {}).get("items", []) if invRes.get("success") else []

    # 3. Ambil data Rak di Inventory
    rackInvRes = await api("GET", "api/game/inventory?itemType=rack&type=rack&skip=0&limit=50")
    inv_racks = (rackInvRes.get("data") or {}).get("items", []) if rackInvRes.get("success") else []

    idle_count = sum(m.get("quantity", 1) or 1 for m in inv_miners)
    idle_racks_count = sum(r.get("quantity", 1) or 1 for r in inv_racks)

    # -------------------------------------------------------------
    # FITUR CERDAS: AUTO PASANG RAK KE LANTAI KAMAR JIKA ADA RAK DI INVENTORY
    # -------------------------------------------------------------
    if idle_racks_count > 0:
        rooms_list = roomData.get("rooms", [])
        # Ambil room level 0 sebagai target utama (cols 8, rows 3)
        target_room = next((rm for rm in rooms_list if (rm.get("room_info") or {}).get("level") == 0), rooms_list[0] if rooms_list else None)
        if target_room:
            u_room_id = target_room.get("_id") or target_room.get("id")
            # 12 koordinat lantai standar untuk rak di kamar 1
            std_floor_pos = [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (3, 2)]
            
            # Cek petak lantai mana yang sudah ada rak terpasang
            occupied_floor = set()
            for r in racks:
                plc = r.get("placement") or {}
                if plc.get("user_room_id") == u_room_id:
                    occupied_floor.add((plc.get("x", 0), plc.get("y", 0)))

            free_floor = [pos for pos in std_floor_pos if pos not in occupied_floor]

            if free_floor:
                log(f"Menemukan {len(free_floor)} slot lantai kosong untuk rak! Memasang rak otomatis...", "i")
                if interactive:
                    print(f"  {N_CYAN}» Ditemukan {len(free_floor)} petak lantai kamar kosong. Memasang rak dari inventory...{RST}")

                # Urutkan rak dari bonus & kapasitas tertinggi
                inv_racks_sorted = sorted(inv_racks, key=lambda r: (r.get("bonus", 0), r.get("cells", 0)), reverse=True)
                racks_to_place = []
                f_idx = 0
                for r in inv_racks_sorted:
                    rid = r.get("rack_id") or r.get("_id")
                    qty = r.get("quantity", 1) or 1
                    for _ in range(qty):
                        if f_idx < len(free_floor):
                            fx, fy = free_floor[f_idx]
                            racks_to_place.append({
                                "rack_id": rid,
                                "placement": {"room_level": 0, "user_room_id": u_room_id, "x": fx, "y": fy}
                            })
                            f_idx += 1

                if racks_to_place:
                    place_rack_res = await api("POST", "api/game/move-racks-from-inventory", {
                        "type": "custom",
                        "items": racks_to_place
                    })
                    if place_rack_res.get("success"):
                        log(f"✓ Berhasil memasang {len(racks_to_place)} rak ke lantai kamar!", "ok")
                        if interactive:
                            print(f"  {N_GREEN}✓ BERHASIL! {len(racks_to_place)} Rak sukses dipasang ke lantai kamar!{RST}")
                        
                        # Refresh data Room & Rak setelah rak terpasang
                        roomRes = await api("GET", f"api/game/room-config/{userId}")
                        roomData = roomRes.get("data", {})
                        racks = roomData.get("racks", [])
                        placed_miners = roomData.get("miners", [])
                        rackInvRes = await api("GET", "api/game/inventory?itemType=rack&type=rack&skip=0&limit=50")
                        inv_racks = (rackInvRes.get("data") or {}).get("items", []) if rackInvRes.get("success") else []
                        idle_racks_count = sum(r.get("quantity", 1) or 1 for r in inv_racks)

    info_inv = f"Inventory: {idle_count} Miner idle | {idle_racks_count} Rak tersimpan"
    log(info_inv, "i")
    if interactive:
        print(f"  {N_CYAN}ℹ{RST} {info_inv}")

    # Hitung kapasitas rak terpasang berdasarkan dimensi rak sebenarnya (width x height)
    total_slots = 0
    used_slots = 0
    for r in racks:
        r_info = r.get("rack_info") or {}
        rw = r_info.get("width", 2)
        rh = r_info.get("height", 4)
        total_slots += (rw * rh)

    for m in placed_miners:
        w = m.get("width", 1) or 1
        used_slots += w

    free_slots = max(0, total_slots - used_slots)
    info_cap = f"Kapasitas Rak: {used_slots}/{total_slots} cell terisi ({free_slots} cell kosong)"
    log(info_cap, "i" if free_slots > 0 else "ok")
    if interactive:
        print(f"  {N_YELLOW}▸{RST} {info_cap}")

    # Auto merge / craft scan
    await scanMergeMiners(interactive=interactive, inv_miners=inv_miners, placed_miners=placed_miners)

    # -------------------------------------------------------------
    # RUMUS CERDAS: EFFECTIVE POWER (RAW POWER + KONTRIBUSI BONUS %)
    # FIX: Hitung total_base_room dari SEMUA miner (room + inventory yg akan dipasang)
    #      agar bonus impact tidak = 0 saat room kosong
    # -------------------------------------------------------------
    total_base_room = sum(m.get("power", 0) for m in placed_miners)

    # Jika room kosong / sedikit miner, estimasi base dari seluruh inventory juga
    # agar effective power calculation lebih akurat
    if total_base_room == 0 and inv_miners:
        # Estimasi: semua miner inventory akan dipasang → hitung total base mereka
        total_base_room = sum(
            (m.get("power", 0) or m.get("hashrate", 0) or 0) * (m.get("quantity", 1) or 1)
            for m in inv_miners
        )

    def calcEffectivePower(m):
        raw = int(m.get("power", 0) or m.get("hashrate", 0) or 0)
        # bonus_percent di RollerCoin: 500 = 5.0%, 50 = 0.5%, 100 = 1.0%
        bonus_val = (m.get("bonus_percent", 0) or 0) / 100.0
        bonus_impact = int(total_base_room * (bonus_val / 100.0))
        return raw + bonus_impact

    if idle_count > 0:
        inv_miners.sort(key=calcEffectivePower, reverse=True)
        if interactive:
            print(f"\n  {N_ORANGE}▸ Miner di Inventory (Berdasarkan Total Efisiensi Power + Bonus):{RST}")
            for m in inv_miners[:8]:
                m_name = m.get("name", "Miner")
                m_pow = fmt_num(m.get("power", 0) or m.get("hashrate", 0))
                m_bonus = (m.get("bonus_percent", 0) or 0) / 100.0
                m_eff = fmt_num(calcEffectivePower(m))
                print(f"    • {m_name:<25} Dasar: {m_pow:>10} GH/s | Bonus: {m_bonus:>4.1f}% | Total Dampak: {m_eff:>12} GH/s")

    if idle_racks_count > 0 and interactive:
        print(f"\n  {N_YELLOW}💡 Tips: Anda punya {idle_racks_count} Rak di inventory yang bisa diletakkan di lantai kamar!{RST}")

    # Cek & optimasi penempatan otomatis (GRATIS 0 RLT)
    if idle_count > 0:
        log("Menghitung slot rak kosong untuk auto-place miner...", "i")
        if interactive:
            print(f"\n  {N_CYAN}» Menghitung penempatan optimal (Power + Bonus Collection)...{RST}")

        # Bangun peta rak terpakai: rack_id -> set of occupied (x, y)
        rack_occupancy = {}
        rack_meta = {}
        for r in racks:
            rid = r.get("_id") or r.get("id")
            r_info = r.get("rack_info") or {}
            rw = r_info.get("width", 2)
            rh = r_info.get("height", 4)
            rack_bonus = r_info.get("bonus", 0) or r.get("bonus", 0) or 0
            rack_meta[rid] = {"width": rw, "height": rh, "bonus": rack_bonus}
            rack_occupancy[rid] = set()

        for pm in placed_miners:
            plc = pm.get("placement") or {}
            rid = plc.get("user_rack_id")
            px = plc.get("x", 0)
            py = plc.get("y", 0)
            pw = pm.get("width", 1) or 1
            if rid in rack_occupancy:
                for dx in range(pw):
                    rack_occupancy[rid].add((px + dx, py))

        # FIX #2 & #5: Cari slot kosong dengan prioritas rak bonus tertinggi
        # dan cek SEMUA posisi x yang valid untuk width-2 (bukan hanya x=0)
        available_slots_w1 = []
        available_slots_w2 = []

        # Urutkan rak berdasarkan bonus tertinggi agar miner terbaik masuk rak terbaik
        sorted_rack_ids = sorted(rack_meta.keys(), key=lambda rid: rack_meta[rid]["bonus"], reverse=True)

        for rid in sorted_rack_ids:
            meta = rack_meta[rid]
            occupied = rack_occupancy.get(rid, set())
            rw = meta["width"]
            rh = meta["height"]
            rack_bonus = meta["bonus"]
            for y in range(rh):
                # Cek semua posisi x yang valid untuk width-2
                for x in range(rw - 1):  # x bisa 0..rw-2 untuk miner w2
                    if (x, y) not in occupied and (x + 1, y) not in occupied:
                        available_slots_w2.append({
                            "user_rack_id": rid, "x": x, "y": y,
                            "rack_bonus": rack_bonus
                        })
                # Slot width-1: semua x
                for x in range(rw):
                    if (x, y) not in occupied:
                        available_slots_w1.append({
                            "user_rack_id": rid, "x": x, "y": y,
                            "rack_bonus": rack_bonus
                        })

        # Urutkan miner inventory berdasarkan EFFECTIVE POWER TERTINGGI
        inv_miners_sorted = sorted(inv_miners, key=calcEffectivePower, reverse=True)
        items_to_move = []

        for item in inv_miners_sorted:
            miner_id = item.get("miner_id") or item.get("_id") or item.get("id")
            w = item.get("width", 1) or 1
            qty = item.get("quantity", 1) or 1

            for _ in range(qty):
                chosen_slot = None
                if w == 2:
                    if available_slots_w2:
                        chosen_slot = available_slots_w2.pop(0)
                        # Hapus semua slot w1 yang sekarang terblok oleh miner w2 ini
                        blocked = {(chosen_slot["user_rack_id"], chosen_slot["y"], chosen_slot["x"]),
                                   (chosen_slot["user_rack_id"], chosen_slot["y"], chosen_slot["x"] + 1)}
                        available_slots_w1 = [
                            s for s in available_slots_w1
                            if (s["user_rack_id"], s["y"], s["x"]) not in blocked
                        ]
                        # Hapus slot w2 lain yang overlap
                        available_slots_w2 = [
                            s for s in available_slots_w2
                            if not (s["user_rack_id"] == chosen_slot["user_rack_id"]
                                    and s["y"] == chosen_slot["y"]
                                    and abs(s["x"] - chosen_slot["x"]) < 2)
                        ]
                else:  # w == 1
                    if available_slots_w1:
                        chosen_slot = available_slots_w1.pop(0)
                        # Jangan hapus slot w2 kecuali kalau kedua sel-nya sudah terpakai
                        available_slots_w2 = [
                            s for s in available_slots_w2
                            if not (s["user_rack_id"] == chosen_slot["user_rack_id"]
                                    and s["y"] == chosen_slot["y"]
                                    and chosen_slot["x"] in {s["x"], s["x"] + 1})
                        ]

                if chosen_slot:
                    items_to_move.append({
                        "miner_id": miner_id,
                        "placement": {
                            "user_rack_id": chosen_slot["user_rack_id"],
                            "x": chosen_slot["x"],
                            "y": chosen_slot["y"]
                        },
                        "name": item.get("name", "Miner"),
                        "power": item.get("power", 0),
                        "eff_power": calcEffectivePower(item)
                    })
                else:
                    break  # Tidak ada slot tersisa untuk miner ini

        if items_to_move:
            if interactive:
                print(f"  {N_GREEN}✓ Ditemukan {len(items_to_move)} slot kosong yang pas untuk miner terbaik Anda!{RST}")

            payload = {
                "type": "custom",
                "items": [{"miner_id": it["miner_id"], "placement": it["placement"]} for it in items_to_move]
            }

            res = await api("POST", "api/game/move-miners-from-inventory", payload)
            if res.get("success"):
                log(f"✓ BERHASIL: {len(items_to_move)} miner sukses dipasang ke rak secara GRATIS!", "ok")
                if interactive:
                    print(f"  {N_GREEN}✓ SUKSES BESAR! {len(items_to_move)} miner berhasil dipasang otomatis ke rak:{RST}")
                    for it in items_to_move:
                        print(f"    • {it['name']} (+{fmt_num(it['power'])} GH/s | Total Efisiensi: +{fmt_num(it['eff_power'])} GH/s)")
                    print(f"  {N_CYAN}⚡ Hash Power akun Anda bertambah seketika tanpa bayar RLT!{RST}")
            else:
                err_msg = res.get("error", "gagal")
                log(f"Move miner error: {err_msg}", "er")
                if interactive:
                    print(f"  {N_RED}✗ Server menolak: {err_msg}{RST}")
        else:
            # -------------------------------------------------------------
            # FITUR CERDAS: AUTO SMART SWAP (TUKAR MINER LEMAH DENGAN MINER KUAT)
            # Mendukung miner lebar 1 DAN lebar 2 sekarang!
            # -------------------------------------------------------------
            swapped_count = 0

            # Pisahkan miner room berdasarkan lebar
            placed_w1 = [m for m in placed_miners if (m.get("width", 1) or 1) == 1]
            placed_w2 = [m for m in placed_miners if (m.get("width", 1) or 1) == 2]
            placed_w1.sort(key=calcEffectivePower)   # Terlemah di awal
            placed_w2.sort(key=calcEffectivePower)   # Terlemah di awal

            # Pisahkan miner inventory berdasarkan lebar
            # FIX #4: Expand quantity > 1 agar semua instance bisa di-swap
            inv_w1 = []
            inv_w2 = []
            for m in inv_miners_sorted:
                qty = m.get("quantity", 1) or 1
                w = m.get("width", 1) or 1
                for _ in range(qty):
                    if w == 2:
                        inv_w2.append(m)
                    else:
                        inv_w1.append(m)

            # --- Swap width-2 ---
            for inv_item in inv_w2:
                inv_eff = calcEffectivePower(inv_item)
                if placed_w2:
                    worst = placed_w2[0]
                    worst_eff = calcEffectivePower(worst)
                    if inv_eff > worst_eff:
                        if interactive:
                            print(f"\n  {N_YELLOW}🧠 Smart Swap (w2): {worst.get('name')} ({fmt_num(worst_eff)} GH/s) → {inv_item.get('name')} ({fmt_num(inv_eff)} GH/s){RST}")
                        unmount_res = await api("POST", "api/game/move-miners-to-inventory", {
                            "type": "default", "user_miners_id": [worst["_id"]]
                        })
                        if unmount_res.get("success"):
                            mount_res = await api("POST", "api/game/move-miners-from-inventory", {
                                "type": "custom",
                                "items": [{"miner_id": inv_item.get("miner_id") or inv_item.get("id"),
                                           "placement": worst.get("placement")}]
                            })
                            if mount_res.get("success"):
                                log(f"✓ Swap-w2: {inv_item.get('name')} gantikan {worst.get('name')} (+{fmt_num(inv_eff - worst_eff)} GH/s)", "ok")
                                placed_w2.pop(0)
                                # Re-sort setelah swap agar kandidat terlemah berikutnya akurat
                                placed_w2.sort(key=calcEffectivePower)
                                swapped_count += 1
                                await sleep(randF(0.8, 1.5) * 1000)

            # --- Swap width-1 ---
            for inv_item in inv_w1:
                inv_eff = calcEffectivePower(inv_item)
                if placed_w1:
                    worst = placed_w1[0]
                    worst_eff = calcEffectivePower(worst)
                    if inv_eff > worst_eff:
                        if interactive:
                            print(f"\n  {N_YELLOW}🧠 Smart Swap (w1): {worst.get('name')} ({fmt_num(worst_eff)} GH/s) → {inv_item.get('name')} ({fmt_num(inv_eff)} GH/s){RST}")
                        unmount_res = await api("POST", "api/game/move-miners-to-inventory", {
                            "type": "default", "user_miners_id": [worst["_id"]]
                        })
                        if unmount_res.get("success"):
                            mount_res = await api("POST", "api/game/move-miners-from-inventory", {
                                "type": "custom",
                                "items": [{"miner_id": inv_item.get("miner_id") or inv_item.get("id"),
                                           "placement": worst.get("placement")}]
                            })
                            if mount_res.get("success"):
                                log(f"✓ Swap-w1: {inv_item.get('name')} gantikan {worst.get('name')} (+{fmt_num(inv_eff - worst_eff)} GH/s)", "ok")
                                placed_w1.pop(0)
                                # Re-sort setelah swap agar kandidat terlemah berikutnya akurat
                                placed_w1.sort(key=calcEffectivePower)
                                swapped_count += 1
                                await sleep(randF(0.8, 1.5) * 1000)

            if swapped_count > 0:
                log(f"✓ Smart Swap selesai: {swapped_count} miner berhasil diganti ke versi lebih kuat!", "ok")
                if interactive:
                    print(f"  {N_GREEN}✓ SUKSES! {swapped_count} miner lemah digantikan miner lebih kuat di rak!{RST}")
            else:
                msg = "Semua rak sudah optimal dan terisi miner dengan efisiensi tertinggi."
                log(msg, "ok")
                if interactive:
                    print(f"\n  {N_GREEN}✓ {msg}{RST}")
    elif idle_count == 0:
        msg = "Semua miner sudah terpasang optimal di rak ruangan Anda."
        log(msg, "ok")
        if interactive:
            print(f"\n  {N_GREEN}✓ {msg}{RST}")

    return True

async def scanMergeMiners(interactive=False, inv_miners=None, placed_miners=None):
    if inv_miners is None or placed_miners is None:
        return
    all_items = []
    for m in placed_miners:
        all_items.append({"id": m.get("_id"), "name": m.get("name"),
                          "level": m.get("level", 0), "width": m.get("width", 1), "src": "room"})
    for m in inv_miners:
        q = m.get("quantity", 0) or 1
        for _ in range(q):
            all_items.append({"id": m.get("miner_id") or m.get("id"), "name": m.get("name"),
                              "level": m.get("level", 0), "width": m.get("width", 1), "src": "inv"})

    grouped = {}
    for m in all_items:
        if not m["name"]:
            continue
        k = f"{m['name']}|{m['level']}|{m['width']}"
        grouped.setdefault(k, []).append(m)

    pairs = []
    for items in grouped.values():
        if len(items) < 2:
            continue
        for i in range(0, (len(items) // 2) * 2, 2):
            pairs.append([items[i], items[i + 1]])

    if pairs:
        log(f"Ditemukan {len(pairs)} pasang miner yang siap di-Merge (Lv.1 + Lv.1 → Lv.2)!", "ok")
        if interactive:
            print(f"\n  {N_GREEN}⚡ Ditemukan {len(pairs)} Pasang Miner yang bisa di-Merge:{RST}")
            for i, p in enumerate(pairs[:5], 1):
                print(f"    [{i}] {p[0]['name']} (Level {p[0]['level']}) [{p[0]['src']} + {p[1]['src']}]")
            print(f"  {N_GRAY}Catatan: Merge/Crafting miner di RollerCoin membutuhkan suku cadang (parts: wires, fan, hashboard).{RST}")
    else:
        if interactive:
            print(f"  {N_GRAY}ℹ Tidak ada miner kembar yang siap di-merge saat ini.{RST}")

# ═══════════════════════════════════════════════════════════════
#  AUTO CLAIM SEASON PASS / RST TICKET REWARDS
# ═══════════════════════════════════════════════════════════════
async def checkSeasonPass():
    """Auto-claim Season Pass rewards yang sudah tersedia."""
    try:
        # Ambil data season pass aktif
        res = await api("GET", "api/season-pass/current")
        if not res.get("success") or not res.get("data"):
            # Coba endpoint alternatif
            res = await api("GET", "api/season/current")
        if not res.get("success") or not res.get("data"):
            log("Season Pass: tidak ada data season aktif", "dbg")
            return

        sp_data = res.get("data", {})
        rewards = sp_data.get("rewards") or sp_data.get("tiers") or []
        claimed_any = False

        for reward in rewards:
            rid = reward.get("id") or reward.get("_id")
            is_claimed = reward.get("is_claimed") or reward.get("claimed")
            is_available = reward.get("is_available") or reward.get("available") or reward.get("can_claim")
            if is_available and not is_claimed and rid:
                claim_res = await api("POST", f"api/season-pass/claim/{rid}")
                if not claim_res.get("success"):
                    claim_res = await api("POST", "api/season-pass/claim", {"reward_id": rid})
                if claim_res.get("success"):
                    r_name = reward.get("name") or reward.get("title") or f"Reward {rid}"
                    log(f"✓ Season Pass reward diklaim: {r_name}!", "ok")
                    claimed_any = True
                await sleep(randF(0.8, 1.5) * 1000)

        if not claimed_any:
            log("Season Pass: semua reward sudah diklaim / belum tersedia", "dbg")
    except Exception as e:
        log(f"Season Pass check: {e}", "dbg")


# ═══════════════════════════════════════════════════════════════
#  SCAN PARTS INVENTORY (BAHAN MERGE/CRAFT)
# ═══════════════════════════════════════════════════════════════
async def scanPartsInventory(interactive=False):
    """Scan bahan-bahan merge (wires, fan, hashboard) di inventory."""
    try:
        res = await api("GET", "api/game/inventory?itemType=part&type=part&skip=0&limit=100")
        if not res.get("success"):
            res = await api("GET", "api/craft/parts")
        parts = []
        if res.get("success"):
            items = (res.get("data") or {}).get("items") or res.get("data") or []
            if isinstance(items, list):
                parts = items

        if interactive:
            if parts:
                print(f"\n  {N_ORANGE}▸ Parts / Bahan Craft di Inventory:{RST}")
                for p in parts:
                    p_name = p.get("name") or p.get("title") or "Part"
                    p_qty = p.get("quantity") or p.get("amount") or 1
                    print(f"    • {p_name:<30} x{p_qty}")
            else:
                print(f"  {N_GRAY}ℹ Tidak ada parts/bahan merge di inventory.{RST}")
        return parts
    except Exception as e:
        log(f"Parts scan: {e}", "dbg")
        return []


async def checkAndSetSplitPower(target_coin="rlt"):
    log(f"Memeriksa alokasi Split Power (Target: {target_coin.upper()})...", "i")
    try:
        powerRes = await api("GET", "api/power/split-power")
        if powerRes.get("success") and powerRes.get("data"):
            dist = powerRes.get("data", {}).get("distribution", {})
            curr = dist.get(target_coin.lower(), 0)
            log(f"Distribusi saat ini: {target_coin.upper()} = {curr}%", "i")
            if curr < 100:
                log(f"Mengalokasikan 100% Hashrate ke {target_coin.upper()} agar koin lebih cepat...", "wr")
                new_dist = {c: 0 for c in dist.keys()}
                new_dist[target_coin.lower()] = 100
                setRes = await api("POST", "api/power/set-split-power", {"distribution": new_dist})
                if setRes.get("success"):
                    log(f"✓ 100% Power berhasil difokuskan ke {target_coin.upper()}!", "ok")
                else:
                    log(f"Perubahan power terkunci cooldown (12 jam): {setRes.get('error', 'cooldown')}", "dbg")
            else:
                log(f"Power sudah 100% optimal di {target_coin.upper()}.", "ok")
    except Exception as e:
        log(f"Split power check: {e}", "dbg")
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
    lines.append(row(f"{N_GREEN}[1]{RST} {N_WHITE}Login Email + OTP{RST}"))
    lines.append(row(f"{N_CYAN}[2]{RST} {N_WHITE}{BOLD}Start 24/7 Gacor Mode (Continuous Auto Loop){RST}"))
    lines.append(row(f"{N_YELLOW}[3]{RST} {N_WHITE}Auto Scan & Set Miner / Rak (Cek Rak & Inventory){RST}"))
    lines.append(row(f"{N_PINK}[4]{RST} {N_WHITE}Set Split Power 100% (Maksimalkan Koin Cepat){RST}"))
    lines.append(row(f"{N_ORANGE}[5]{RST} {N_WHITE}Lihat Status Mining Lengkap (Power, League, Reward){RST}"))
    lines.append(row(f"{N_PURPLE}[6]{RST} {N_WHITE}Scan Parts / Bahan Merge di Inventory{RST}"))
    lines.append(row(f"{N_GREEN}[7]{RST} {N_WHITE}{BOLD}Auto Forge Merge (Parts & Miner Sekarang!){RST}"))
    lines.append(row(f"{N_RED}[8]{RST} {N_WHITE}Copot Semua Miner ke Inventory (Unmount All){RST}"))
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

            # 3. Cek & Optimasi Miner / Rak di Kamar
            if cfg.get("auto_miners", True):
                await scanAndOptimizeRoom(interactive=False)

            # 4. Cek & Klaim Quest Harian
            if cfg.get("auto_quests", True):
                await checkDailyQuests()

            # 5. Cek & Klaim Season Pass Rewards
            if cfg.get("auto_season_pass", True):
                await checkSeasonPass()

            # 6. Hamster Expedition
            if cfg.get("hamster", True):
                await hamster()

            # 7. Auto Merge Forge (Parts & Miner)
            if cfg.get("auto_forge", True):
                await autoForgeMerge(interactive=False)

            # 8. Main Game Batch Berdasarkan Prioritas PPS
            if cfg.get("game", True):
                await playGameBatch(cfg, max_games=25)

            # 9. Jeda Siklus Manusiawi (Rest 30–60s)
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

            choice = "2" if auto_start else showMenu(cfg)
            if not choice:
                continue

            if choice == "0":
                sys.stdout.write("\x1b[?25h")
                clear()
                print(f"{RED}[!] Keluar.{RST}")
                return

            if choice == "1":
                await emailLogin()
                continue

            if choice == "2":
                if not cfg.get("userAgent"):
                    cfg["userAgent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                         "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
                    saveConfig(cfg)

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

            if choice == "3":
                dashboard.pause()
                clear()
                print(f"{N_CYAN}{BOLD}⛏  Room & Miner Optimizer{RST}")
                print(f"{N_GRAY}Memeriksa rak dan miner inventory Anda...{RST}\n")
                await refreshTokenFlow(quiet=True)
                await scanAndOptimizeRoom(interactive=True)
                await _async_input(f"\n  {N_WHITE}Tekan Enter untuk kembali ke menu...{RST}")
                continue

            if choice == "4":
                dashboard.pause()
                clear()
                print(f"{N_PINK}{BOLD}⚡ Alokasi Split Power (Fokus Koin Cepat){RST}")
                print(f"{N_GRAY}Fokuskan 100% Hashrate ke 1 koin untuk mempercepat withdraw / buy miner.{RST}\n")
                print(f"  {N_YELLOW}[1]{RST} RLT (RollerToken - Rekomendasi untuk beli miner)")
                print(f"  {N_YELLOW}[2]{RST} RST (Roller Season Token)")
                print(f"  {N_YELLOW}[3]{RST} BTC (Bitcoin)")
                print(f"  {N_YELLOW}[4]{RST} DOGE (Dogecoin)")
                print(f"  {N_YELLOW}[5]{RST} BNB (Binance Coin)")
                c_opt = await _async_input(f"\n  {N_YELLOW}▸{RST} {N_WHITE}Pilih Koin (1-5) : ")
                coin_map = {"1": "rlt", "2": "rst", "3": "btc", "4": "doge", "5": "bnb"}
                target_c = coin_map.get(c_opt, "rlt")
                await refreshTokenFlow(quiet=True)
                await checkAndSetSplitPower(target_coin=target_c)
                await _async_input(f"\n  {N_WHITE}Tekan Enter untuk kembali ke menu...{RST}")
                continue

            if choice == "5":
                dashboard.pause()
                clear()
                print(f"{N_ORANGE}{BOLD}📊 Status Mining Lengkap{RST}\n")
                await refreshTokenFlow(quiet=True)
                prof = await getProfile()
                if not prof:
                    print(f"  {N_RED}✗ Token expired! Silakan login ulang (menu 1).{RST}")
                else:
                    name = prof.get("name") or prof.get("email") or "User"
                    power = prof.get("max_total_power", 0) or 0
                    bonus = prof.get("bonus_percent", 0) or 0
                    miners = prof.get("user_miners_amount", 0) or 0
                    league = prof.get("league_title") or prof.get("league") or "-"
                    bat_pct = prof.get("battery_charge_level") or prof.get("battery") or "?"
                    bat_min = prof.get("battery_minutes_left") or "?"

                    print(f"  {N_GRAY}Nama{RST}        : {N_YELLOW}{name}{RST}")
                    print(f"  {N_GRAY}Total Power{RST} : {N_CYAN}{fmt_num(power)} GH/s{RST}")
                    print(f"  {N_GRAY}Bonus{RST}       : {N_GREEN}+{bonus}%{RST}")
                    print(f"  {N_GRAY}Miners{RST}      : {N_PINK}{miners}{RST}")
                    print(f"  {N_GRAY}League{RST}      : {N_ORANGE}{league}{RST}")
                    if bat_pct != "?":
                        bc = N_GREEN if int(bat_pct) > 50 else (N_YELLOW if int(bat_pct) > 20 else N_RED)
                        print(f"  {N_GRAY}Baterai{RST}     : {bc}{bat_pct}%{RST} (sisa {bat_min} menit)")

                    # Cek info league lebih detail
                    league_res = await api("GET", "api/game/league")
                    if league_res.get("success") and league_res.get("data"):
                        ld = league_res["data"]
                        curr_power = ld.get("current_power") or ld.get("power", 0)
                        next_power = ld.get("next_level_power") or ld.get("next_power", 0)
                        league_name = ld.get("current_league") or ld.get("league_name", "-")
                        if next_power:
                            diff = max(0, int(next_power) - int(curr_power))
                            print(f"\n  {N_GREEN}▸ League: {league_name}{RST}")
                            print(f"  {N_GRAY}  Power saat ini{RST}: {N_CYAN}{fmt_num(curr_power)} GH/s{RST}")
                            print(f"  {N_GRAY}  Target naik league{RST}: {N_YELLOW}{fmt_num(next_power)} GH/s{RST}")
                            print(f"  {N_GRAY}  Kurang{RST}: {N_RED}{fmt_num(diff)} GH/s{RST}")

                    # Split power info
                    sp_res = await api("GET", "api/power/split-power")
                    if sp_res.get("success") and sp_res.get("data"):
                        dist = sp_res["data"].get("distribution", {})
                        if dist:
                            print(f"\n  {N_PINK}▸ Split Power:{RST}")
                            for coin, pct in dist.items():
                                bar = "█" * int((pct or 0) / 5)
                                print(f"    {coin.upper():<6}: {N_CYAN}{pct:>3}%{RST} {N_GRAY}{bar}{RST}")

                await _async_input(f"\n  {N_WHITE}Tekan Enter untuk kembali ke menu...{RST}")
                continue

            if choice == "6":
                dashboard.pause()
                clear()
                print(f"{N_PURPLE}{BOLD}🔧 Scan Parts / Bahan Merge di Inventory{RST}\n")
                await refreshTokenFlow(quiet=True)
                await scanPartsInventory(interactive=True)
                await _async_input(f"\n  {N_WHITE}Tekan Enter untuk kembali ke menu...{RST}")
                continue

            if choice == "7":
                dashboard.pause()
                clear()
                print(f"{N_GREEN}{BOLD}⚒  Auto Forge Merge (Parts & Miner){RST}")
                print(f"{N_GRAY}Mengecek dan mengeksekusi resep merge yang siap di Forge...{RST}\n")
                await refreshTokenFlow(quiet=True)
                merges = await autoForgeMerge(interactive=True)
                if merges == 0:
                    print(f"\n  {N_YELLOW}ℹ Belum ada parts atau miner yang memenuhi syarat merge.{RST}")
                else:
                    print(f"\n  {N_GREEN}✓ Berhasil menyelesaikan {merges}x merge!{RST}")
                await _async_input(f"\n  {N_WHITE}Tekan Enter untuk kembali ke menu...{RST}")
                continue

            if choice == "8":
                dashboard.pause()
                clear()
                print(f"{N_RED}{BOLD}📦 Copot Semua Miner ke Inventory (Unmount All){RST}\n")
                confirm = await _async_input(f"  {N_YELLOW}Yakin ingin mencopot SEMUA miner dari rak? (y/n): {RST}")
                if confirm.lower() == "y":
                    await refreshTokenFlow(quiet=True)
                    prof = await getProfile()
                    uid = (prof or {}).get("id") or (prof or {}).get("_id")
                    if uid:
                        print(f"  {N_CYAN}» Mengambil data miner di ruangan...{RST}")
                        r_res = await api("GET", f"api/game/room-config/{uid}")
                        placed = (r_res.get("data") or {}).get("miners", [])
                        if placed:
                            m_ids = [m["_id"] for m in placed if m.get("_id")]
                            print(f"  {N_CYAN}» Mencopot {len(m_ids)} miner ke inventory...{RST}")
                            unm_res = await api("POST", "api/game/move-miners-to-inventory", {
                                "type": "default",
                                "user_miners_id": m_ids
                            })
                            if unm_res.get("success"):
                                print(f"  {N_GREEN}✓ SUKSES! {len(m_ids)} miner berhasil dipindahkan ke inventory.{RST}")
                                print(f"  {N_YELLOW}Sekarang Anda bisa menjalankan Menu [7] untuk mengecek Merge Miner di Forge!{RST}")
                            else:
                                print(f"  {N_RED}✗ Gagal unmount: {unm_res.get('error')}{RST}")
                        else:
                            print(f"  {N_YELLOW}ℹ Ruangan sudah kosong, tidak ada miner yang terpasang.{RST}")
                else:
                    print(f"  {N_GRAY}Dibatalkan.{RST}")
                await _async_input(f"\n  {N_WHITE}Tekan Enter untuk kembali ke menu...{RST}")
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

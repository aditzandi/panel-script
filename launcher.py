"""Launcher online 1 FILE: config ada di dalam file ini, taruh di folder mana pun.

- Sub-aplikasi diunduh dari link (base_url + file), lalu dijalankan
- File unduhan disimpan di folder sementara & dihapus setelah tiap app selesai
- Semua sisa dihapus saat launcher keluar (normal, Ctrl+C, atau sesi ditutup)
- Sisa dari crash/force-close sebelumnya dibersihkan saat launcher dibuka lagi
"""
import atexit
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


# ====== EDIT BAGIAN INI SAJA ==========================================
CONFIG = {
    "title": "PANEL ONLINE",
    "subtitle": "Kumpulan script dalam satu panel",
    "creator": "Bang Miun C12",
    "version": "2.0",
    "base_url": "https://raw.githubusercontent.com/aditzandi/panel-script/refs/heads/main/",
    "menu_online": True,        # True = daftar menu diambil dari menu.json di base_url
    "categories": [
        {
            "name": "TANPA API KEY",
            "items": [
                {"label": "roller", "file": "bot.js"},
                {"label": "Kalkulator", "file": "kalkulator.py"},
            ],
        },
        {
            "name": "API KEY",
            "items": [
                {"label": "tap.coin.de", "file": "tap.py"},
                {"label": "Minitasky", "file": "minitasky.py"},
            ],
        },
        {
            "name": "APLIKASI TELEGRAM",
            "items": [
                {"label": "PlayNXC", "file": "playnxc.py"},
                {"label": "FarmBuddiesBot", "file": "FarmBuddiesBot.py"},
            ],
        },
    ],
}
# =======================================================================

PREFIX = "panel_tmp_"


# ---------------------------------------------------------------------
# Pembersihan file sementara
# ---------------------------------------------------------------------
def bersihkan_sisa_lama(umur_detik=3600):
    """Hapus folder panel_tmp_* peninggalan crash/force-close (> 1 jam)."""
    for p in Path(tempfile.gettempdir()).glob(PREFIX + "*"):
        try:
            if p.is_dir() and time.time() - p.stat().st_mtime > umur_detik:
                shutil.rmtree(p, ignore_errors=True)
        except OSError:
            pass


bersihkan_sisa_lama()
WORKDIR = Path(tempfile.mkdtemp(prefix=PREFIX))


def bersihkan():
    shutil.rmtree(WORKDIR, ignore_errors=True)


atexit.register(bersihkan)          # jalan saat keluar normal / error


def _keluar(signum, frame):         # SIGTERM / SIGHUP (sesi ditutup)
    sys.exit(0)                     # sys.exit -> atexit tetap berjalan


for nama_sinyal in ("SIGTERM", "SIGHUP"):
    if hasattr(signal, nama_sinyal):
        signal.signal(getattr(signal, nama_sinyal), _keluar)


# ---------------------------------------------------------------------
# Tampilan: warna, kotak, banner
# ---------------------------------------------------------------------
def _siapkan_terminal():
    """Aktifkan warna ANSI di Windows & paksa output UTF-8."""
    if os.name == "nt":
        os.system("")               # mengaktifkan mode VT di Windows 10+
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            m = ctypes.c_ulong()
            if k.GetConsoleMode(h, ctypes.byref(m)):
                k.SetConsoleMode(h, m.value | 0x0004)
        except Exception:
            pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_siapkan_terminal()

WARNA_AKTIF = (sys.stdout.isatty() or bool(os.environ.get("FORCE_COLOR"))) and not os.environ.get("NO_COLOR")


def _kode(n):
    return f"\033[{n}m" if WARNA_AKTIF else ""


def _k256(n):
    return f"\033[38;5;{n}m" if WARNA_AKTIF else ""


R = _kode(0)
BOLD = _kode(1)
DIM = _kode(2)
MERAH = _kode(91)
HIJAU = _kode(92)
KUNING = _kode(93)
BIRU = _kode(94)
UNGU = _kode(95)
CYAN = _kode(96)
PUTIH = _kode(97)
ORANYE = _k256(214)
BORDER = _k256(39)

try:
    _kolom = shutil.get_terminal_size((80, 24)).columns
except Exception:
    _kolom = 80
WIDTH = max(40, min(56, _kolom - 1))

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

BANNER = [
    "██████╗  █████╗ ███╗   ██╗███████╗██╗     ",
    "██╔══██╗██╔══██╗████╗  ██║██╔════╝██║     ",
    "██████╔╝███████║██╔██╗ ██║█████╗  ██║     ",
    "██╔═══╝ ██╔══██║██║╚██╗██║██╔══╝  ██║     ",
    "██║     ██║  ██║██║ ╚████║███████╗███████╗",
    "╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝",
]
GRADASI = (51, 45, 39, 33, 63, 99)   # cyan -> biru -> ungu


def vlen(teks):
    """Panjang teks yang terlihat (tanpa kode warna)."""
    return len(ANSI_RE.sub("", teks))


def bersih_layar():
    os.system("cls" if os.name == "nt" else "clear")


def tengah(teks, lebar=None):
    lebar = lebar or WIDTH
    sisa = max(0, lebar - vlen(teks))
    return " " * (sisa // 2) + teks


def atas(judul=""):
    if judul:
        label = f" {judul} "
        sisa = WIDTH - 2 - vlen(label) - 2
        return f"{BORDER}╔══{R}{BOLD}{PUTIH}{label}{R}{BORDER}{'═' * max(0, sisa)}╗{R}"
    return f"{BORDER}╔{'═' * (WIDTH - 2)}╗{R}"


def bawah():
    return f"{BORDER}╚{'═' * (WIDTH - 2)}╝{R}"


def pemisah():
    return f"{BORDER}╟{'─' * (WIDTH - 2)}╢{R}"


def baris(kiri="", kanan="", rata="kiri"):
    """Satu baris kotak: teks kiri, opsional teks kanan (rata kanan)."""
    dalam = WIDTH - 4
    if rata == "tengah":
        isi = tengah(kiri, dalam)
        isi += " " * max(0, dalam - vlen(isi))
    else:
        celah = max(1, dalam - vlen(kiri) - vlen(kanan))
        isi = kiri + " " * celah + kanan if kanan else kiri + " " * max(0, dalam - vlen(kiri))
    return f"{BORDER}║{R} {isi} {BORDER}║{R}"


def cetak_header():
    """Banner + kotak info pembuat. Dipanggil di setiap layar."""
    bersih_layar()
    print()
    if WIDTH >= 44:
        for teks, g in zip(BANNER, GRADASI):
            print(tengah(f"{_k256(g)}{BOLD}{teks}{R}"))
    judul = CONFIG.get("title", "PANEL")
    print(tengah(f"{BOLD}{PUTIH}{judul}{R}"))
    sub = CONFIG.get("subtitle")
    if sub:
        print(tengah(f"{DIM}{sub}{R}"))
    print()
    print(atas())
    waktu = time.strftime("%d %b %Y  %H:%M")
    print(baris(f"{ORANYE}◆{R} {DIM}Dibuat oleh{R}  {DIM}:{R} {BOLD}{HIJAU}{CONFIG.get('creator', '-')}{R}"))
    print(baris(f"{ORANYE}◆{R} {DIM}Versi      {R}  {DIM}:{R} {PUTIH}{CONFIG.get('version', '1.0')}{R}"))
    print(baris(f"{ORANYE}◆{R} {DIM}Waktu      {R}  {DIM}:{R} {PUTIH}{waktu}{R}"))
    warna_status = HIJAU if STATUS_MENU == "online" else KUNING
    print(baris(f"{ORANYE}◆{R} {DIM}Menu       {R}  {DIM}:{R} {warna_status}{STATUS_MENU}{R}"))
    print(bawah())
    print()


def jeda(pesan="Tekan Enter untuk kembali"):
    input(f"\n {DIM}↵  {pesan}...{R}")


def prompt(batas):
    return input(f"\n {CYAN}{BOLD}❯{R} {PUTIH}Pilih menu{R} {DIM}[0-{batas}]{R} {CYAN}:{R} ").strip()


def info(ikon, warna, teks):
    print(f" {warna}{ikon}{R} {teks}")


# ---------------------------------------------------------------------
# Menu online (menu.json di base_url)
# ---------------------------------------------------------------------
STATUS_MENU = "bawaan"
NAMA_FILE_AMAN = re.compile(r"[A-Za-z0-9_\-]+\.py")


def _menu_valid(data):
    """Pastikan struktur menu.json benar & nama file aman."""
    if not isinstance(data, dict) or not isinstance(data.get("categories"), list) or not data["categories"]:
        return False
    for kat in data["categories"]:
        if not isinstance(kat, dict) or not isinstance(kat.get("name"), str) or not isinstance(kat.get("items"), list):
            return False
        for it in kat["items"]:
            if not isinstance(it, dict) or not isinstance(it.get("label"), str):
                return False
            f = it.get("file")
            if f is not None and not (isinstance(f, str) and NAMA_FILE_AMAN.fullmatch(f)):
                return False
    return True


def muat_menu_online(cfg):
    """Ambil menu.json; kalau gagal/tidak valid, pakai menu bawaan di file ini."""
    global STATUS_MENU
    if not cfg.get("menu_online") or not cfg["base_url"].startswith("https://"):
        return
    try:
        req = urllib.request.Request(cfg["base_url"] + "menu.json", headers={"User-Agent": "panel/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        if not _menu_valid(data):
            return
        for kunci in ("title", "subtitle", "version"):    # creator tetap dari file ini
            if isinstance(data.get(kunci), str):
                cfg[kunci] = data[kunci]
        cfg["categories"] = data["categories"]
        STATUS_MENU = "online"
    except Exception:
        pass


# ---------------------------------------------------------------------
# Unduh & jalankan
# ---------------------------------------------------------------------
def ukuran(n):
    return f"{n / 1024:.1f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.2f} MB"


def bar_progress(selesai, total, lebar=28):
    if total:
        persen = min(1.0, selesai / total)
        penuh = int(lebar * persen)
        bar = f"{HIJAU}{'█' * penuh}{R}{DIM}{'░' * (lebar - penuh)}{R}"
        return f" {BORDER}[{R}{bar}{BORDER}]{R} {BOLD}{int(persen * 100):>3}%{R}  {DIM}{ukuran(selesai)}{R}"
    putar = "|/-\\"[int(time.time() * 8) % 4]
    return f" {CYAN}{putar}{R} {DIM}{ukuran(selesai)}{R}"


def unduh(url, tujuan):
    if not url.startswith("https://"):
        info("✖", MERAH, "Ditolak: hanya link https yang diizinkan.")
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "panel/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            total = int(r.headers.get("Content-Length") or 0)
            selesai = 0
            potongan = []
            while True:
                blok = r.read(8192)
                if not blok:
                    break
                potongan.append(blok)
                selesai += len(blok)
                sys.stdout.write("\r" + bar_progress(selesai, total) + "   ")
                sys.stdout.flush()
        tujuan.write_bytes(b"".join(potongan))
        sys.stdout.write("\r" + bar_progress(selesai or 1, selesai or 1) + "   \n")
        sys.stdout.flush()
        return True
    except Exception as e:
        sys.stdout.write("\n")
        info("✖", MERAH, f"Gagal unduh {DIM}({e}){R}")
        return False


def jalankan(item, base_url):
    nama = item.get("file")
    label = item.get("label", nama or "?")
    if not nama:
        print()
        info("!", KUNING, f"{BOLD}{label}{R} belum tersedia. Nantikan update berikutnya.")
        jeda()
        return
    if not NAMA_FILE_AMAN.fullmatch(nama):
        print()
        info("✖", MERAH, f"Nama file tidak valid: {nama}")
        jeda()
        return
    url = base_url + nama
    path = WORKDIR / nama
    cetak_header()
    print(atas("MEMUAT APLIKASI"))
    print(baris(f"{ORANYE}▸{R} {BOLD}{PUTIH}{label}{R}"))
    print(baris(f"{DIM}{nama}{R}"))
    print(bawah())
    print()
    if not unduh(url, path):
        jeda()
        return
    info("✔", HIJAU, f"{BOLD}Siap!{R} Menjalankan {PUTIH}{label}{R}...")
    time.sleep(0.6)
    bersih_layar()
    kode = None
    try:
        kode = subprocess.run([sys.executable, str(path)]).returncode
    except KeyboardInterrupt:
        print()
        info("!", KUNING, "App dihentikan.")
    finally:
        path.unlink(missing_ok=True)    # bersih setelah app selesai/di-stop
    print()
    if kode in (None, 0):
        info("✔", HIJAU, f"{BOLD}{label}{R} selesai. File sementara dihapus.")
    else:
        info("!", KUNING, f"{BOLD}{label}{R} berhenti dengan kode {kode}. File sementara dihapus.")
    jeda()


# ---------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------
def tampil_menu(judul, jalur, baris_menu):
    """baris_menu: list of (teks, badge). Mengembalikan indeks pilihan atau None."""
    cetak_header()
    print(atas(judul))
    if jalur:
        print(baris(f"{DIM}{jalur}{R}"))
        print(pemisah())
    for i, (teks, badge) in enumerate(baris_menu, start=1):
        print(baris(f"{BORDER}[{R}{BOLD}{CYAN}{i}{R}{BORDER}]{R} {ORANYE}▸{R} {PUTIH}{teks}{R}", badge))
    print(pemisah())
    print(baris(f"{BORDER}[{R}{BOLD}{MERAH}0{R}{BORDER}]{R} {MERAH}✖{R} {PUTIH}Kembali / Keluar{R}"))
    print(bawah())
    while True:
        jawab = prompt(len(baris_menu))
        if jawab == "0":
            return None
        if jawab.isdigit() and 1 <= int(jawab) <= len(baris_menu):
            return int(jawab) - 1
        info("✖", MERAH, "Pilihan tidak valid, coba lagi.")


def badge_kategori(kat):
    tersedia = sum(1 for it in kat["items"] if it.get("file"))
    if tersedia == 0:
        return f"{KUNING}segera{R}"
    return f"{HIJAU}{tersedia} app{R}"


def badge_item(it):
    return f"{HIJAU}siap{R}" if it.get("file") else f"{KUNING}segera{R}"


def salam_perpisahan():
    bersih_layar()
    print()
    print(tengah(f"{BOLD}{HIJAU}Sampai jumpa!{R}"))
    print(tengah(f"{DIM}Terima kasih sudah memakai panel ini{R}"))
    print()
    print(tengah(f"{ORANYE}◆{R} {DIM}Dibuat oleh{R} {BOLD}{PUTIH}{CONFIG.get('creator', '-')}{R}"))
    print(tengah(f"{DIM}cache dibersihkan{R}"))
    print()


def main():
    cfg = CONFIG
    base_url = cfg["base_url"]
    muat_menu_online(cfg)
    while True:
        kategori = cfg["categories"]
        i = tampil_menu(
            "MENU UTAMA", None,
            [(k["name"], badge_kategori(k)) for k in kategori],
        )
        if i is None:
            salam_perpisahan()
            return
        items = kategori[i]["items"]
        while True:
            j = tampil_menu(
                kategori[i]["name"], f"Menu utama  ›  {kategori[i]['name']}",
                [(it["label"], badge_item(it)) for it in items],
            )
            if j is None:
                break
            jalankan(items[j], base_url)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n {DIM}Keluar. (cache dibersihkan){R}")

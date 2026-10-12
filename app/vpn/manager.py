"""Управление VPN: установка sing-box, запуск/остановка, системный прокси, умная маршрутизация,
подписки, пинг, раздача в локальную сеть."""
import base64
import ctypes
import io
import json
import os
import secrets
import socket
import ssl
import subprocess
import threading
import time
import urllib.request
import zipfile
from collections import deque
import re
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ..i18n import tr
from ..paths import engine_dir
from ..settings import settings
from ..winutil import CREATE_NO_WINDOW, IS_WIN, run
from . import config as C
from . import links as L

SB_VERSION = "1.14.3"
SB_URL = (f"https://github.com/SagerNet/sing-box/releases/download/v{SB_VERSION}/"
          f"sing-box-{SB_VERSION}-windows-amd64.zip")
RECHECK_AUTO = 6 * 3600        # перепроверять «авто»-сайты раз в 6 ч
NEG_TTL = 15 * 60              # сайт работает напрямую — не проверять повторно 15 мин
SUB_REFRESH = 12 * 3600
FW_RULE = "ZapretCloud VPN (LAN)"
WATCH_PORTS = {"443", "80"}
_LOG_RE = re.compile(r"^(TRACE|DEBUG|INFO|WARN|ERROR|FATAL)\[\d+\]\s+(?:\[(\d+) ([\d.]+)(ms|s|m\S*)\]\s+)?(.*)$")

MULTI_SUFFIX = {"co.uk", "com.au", "co.jp", "com.br", "com.tr", "com.cn", "co.kr", "com.ua", "org.uk",
                "com.ru", "net.ru", "org.ru", "pp.ua", "co.in", "github.io", "googleapis.com",
                "cloudfront.net", "herokuapp.com", "appspot.com", "vercel.app", "netlify.app", "pages.dev",
                "workers.dev", "blogspot.com", "azurewebsites.net"}


def base_domain(host: str) -> str:
    host = host.lower().strip(".")
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if ".".join(parts[-2:]) in MULTI_SUFFIX:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _free_port(pref: int) -> int:
    for p in [pref] + [0]:
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            port = s.getsockname()[1]
            s.close()
            return port
        except OSError:
            s.close()
    return pref


def tcp_ping(host, port, timeout=3.0) -> int:
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            pass
        return int((time.perf_counter() - t0) * 1000)
    except OSError:
        return -1


PROBE_AUTH = ("zc" + secrets.token_hex(4), secrets.token_urlsafe(18))   # пароль служебных прокси (на запуск программы)


def probe_proxy_url(port: int) -> str:
    return f"http://{PROBE_AUTH[0]}:{PROBE_AUTH[1]}@127.0.0.1:{port}"


def tls_probe(host: str, proxy_port: int, timeout=6.0) -> bool:
    """TLS-рукопожатие с host:443 через локальный HTTP-прокси sing-box (probe-direct / probe-vpn)."""
    auth = base64.b64encode(f"{PROBE_AUTH[0]}:{PROBE_AUTH[1]}".encode()).decode()
    try:
        s = socket.create_connection(("127.0.0.1", proxy_port), timeout=timeout)
    except OSError:
        return False
    try:
        s.settimeout(timeout)
        s.sendall(f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n"
                  f"Proxy-Authorization: Basic {auth}\r\n\r\n".encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            ch = s.recv(1024)
            if not ch:
                return False
            resp += ch
        if b" 200" not in resp.split(b"\r\n", 1)[0]:
            return False
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ss = ctx.wrap_socket(s, server_hostname=host, do_handshake_on_connect=False)
        ss.settimeout(timeout)
        ss.do_handshake()
        ss.close()
        return True
    except (OSError, ssl.SSLError):
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def lan_ips() -> list[str]:
    import psutil
    out = []
    for name, addrs in psutil.net_if_addrs().items():
        if C.TUN_NAME.lower() in name.lower():
            continue
        st = psutil.net_if_stats().get(name)
        if st and not st.isup:
            continue
        for a in addrs:
            if a.family == socket.AF_INET:
                ip = a.address
                if ip.startswith(("192.168.", "10.")) or (ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31
                                                          and not ip.startswith("172.19.0.")):
                    out.append(ip)
    return sorted(set(out), key=lambda x: (not x.startswith("192.168."), x))


def best_iface_index() -> int | None:
    """Индекс физического интерфейса с маршрутом в интернет (до поднятия TUN)."""
    if not IS_WIN:
        return None
    try:
        idx = ctypes.c_ulong(0)
        addr = int.from_bytes(socket.inet_aton("8.8.8.8"), "little")
        if ctypes.windll.iphlpapi.GetBestInterface(ctypes.c_ulong(addr), ctypes.byref(idx)) == 0 and idx.value:
            if not _is_tun_index(int(idx.value)):
                return int(idx.value)
    except Exception:
        pass
    # запасной путь: маршрут по умолчанию с наименьшей метрикой, кроме нашего TUN
    from ..winutil import powershell
    code, out = powershell(
        "Get-NetRoute -DestinationPrefix 0.0.0.0/0 | Where-Object { $_.InterfaceAlias -notlike '*%s*' } | "
        "Sort-Object { $_.RouteMetric + $_.InterfaceMetric } | Select-Object -First 1 -ExpandProperty ifIndex" % C.TUN_NAME,
        timeout=20)
    try:
        return int(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def _is_tun_index(idx: int) -> bool:
    try:
        return C.TUN_NAME.lower() in socket.if_indextoname(idx).lower()
    except Exception:
        return False


# ---------------- системный прокси Windows ----------------
_REG = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _proxy_read():
    import winreg
    out = {}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG) as k:
        for n in ("ProxyEnable", "ProxyServer", "ProxyOverride"):
            try:
                out[n] = winreg.QueryValueEx(k, n)[0]
            except OSError:
                out[n] = None
    return out


def _proxy_write(vals: dict):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG, 0, winreg.KEY_SET_VALUE) as k:
        for n, v in vals.items():
            if v is None:
                try:
                    winreg.DeleteValue(k, n)
                except OSError:
                    pass
            elif n == "ProxyEnable":
                winreg.SetValueEx(k, n, 0, winreg.REG_DWORD, int(v))
            else:
                winreg.SetValueEx(k, n, 0, winreg.REG_SZ, str(v))
    try:
        wi = ctypes.windll.wininet
        wi.InternetSetOptionW(None, 39, None, 0)   # SETTINGS_CHANGED
        wi.InternetSetOptionW(None, 37, None, 0)   # REFRESH
    except Exception:
        pass


def set_system_proxy(port: int):
    if not IS_WIN:
        return
    if not settings.get("vpn_proxy_backup"):
        settings.set("vpn_proxy_backup", _proxy_read())
    _proxy_write({"ProxyEnable": 1, "ProxyServer": f"127.0.0.1:{port}",
                  "ProxyOverride": "localhost;127.*;10.*;192.168.*;172.16.*;172.17.*;172.18.*;172.2*;172.30.*;"
                                   "172.31.*;*.local;<local>"})


def restore_system_proxy():
    if not IS_WIN:
        return
    b = settings.get("vpn_proxy_backup")
    if not b:
        return
    try:
        _proxy_write({"ProxyEnable": b.get("ProxyEnable") or 0, "ProxyServer": b.get("ProxyServer"),
                      "ProxyOverride": b.get("ProxyOverride")})
    except OSError:
        return
    settings.set("vpn_proxy_backup", None)


# ---------------- хранилище ----------------
class VpnStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        d = {}
        try:
            d = json.loads(path.read_text("utf-8"))
        except Exception:
            pass
        self.servers: list[dict] = d.get("servers", [])
        self.subs: list[dict] = d.get("subs", [])
        self.selected: str | None = d.get("selected")
        self.domains: list[str] = d.get("domains", [])        # вручную «через VPN»
        self.direct: list[str] = d.get("direct", [])          # «всегда напрямую»
        self.auto: dict = d.get("auto", {})                   # выучено: {domain: {"ts", "host"}}
        self.packs: list[str] = d.get("packs", [])
        self.apps: list[dict] = d.get("apps", [])             # [{"name","path","via": vpn|direct}]
        self.flags: dict = d.get("flags", {})
        if not self.flags.get("tg_pack"):
            # 2.2.1: Telegram в России ограничен — набор включаем один раз (можно снять галочку)
            self.flags["tg_pack"] = True
            if "telegram" not in self.packs:
                self.packs.append("telegram")

    def save(self):
        with self.lock:
            data = {"servers": self.servers, "subs": self.subs, "selected": self.selected, "domains": self.domains,
                    "direct": self.direct, "auto": self.auto, "packs": self.packs, "apps": self.apps,
                    "flags": self.flags}
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
            tmp.replace(self.path)

    def server(self, sid=None):
        sid = sid or self.selected
        return next((s for s in self.servers if s["id"] == sid), None)

    def vpn_domains(self) -> list[str]:
        out = list(self.domains) + list(self.auto)
        for k in self.packs:
            out += C.PACKS.get(k, ("", []))[1]
        dset = set(self.direct)
        return [d for d in out if d not in dset]

    def vpn_cidrs(self) -> list[str]:
        out = []
        for k in self.packs:
            out += C.PACK_CIDRS.get(k, [])
        return out

    def direct_domains(self, ru: bool) -> list[str]:
        return list(self.direct) + (C.RU_SUFFIX if ru else [])

    def add_servers(self, servers, sub=None):
        added = 0
        with self.lock:
            have = {s["id"] for s in self.servers}
            for s in servers:
                if sub:
                    s["sub"] = sub
                if s["id"] not in have:
                    self.servers.append(s)
                    have.add(s["id"])
                    added += 1
            if not self.selected and self.servers:
                self.selected = self.servers[0]["id"]
        self.save()
        return added


# ---------------- менеджер ----------------
class VpnManager(QObject):
    state_changed = pyqtSignal()
    servers_changed = pyqtSignal()
    lists_changed = pyqtSignal()
    learned = pyqtSignal(str)
    toast = pyqtSignal(str, str)
    install_progress = pyqtSignal(float)
    stats = pyqtSignal()

    def __init__(self, data: Path):
        super().__init__()
        self.data = data
        self.dir = data / "vpn"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.store = VpnStore(data / "vpn.json")
        try:
            self.store.save()
        except OSError:
            pass
        self.proc: subprocess.Popen | None = None
        self.state = "off"           # off | starting | on | stopping
        self.error = ""
        self.mode = None             # режим текущего запуска
        self.route = None
        self.ports = {}
        self.secret = secrets.token_hex(12)
        self.phys_idx = None
        self.installing = False
        self.pings: dict[str, int] = {}
        self.now_vpn: dict[str, int] = {}     # сайты, идущие через VPN прямо сейчас {host: соединений}
        self.now_direct = 0
        self.traffic = (0, 0)
        self.speed = (0, 0)
        self._last_tr = None
        self._conns = {}
        self._neg = {}
        self._checking = set()
        self._poll_busy = False
        self._started_at = 0
        self._stop_req = False
        self._lock = threading.Lock()
        self._log = deque(maxlen=300)
        self._sus = deque(maxlen=200)
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._poll_tick)
        self._health = QTimer(self)
        self._health.timeout.connect(self._health_tick)
        self._slow = QTimer(self)
        self._slow.timeout.connect(self._slow_tick)
        self._slow.start(30 * 60 * 1000)
        # прокси мог остаться после аварийного завершения
        if not self._find_stray():
            restore_system_proxy()
        self.write_rulesets()

    # ---- установка ядра ----
    @property
    def exe(self) -> Path:
        env = os.environ.get("ZC_SINGBOX")
        if env:
            return Path(env)
        return engine_dir() / "vpn" / ("sing-box.exe" if IS_WIN else "sing-box")

    def installed(self) -> bool:
        return self.exe.exists()

    def install(self):
        """Скачать sing-box (выполняется в фоне)."""
        self.installing = True
        try:
            req = urllib.request.Request(SB_URL, headers={"User-Agent": "ZapretCloud"})
            with urllib.request.urlopen(req, timeout=30) as r:
                total = int(r.headers.get("Content-Length") or 0)
                buf = io.BytesIO()
                got = 0
                while True:
                    ch = r.read(256 * 1024)
                    if not ch:
                        break
                    buf.write(ch)
                    got += len(ch)
                    if total:
                        self.install_progress.emit(got / total)
            z = zipfile.ZipFile(buf)
            dst = self.exe.parent
            dst.mkdir(parents=True, exist_ok=True)
            for n in z.namelist():
                fn = n.rsplit("/", 1)[-1]
                if fn in ("sing-box.exe", "libcronet.dll", "LICENSE"):
                    tmp = dst / (fn + ".new")
                    tmp.write_bytes(z.read(n))
                    tmp.replace(dst / fn)
            if not self.exe.exists():
                raise RuntimeError("sing-box.exe не найден в архиве")
            return True
        finally:
            self.installing = False

    # ---- списки ----
    def write_rulesets(self):
        C.write_ruleset(self.dir / "rs_vpn.json", self.store.vpn_domains())
        C.write_ruleset(self.dir / "rs_vpn_ip.json", [], self.store.vpn_cidrs())
        C.write_ruleset(self.dir / "rs_direct.json", self.store.direct_domains(bool(settings.get("vpn_ru_direct"))))

    def lists_updated(self, need_restart=False):
        """Списки изменились: sing-box подхватывает файлы сам, перезапуск нужен только для правил программ."""
        self.store.save()
        self.write_rulesets()
        self.lists_changed.emit()
        if need_restart and self.running():
            self.restart()

    def add_domain(self, d, direct=False):
        from ..sites import normalize
        try:
            d = normalize(d)
        except Exception:
            d = (d or "").strip().lower()
        if not d or "." not in d:
            return False
        lst = self.store.direct if direct else self.store.domains
        other = self.store.domains if direct else self.store.direct
        if d in other:
            other.remove(d)
        if d not in lst:
            lst.append(d)
        self.store.auto.pop(d, None)
        self.lists_updated()
        return True

    # ---- состояние ----
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def active_mode(self):
        return self.mode if self.state == "on" else None

    def winws_args(self) -> list[str]:
        """Для zapret: при TUN обрабатывать только физический интерфейс (иначе пакеты попадут в обработку дважды)."""
        if self.state in ("on", "starting") and self.mode == "tun" and self.phys_idx:
            return [f"--wf-iface={self.phys_idx}"]
        return []

    def _find_stray(self) -> bool:
        try:
            import psutil
            me = str(self.exe).lower()
            for p in psutil.process_iter(["name", "exe"]):
                if (p.info["name"] or "").lower() in ("sing-box.exe", "sing-box") and (p.info["exe"] or "").lower() == me:
                    return True
        except Exception:
            pass
        return False

    def _wait_tun_gone(self, timeout=10.0):
        """Ждём, пока Windows удалит TUN-адаптер прошлого запуска: новый с тем же именем
        при живом старом зависает на «open interface take too much time»."""
        try:
            import psutil
        except Exception:
            return
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if not any(C.TUN_NAME.lower() in n.lower() for n in psutil.net_if_stats()):
                    return
            except Exception:
                return
            time.sleep(0.5)

    def _kill_stray(self):
        killed = []
        try:
            import psutil
            me = str(self.exe).lower()
            for p in psutil.process_iter(["name", "exe"]):
                if (p.info["name"] or "").lower() in ("sing-box.exe", "sing-box") and (p.info["exe"] or "").lower() == me:
                    p.kill()
                    killed.append(p)
            if killed:
                # ждём, пока Windows освободит TUN-адаптер, иначе новый зависает на
                # «open interface take too much time»
                psutil.wait_procs(killed, timeout=5)
                time.sleep(1.5)
        except Exception:
            pass

    # ---- запуск ----
    def start_blocking(self) -> tuple[bool, str]:
        try:
            from ..conflicts import other_vpn
            other = other_vpn(adapters=False)
        except Exception:
            other = ""
        if other:
            return False, tr("Запущен другой VPN") + f" ({other}). " + \
                tr("Два VPN одновременно не работают — закройте его и включите VPN снова.")
        # Первый запуск TUN в Windows часто падает (адаптер прошлого запуска ещё не удалён,
        # сеть не готова, wintun не успел инициализироваться). Повторяем автоматически —
        # то же, что делает кнопка «Починить VPN».
        fatal = (tr("Добавьте сервер"), tr("Компонент VPN не установлен"), tr("Ошибка конфигурации"))
        tries = 3 if (settings.get("vpn_mode") or "tun") == "tun" else 2
        ok, msg = False, ""
        for i in range(tries):
            ok, msg = self._start_once()
            if ok or msg.startswith(fatal):
                break
            self._start_err(i + 1, msg)
            if "already exists" in msg or "Element not found" in msg:
                # в Windows остался «призрачный» адаптер с этим именем (после сбоя/обновления)
                # — его нельзя ни создать, ни открыть. Берём следующее имя.
                self._next_tun_name()
            self._stop_proc()
            self._kill_stray()
            self._wait_tun_gone(15)
            time.sleep(2 + i * 2)
        return ok, msg

    TUN_NAMES = (C.TUN_NAME, C.TUN_NAME + "2", C.TUN_NAME + "3", C.TUN_NAME + "4")

    def tun_name(self) -> str:
        n = settings.get("vpn_tun_name") or C.TUN_NAME
        return n if n in self.TUN_NAMES else C.TUN_NAME

    def _next_tun_name(self):
        names = self.TUN_NAMES
        settings.set("vpn_tun_name", names[(names.index(self.tun_name()) + 1) % len(names)])

    def _start_err(self, attempt: int, msg: str):
        """Журнал неудачных попыток запуска — для диагностики (vpn/start-errors.log)."""
        try:
            f = self.dir / "start-errors.log"
            if f.exists() and f.stat().st_size > 200_000:
                f.unlink()
            with f.open("a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} attempt {attempt}: {msg}\n")
                fh.write("    " + "\n    ".join(list(self._log)[-15:]) + "\n")
        except Exception:
            pass

    def _start_once(self) -> tuple[bool, str]:
        with self._lock:
            srv = self.store.server()
            if not srv:
                return False, tr("Добавьте сервер")
            if not self.installed():
                return False, tr("Компонент VPN не установлен")
            self._stop_proc()
            self._kill_stray()
            mode = settings.get("vpn_mode") or "tun"
            route = settings.get("vpn_route") or "smart"
            lan = bool(settings.get("vpn_lan"))
            self.ports = {"mixed": int(settings.get("vpn_port") or 10808) if lan else _free_port(int(settings.get("vpn_port") or 10808)),
                          "probe_direct": _free_port(0), "probe_vpn": _free_port(0), "api": _free_port(0)}
            if mode == "tun":
                self.phys_idx = best_iface_index()
            self.write_rulesets()
            learn = route == "smart" and bool(settings.get("vpn_learn"))
            cfg = C.build(srv["outbound"], mode=mode, route=route, ports=self.ports, secret=self.secret,
                          rs_vpn=self.dir / "rs_vpn.json", rs_direct=self.dir / "rs_direct.json",
                          rs_vpn_ip=self.dir / "rs_vpn_ip.json", lan=lan,
                          apps=self.store.apps, log_level="trace" if learn else "warn",
                          tun_name=self.tun_name(), probe_auth=PROBE_AUTH,
                          local_ips=lan_ips() if lan and mode == "tun" else ())
            path = self.dir / "config.json"
            path.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), "utf-8")
            code, out = run([str(self.exe), "check", "-c", str(path), "--disable-color"], timeout=20)
            if code != 0:
                return False, tr("Ошибка конфигурации") + ": " + out.strip()[-300:]
            if mode == "tun":
                self._wait_tun_gone()
            try:
                self.proc = subprocess.Popen([str(self.exe), "run", "-c", str(path), "-D", str(self.dir), "--disable-color"],
                                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                             cwd=str(self.dir), creationflags=CREATE_NO_WINDOW)
            except OSError as e:
                return False, str(e)
            self._log.clear()
            threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()
            self.mode, self.route = mode, route
            t0 = time.time()
            # создание TUN-адаптера в Windows иногда занимает 10–30 с (sing-box пишет
            # «take too much time», но продолжает) — не убиваем его раньше времени
            limit = 45 if mode == "tun" else 12
            while time.time() - t0 < limit:
                if self.proc.poll() is not None:
                    return False, tr("VPN не запустился") + ": " + self.log_tail()
                if self._api("/version", timeout=1) is not None:
                    break
                time.sleep(0.25)
            else:
                self._stop_proc()
                return False, tr("VPN не отвечает") + ": " + self.log_tail()
            if mode == "proxy":
                try:
                    set_system_proxy(self.ports["mixed"])
                except OSError as e:
                    return False, str(e)
            if lan:
                self._firewall(True)
            self._started_at = time.time()
            self._conns.clear()
            self._last_tr = None
            return True, ""

    def log_tail(self, n=4) -> str:
        lines = [l for l in self._log if "ERROR" in l or "FATAL" in l] or list(self._log)
        lines = [l.split("] ", 1)[-1] if "] " in l else l for l in lines]
        return " | ".join(lines[-n:])[-400:]

    def _save_log(self):
        try:
            (self.dir / "sing-box.log").write_text("\n".join(self._log), "utf-8")
        except OSError:
            pass

    def _reader(self, proc):
        """Читает вывод sing-box: журнал ошибок + быстрые обрывы соединений (сброс DPI) для умного режима."""
        dom, direct, skip = {}, {}, set()
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").rstrip()
            m = _LOG_RE.match(line)
            if not m:
                if line:
                    self._log.append(line)
                continue
            lvl, cid, el, unit, msg = m.groups()
            if lvl not in ("TRACE", "DEBUG"):
                self._log.append(line)
            if cid is None:
                continue
            if "probe-" in msg and "inbound connection" in msg:
                skip.add(cid)
            elif msg.startswith("router: sniffed protocol") and "domain: " in msg:
                dom[cid] = msg.rsplit("domain: ", 1)[1].strip()
            elif msg.startswith("outbound/direct[direct]: outbound connection to "):
                direct[cid] = msg.rsplit(" ", 1)[1]
            elif msg == "connection: connection download closed":
                tgt = direct.pop(cid, None)
                d = dom.pop(cid, None)
                if cid in skip:
                    skip.discard(cid)
                    continue
                quick = unit == "ms" or (unit == "s" and float(el) < 2.0)
                if tgt and quick and tgt.rsplit(":", 1)[-1] in WATCH_PORTS:
                    host = d or tgt.rsplit(":", 1)[0]
                    if host and not host.replace(".", "").isdigit() and ":" not in host:
                        self._sus.append(host)
            if len(dom) > 4000:
                dom.clear(); direct.clear(); skip.clear()
        self._save_log()

    def _stop_proc(self):
        p, self.proc = self.proc, None
        if p and p.poll() is None:
            try:
                p.terminate()
                p.wait(5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        restore_system_proxy()

    def stop_blocking(self):
        with self._lock:
            self._stop_proc()
            if settings.get("vpn_lan") or self.ports:
                self._firewall(False)
            self.now_vpn = {}
            self.speed = (0, 0)

    # асинхронные обёртки (сигналы — в основном потоке)
    def start(self, done=None):
        from ..core import run_async
        if self.state in ("starting", "stopping"):
            return
        self.state = "starting"
        self.error = ""
        self.state_changed.emit()

        def ok(r):
            good, msg = r
            self.state = "on" if good else "off"
            self.error = msg
            if good:
                self._poll.start(2000)
                self._health.start(3000)
                settings.set("vpn_was_on", True)
            else:
                self._stop_proc()
                self.toast.emit(msg, "error")
            self.state_changed.emit()
            if done:
                done(good)
        run_async(self.start_blocking, done=ok,
                  fail=lambda e: (setattr(self, "state", "off"), self.toast.emit(e, "error"), self.state_changed.emit()))

    def stop(self, done=None, remember=True):
        from ..core import run_async
        if self.state == "off" and not self.running():
            return
        self.state = "stopping"
        self._poll.stop()
        self._health.stop()
        self.state_changed.emit()
        if remember:
            settings.set("vpn_was_on", False)

        def fin(_):
            self.state = "off"
            self.mode = None
            self.state_changed.emit()
            if done:
                done()
        run_async(self.stop_blocking, done=fin, fail=lambda e: fin(None))

    def restart(self):
        if self.state == "on":
            self.stop(done=self.start, remember=False)

    def repair(self):
        """«Починить VPN»: остановить, убрать зависшие процессы sing-box и запустить заново."""
        from ..core import run_async
        if self.state in ("starting", "stopping"):
            return
        self.state = "stopping"
        self._poll.stop()
        self._health.stop()
        self.state_changed.emit()

        def work():
            self.stop_blocking()
            self._kill_stray()
            time.sleep(1)

        def fin(_):
            self.state = "off"
            self.mode = None
            self.state_changed.emit()
            self.start()
        run_async(work, done=fin, fail=lambda e: fin(None))

    def toggle(self):
        self.stop() if self.state in ("on", "starting") else self.start()

    def shutdown(self):
        """Выход из программы: синхронно."""
        self._poll.stop()
        self._health.stop()
        self.stop_blocking()

    # ---- API sing-box (Clash API) ----
    def _api(self, path, timeout=2):
        if not self.ports.get("api"):
            return None
        req = urllib.request.Request(f"http://127.0.0.1:{self.ports['api']}{path}",
                                     headers={"Authorization": f"Bearer {self.secret}"})
        op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with op.open(req, timeout=timeout) as r:
                return json.loads(r.read() or b"{}")
        except Exception:
            return None

    def _health_tick(self):
        if self.state == "on" and not self.running():
            self._poll.stop()
            self._health.stop()
            err = self.log_tail()
            restore_system_proxy()
            self.state = "off"
            self.mode = None
            try:
                from ..conflicts import other_vpn
                other = other_vpn()
            except Exception:
                other = ""
            if other:
                self.toast.emit(tr("VPN отключился: запущен другой VPN") + f" ({other}). " +
                                tr("Два VPN одновременно не работают — закройте его и включите VPN снова."), "error")
            else:
                self.toast.emit(tr("VPN неожиданно отключился") + (f": {err}" if err else ""), "error")
            self.state_changed.emit()

    # ---- наблюдение за соединениями и умная маршрутизация ----
    def _poll_tick(self):
        if self._poll_busy or self.state != "on":
            return
        self._poll_busy = True
        from ..core import run_async
        run_async(self._api, "/connections", done=self._on_conns,
                  fail=lambda e: setattr(self, "_poll_busy", False))

    def _on_conns(self, d):
        self._poll_busy = False
        if not d or self.state != "on":
            return
        now = time.time()
        up, down = d.get("uploadTotal", 0), d.get("downloadTotal", 0)
        if self._last_tr:
            t, u0, d0 = self._last_tr
            dt = max(0.5, now - t)
            self.speed = (max(0, int((up - u0) / dt)), max(0, int((down - d0) / dt)))
        self._last_tr = (now, up, down)
        self.traffic = (up, down)
        vpn, ndirect, seen = {}, 0, set()
        learn = self.route == "smart" and settings.get("vpn_learn")
        for c in d.get("connections") or []:
            md = c.get("metadata") or {}
            typ = md.get("type", "")
            if "probe-" in typ:
                continue
            host = md.get("host") or md.get("destinationIP") or ""
            chains = c.get("chains") or []
            if "proxy" in chains:
                if host:
                    h = base_domain(host) if md.get("host") else host
                    vpn[h] = vpn.get(h, 0) + 1
                continue
            ndirect += 1
            if not learn or not md.get("host") or str(md.get("destinationPort")) not in WATCH_PORTS:
                continue
            cid = c.get("id")
            seen.add(cid)
            prev = self._conns.get(cid)
            start = prev[3] if prev else now
            self._conns[cid] = (md["host"], c.get("upload", 0), c.get("download", 0), start)
            if c.get("download", 0) == 0 and c.get("upload", 0) > 0 and now - start >= 5:
                self._suspect(md["host"])
        for cid in list(self._conns):
            if cid not in seen:
                host, u, dn, st = self._conns.pop(cid)
                if dn == 0 and u > 0:
                    self._suspect(host)
        while learn and self._sus:
            self._suspect(self._sus.popleft())
        self.now_vpn = dict(sorted(vpn.items(), key=lambda x: -x[1]))
        self.now_direct = ndirect
        self.stats.emit()

    def _suspect(self, host):
        b = base_domain(host)
        now = time.time()
        if b in self._checking or len(self._checking) >= 4:
            return
        if now - self._neg.get(b, 0) < NEG_TTL:
            return
        vd = set(self.store.vpn_domains()) | set(self.store.direct)
        if b in vd or host in vd:
            return
        self._checking.add(b)
        from ..core import run_async

        def work():
            if tls_probe(host, self.ports["probe_direct"]):
                return "direct"
            if tls_probe(host, self.ports["probe_vpn"], timeout=8):
                return "vpn"
            return "down"

        def done(r):
            self._checking.discard(b)
            if r == "vpn" and self.state == "on":
                self.store.auto[b] = {"ts": time.time(), "host": host}
                self.lists_updated()
                self.learned.emit(b)
            else:
                self._neg[b] = time.time()
        run_async(work, done=done, fail=lambda e: self._checking.discard(b))

    def _slow_tick(self):
        """Раз в 30 мин: обновить подписки, перепроверить «авто»-сайты (вернуть на zapret, если снова открываются)."""
        if self.state != "on":
            return
        self.refresh_subs(only_old=True)
        now = time.time()
        old = [(d, v) for d, v in self.store.auto.items() if now - v.get("checked", v.get("ts", 0)) > RECHECK_AUTO]
        if not old:
            return
        from ..core import run_async

        def work():
            back = []
            for d, v in old[:20]:
                if tls_probe(v.get("host") or d, self.ports["probe_direct"]):
                    back.append(d)
            return back

        def done(back):
            for d, v in old[:20]:
                if d in self.store.auto:
                    self.store.auto[d]["checked"] = now
            for d in back:
                self.store.auto.pop(d, None)
            self.lists_updated()
        run_async(work, done=done)

    def forget_auto(self):
        self.store.auto.clear()
        self._neg.clear()
        self.lists_updated()

    # ---- серверы, подписки, пинг ----
    def add_input(self, text, done):
        """Ссылка(и) или ссылка подписки. done(added, errors, msg)."""
        from ..core import run_async
        text = (text or "").strip()
        if L.is_subscription(text):
            def work():
                return self._fetch_sub(text)

            def ok(r):
                servers, errors, info = r
                sub = next((s for s in self.store.subs if s["url"] == text), None)
                if not sub:
                    sub = {"id": L.sid(text), "url": text}
                    self.store.subs.append(sub)
                sub.update({"name": info.get("title") or sub.get("name") or text.split("/")[2], "info": info,
                            "updated": time.time()})
                n = self._replace_sub(sub["id"], servers)
                self.servers_changed.emit()
                done(n, errors, "")
            run_async(work, done=ok, fail=lambda e: done(0, [str(e)], ""))
            return
        servers, errors = L.parse_text(text)
        n = self.store.add_servers(servers)
        if servers and n == 0 and not errors:
            errors = [tr("Этот сервер уже добавлен")]
        self.servers_changed.emit()
        done(n, errors, "")

    def _fetch_sub(self, url):
        try:
            return L.fetch_subscription(url)
        except L.LinkError:
            raise
        except Exception as e:  # noqa
            if self.state == "on" and self.ports.get("probe_vpn"):
                return L.fetch_subscription(url, proxy=probe_proxy_url(self.ports['probe_vpn']))
            raise RuntimeError(tr("Не удалось загрузить подписку") + f": {e}")

    def _replace_sub(self, sub_id, servers):
        with self.store.lock:
            sel = self.store.server()
            keep = [s for s in self.store.servers if s.get("sub") != sub_id]
            for s in servers:
                s["sub"] = sub_id
            self.store.servers = keep + servers
            if sel and sel.get("sub") == sub_id and not self.store.server(sel["id"]):
                # выбранный сервер пропал из подписки — берём похожий по имени или первый
                alt = next((s for s in servers if s["name"] == sel["name"]), servers[0] if servers else None)
                self.store.selected = alt["id"] if alt else (keep[0]["id"] if keep else None)
            if not self.store.selected and self.store.servers:
                self.store.selected = self.store.servers[0]["id"]
        self.store.save()
        return len(servers)

    def refresh_subs(self, only_old=False, done=None):
        from ..core import run_async
        subs = [s for s in self.store.subs if not only_old or time.time() - s.get("updated", 0) > SUB_REFRESH]
        if not subs:
            if done:
                done([])
            return
        sel_before = self.store.server()

        def work():
            res = []
            for s in subs:
                try:
                    res.append((s, self._fetch_sub(s["url"]), None))
                except Exception as e:  # noqa
                    res.append((s, None, str(e)))
            return res

        def ok(res):
            errs = []
            for s, r, err in res:
                if err:
                    errs.append(f"{s.get('name')}: {err}")
                    continue
                servers, _e, info = r
                if servers:
                    s.update({"info": info, "updated": time.time()})
                    if info.get("title"):
                        s["name"] = info["title"]
                    self._replace_sub(s["id"], servers)
            self.store.save()
            self.servers_changed.emit()
            new = self.store.server()
            if self.state == "on" and sel_before and new and new["outbound"] != sel_before["outbound"]:
                self.restart()
            if done:
                done(errs)
        run_async(work, done=ok)

    def remove_server(self, sid):
        with self.store.lock:
            self.store.servers = [s for s in self.store.servers if s["id"] != sid]
            if self.store.selected == sid:
                self.store.selected = self.store.servers[0]["id"] if self.store.servers else None
        self.store.save()
        self.servers_changed.emit()

    def remove_sub(self, sub_id):
        with self.store.lock:
            self.store.subs = [s for s in self.store.subs if s["id"] != sub_id]
        self._replace_sub(sub_id, [])
        self.servers_changed.emit()

    def select(self, sid):
        if self.store.selected == sid:
            return
        self.store.selected = sid
        self.store.save()
        self.servers_changed.emit()
        if self.state == "on":
            self.restart()

    def ping_all(self, done=None):
        from ..core import run_async
        from concurrent.futures import ThreadPoolExecutor
        servers = list(self.store.servers)

        def work():
            with ThreadPoolExecutor(16) as ex:
                return dict(zip([s["id"] for s in servers],
                                ex.map(lambda s: tcp_ping(s["host"], s["port"]), servers)))

        def ok(r):
            self.pings.update(r)
            self.servers_changed.emit()
            if done:
                done()
        run_async(work, done=ok)

    def real_delay(self, done):
        """Задержка через VPN (HTTP-запрос через сервер)."""
        from ..core import run_async

        def work():
            r = self._api("/proxies/proxy/delay?timeout=5000&url=https%3A%2F%2Fwww.gstatic.com%2Fgenerate_204", timeout=7)
            return (r or {}).get("delay", -1)
        run_async(work, done=done, fail=lambda e: done(-1))

    # ---- локальная сеть (раздача на телефон) ----
    def _firewall(self, on: bool):
        if not IS_WIN:
            return
        run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={FW_RULE}"], timeout=15)
        if on:
            run(["netsh", "advfirewall", "firewall", "add", "rule", f"name={FW_RULE}", "dir=in", "action=allow",
                 f"program={self.exe}", "protocol=TCP", f"localport={self.ports.get('mixed', 10808)}",
                 "remoteip=localsubnet", "profile=any", "enable=yes"], timeout=15)

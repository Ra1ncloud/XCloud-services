"""Поиск программ, мешающих работе zapret: другие DPI-обходчики, чужие winws/WinDivert, VPN."""
import re

from .winutil import IS_WIN, run

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

# процесс -> понятное название
PROCESSES = {
    "goodbyedpi.exe": "GoodbyeDPI",
    "winws.exe": "winws (другой zapret)",
    "winws2.exe": "winws2 (другой zapret)",
    "zapret.exe": "Zapret GUI",
    "zapretstudio.exe": "Zapret Studio",
    "ciadpi.exe": "ByeDPI",
    "byedpi.exe": "ByeDPI",
    "spoofdpi.exe": "SpoofDPI",
    "nodpi.exe": "NoDPI",
    "dpitunnel.exe": "DPI Tunnel",
    "powertunnel.exe": "PowerTunnel",
}
# службы, которые держат свой WinDivert или обход
SERVICES = {
    "goodbyedpi": "GoodbyeDPI (служба)",
    "zapret": "zapret (служба Flowseal)",
    "windivert": "WinDivert (чужой драйвер)",
    "windivert14": "WinDivert 1.4 (чужой драйвер)",
    "winws1": "winws (служба)",
    "winws2": "winws2 (служба)",
}
VPN_RE = re.compile(r"vpn|wireguard|\bwg\d*\b|wintun|\btap\b|tap-|\btun\b|openvpn|warp|proton|nord|outline|amnezia|"
                    r"hamachi|radmin|zerotier|tailscale|happ|v2ray|hiddify|nekoray|sing-?box", re.I)


VPN_APPS_RE = re.compile(r"^(happ|hiddify|v2rayn|nekoray|nekobox|amneziavpn|amneziawg|outline|wireguard|"
                         r"protonvpn|nordvpn|warp-svc|cloudflare warp|windscribe|expressvpn|clash.*|flclash|karing)(\.exe)?$", re.I)


def other_vpn(adapters: bool = True) -> str:
    """Название стороннего VPN, если он сейчас запущен (процесс или поднятый сетевой адаптер), иначе ""."""
    if not psutil:
        return ""
    try:
        for p in psutil.process_iter(["name"]):
            n = p.info.get("name") or ""
            if VPN_APPS_RE.match(n):
                return n.rsplit(".", 1)[0]
    except Exception:
        pass
    if not adapters:
        return ""
    try:
        for name, st in psutil.net_if_stats().items():
            if st.isup and VPN_RE.search(name) and "zapretcloud" not in name.lower():
                return name
    except Exception:
        pass
    return ""


def detect(own_pids=()) -> list[dict]:
    res = []
    own = set(own_pids or ())
    if psutil:
        try:
            for p in psutil.process_iter(["name", "pid"]):
                n = (p.info.get("name") or "").lower()
                if n in PROCESSES and p.info["pid"] not in own:
                    res.append({"kind": "process", "id": n, "pid": p.info["pid"], "title": PROCESSES[n], "blocking": True})
        except Exception:
            pass
        if IS_WIN:
            try:
                for s in psutil.win_service_iter():
                    n = s.name().lower()
                    if n in SERVICES:
                        try:
                            st = s.status()
                        except Exception:
                            st = ""
                        if st in ("running", "start_pending"):
                            res.append({"kind": "service", "id": s.name(), "title": SERVICES[n], "blocking": True})
            except Exception:
                pass
        try:
            for name, st in psutil.net_if_stats().items():
                if st.isup and VPN_RE.search(name) and "zapretcloud" not in name.lower():
                    res.append({"kind": "vpn", "id": name, "title": f"VPN: {name}", "blocking": False})
        except Exception:
            pass
    # один и тот же процесс может встречаться несколько раз — сворачиваем
    seen, out = set(), []
    for r in res:
        k = (r["kind"], r["id"], r.get("pid"))
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def stop(items: list[dict]) -> list[str]:
    """Останавливает мешающие процессы и службы. Возвращает список ошибок."""
    errors = []
    for it in items:
        try:
            if it["kind"] == "process":
                if psutil:
                    psutil.Process(it["pid"]).kill()
                elif IS_WIN:
                    run(["taskkill", "/F", "/PID", str(it["pid"])], timeout=10)
            elif it["kind"] == "service" and IS_WIN:
                code, out = run(["sc", "stop", it["id"]], timeout=15)
                if it["id"].lower().startswith("windivert"):
                    run(["sc", "delete", it["id"]], timeout=10)
        except Exception as e:  # noqa
            errors.append(f"{it['title']}: {e}")
    return errors

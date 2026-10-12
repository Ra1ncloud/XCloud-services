"""Проверки доступности сайтов и сервисов."""
import json
import os
import socket
import ssl
import struct
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict

CATEGORIES = ["youtube", "discord", "telegram", "games", "ai", "custom"]


@dataclass
class Target:
    id: str
    name: str
    category: str
    kind: str          # https | download | tcp | stun
    host: str
    port: int = 443
    path: str = "/"
    min_bytes: int = 0
    required: bool = True


DEFAULT_TARGETS = [
    Target("yt_web", "YouTube", "youtube", "https", "www.youtube.com"),
    Target("yt_img", "YouTube превью (загрузка)", "youtube", "download", "i.ytimg.com",
           path="/vi/dQw4w9WgXcQ/maxresdefault.jpg", min_bytes=40000),
    Target("yt_cdn", "YouTube видео-CDN", "youtube", "https", "redirector.googlevideo.com", path="/report_mapping"),
    Target("ds_web", "Discord", "discord", "https", "discord.com"),
    Target("ds_gw", "Discord Gateway", "discord", "https", "gateway.discord.gg"),
    Target("ds_cdn", "Discord CDN", "discord", "https", "cdn.discordapp.com"),
    Target("ds_upd", "Discord обновления", "discord", "https", "updates.discord.com"),
    Target("ds_voice", "Голос / звонки (UDP STUN)", "discord", "stun", "stun.l.google.com", 19302, required=False),
    Target("tg_web", "Telegram Web", "telegram", "https", "web.telegram.org"),
    Target("tg_tme", "t.me", "telegram", "https", "t.me"),
    Target("tg_dc2", "Telegram DC2", "telegram", "tcp", "149.154.167.51", 443),
    Target("tg_dc4", "Telegram DC4", "telegram", "tcp", "149.154.167.91", 443),
    Target("gm_steam", "Steam магазин", "games", "https", "store.steampowered.com"),
    Target("gm_steamc", "Steam Community", "games", "https", "steamcommunity.com"),
    Target("gm_roblox", "Roblox", "games", "https", "www.roblox.com"),
    Target("gm_rbxapi", "Roblox API", "games", "https", "apis.roblox.com"),
    Target("gm_epic", "Epic Games", "games", "https", "store.epicgames.com"),
    Target("ai_gpt", "ChatGPT", "ai", "https", "chatgpt.com"),
    Target("ai_claude", "Claude", "ai", "https", "claude.ai"),
    Target("ai_gemini", "Gemini", "ai", "https", "gemini.google.com"),
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def custom_targets(entries) -> list[Target]:
    res = []
    for e in entries or []:
        host = str(e).strip().replace("https://", "").replace("http://", "").split("/")[0]
        if host:
            port = 443
            if ":" in host:
                host, p = host.rsplit(":", 1)
                port = int(p) if p.isdigit() else 443
            kind = "https" if port == 443 else "tcp"
            res.append(Target("c_" + host, host, "custom", kind, host, port))
    return res


@dataclass
class Result:
    target_id: str
    ok: bool
    ms: int
    detail: str


def _ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def check_https(t: Target, timeout: float) -> tuple[bool, str]:
    try:
        ip = socket.gethostbyname(t.host)
    except OSError:
        return False, "DNS: не разрешается"
    try:
        s = socket.create_connection((ip, t.port), timeout=timeout)
    except socket.timeout:
        return False, "TCP: таймаут"
    except OSError as e:
        return False, f"TCP: {e.strerror or e}"
    try:
        s.settimeout(timeout)
        ss = _ctx().wrap_socket(s, server_hostname=t.host)
    except socket.timeout:
        s.close()
        return False, "TLS: таймаут (блокировка DPI)"
    except (ssl.SSLError, OSError) as e:
        s.close()
        return False, "TLS: сброс соединения" if isinstance(e, ConnectionResetError) else f"TLS: {e.__class__.__name__}"
    try:
        req = (f"GET {t.path} HTTP/1.1\r\nHost: {t.host}\r\nUser-Agent: {UA}\r\n"
               f"Accept: */*\r\nConnection: close\r\n\r\n").encode()
        ss.sendall(req)
        data = b""
        need = max(t.min_bytes, 1)
        closed = False
        try:
            while len(data) < need + 512:
                chunk = ss.recv(16384)
                if not chunk:
                    closed = True
                    break
                data += chunk
                if t.kind == "https" and b"\r\n" in data:
                    break
        except socket.timeout:
            if not data:
                raise
            if t.kind == "download":
                body = len(data.split(b"\r\n\r\n", 1)[-1])
                return False, f"обрыв после {body // 1024} КБ"
        line = data.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        if not line.startswith("HTTP/"):
            return False, "HTTP: нет ответа"
        code = line.split(" ")[1] if " " in line else "?"
        if t.kind == "download":
            body = len(data.split(b"\r\n\r\n", 1)[-1])
            if body < t.min_bytes and not closed:
                return False, f"обрыв после {body // 1024} КБ"
            return True, f"HTTP {code}, {body // 1024} КБ"
        return True, f"HTTP {code}"
    except socket.timeout:
        return False, "HTTP: таймаут (замедление/обрыв)"
    except (ssl.SSLError, OSError) as e:
        return False, f"HTTP: {e.__class__.__name__}"
    finally:
        try:
            ss.close()
        except Exception:
            pass


def check_tcp(t: Target, timeout: float) -> tuple[bool, str]:
    try:
        s = socket.create_connection((t.host, t.port), timeout=timeout)
        s.close()
        return True, "TCP OK"
    except socket.timeout:
        return False, "TCP: таймаут"
    except OSError as e:
        return False, f"TCP: {e.strerror or e}"


def check_stun(t: Target, timeout: float) -> tuple[bool, str]:
    try:
        ip = socket.gethostbyname(t.host)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        tid = os.urandom(12)
        s.sendto(struct.pack("!HHI", 0x0001, 0, 0x2112A442) + tid, (ip, t.port))
        data, _ = s.recvfrom(2048)
        s.close()
        return (data[8:20] == tid), "UDP OK" if data[8:20] == tid else "UDP: неверный ответ"
    except socket.timeout:
        return False, "UDP: таймаут"
    except OSError as e:
        return False, f"UDP: {e}"


def check(t: Target, timeout: float = 5.0) -> Result:
    t0 = time.perf_counter()
    fn = {"https": check_https, "download": check_https, "tcp": check_tcp, "stun": check_stun}[t.kind]
    try:
        ok, detail = fn(t, timeout)
    except Exception as e:  # noqa
        ok, detail = False, str(e)
    return Result(t.id, ok, int((time.perf_counter() - t0) * 1000), detail)


def run_checks(targets: list[Target], timeout: float = 5.0, workers: int = 12) -> dict[str, Result]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return {r.target_id: r for r in ex.map(lambda t: check(t, timeout), targets)}


def summarize(targets: list[Target], results: dict[str, Result]) -> dict:
    cats = {}
    for t in targets:
        c = cats.setdefault(t.category, [0, 0])
        r = results.get(t.id)
        c[1] += 1
        if r and r.ok:
            c[0] += 1
    req = [t for t in targets if t.required]
    ok = sum(1 for t in req if results.get(t.id) and results[t.id].ok)
    return {"ok": ok, "total": len(req), "score": round(100 * ok / len(req)) if req else 0,
            "cats": cats, "failed": [t.id for t in targets if not (results.get(t.id) and results[t.id].ok)]}


def detect_isp(timeout=6) -> dict:
    for url, mapper in (
        ("http://ip-api.com/json/?fields=status,isp,org,as,query,country,city&lang=ru",
         lambda d: {"isp": d.get("isp") or d.get("org"), "as": d.get("as", ""), "ip": d.get("query", ""),
                    "city": d.get("city", "")}),
        ("https://ipinfo.io/json", lambda d: {"isp": d.get("org", ""), "as": d.get("org", "").split(" ")[0],
                                              "ip": d.get("ip", ""), "city": d.get("city", "")}),
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = mapper(json.loads(r.read().decode("utf-8")))
                if d.get("isp"):
                    return d
        except Exception:
            continue
    return {"isp": "", "as": "", "ip": "", "city": ""}


def isp_key(info: dict) -> str:
    asn = (info.get("as") or "").split(" ")[0]
    return asn or info.get("isp") or "unknown"


# ---------- DNS-подмена ----------
def doh_resolve(name: str, timeout=5) -> list[str]:
    try:
        req = urllib.request.Request(f"https://dns.google/resolve?name={name}&type=A", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            d = json.loads(r.read().decode())
        return [a["data"] for a in d.get("Answer", []) if a.get("type") == 1]
    except Exception:
        return []


def system_resolve(name: str) -> list[str]:
    try:
        return sorted({i[4][0] for i in socket.getaddrinfo(name, 443, socket.AF_INET)})
    except OSError:
        return []


BOGUS_PREFIXES = ("0.", "127.", "10.", "192.168.", "195.208.", "62.33.207.", "95.167.13.", "188.186.157.")


def dns_check(names=("www.youtube.com", "discord.com", "web.telegram.org", "chatgpt.com", "steamcommunity.com")):
    rows = []
    for n in names:
        sys_ips = system_resolve(n)
        doh_ips = doh_resolve(n)
        bogus = (not sys_ips) or any(ip.startswith(BOGUS_PREFIXES) for ip in sys_ips)
        rows.append({"name": n, "system": sys_ips, "doh": doh_ips, "suspicious": bogus})
    return rows


def target_to_dict(t: Target):
    return asdict(t)

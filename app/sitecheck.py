"""«Сайт не открывается?» — пошаговая проверка: DNS → TCP → TLS (SNI) → HTTP."""
import socket
import ssl
import time

from . import sites as S
from .tester import BOGUS_PREFIXES, UA, system_resolve

VERDICTS = ("ok", "dns", "ip", "dpi", "http", "down", "bad")


def _tls(ip, host, timeout):
    t0 = time.perf_counter()
    s = socket.create_connection((ip, 443), timeout=timeout)
    s.settimeout(timeout)
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    ss = c.wrap_socket(s, server_hostname=host)
    return ss, int((time.perf_counter() - t0) * 1000)


def check(url: str, timeout: float = 6.0) -> dict:
    """Возвращает {"host", "steps": [(name, ok, detail)], "verdict", "ips"}."""
    host = S.normalize(url)
    res = {"host": host, "steps": [], "verdict": "bad", "ips": []}
    if not host:
        return res
    steps = res["steps"]
    if S.is_ip(host):
        sys_ips, doh_ips = [host], [host]
    else:
        # домен мог быть введён без www — пробуем как есть
        sys_ips = system_resolve(host)
        doh_ips = [ip for ip in S.resolve(host, timeout) if ":" not in ip]
        if not sys_ips and not doh_ips and not host.startswith("www."):
            sys_ips, doh_ips = system_resolve("www." + host), [ip for ip in S.resolve("www." + host, timeout) if ":" not in ip]
    res["ips"] = doh_ips or sys_ips
    bogus = bool(sys_ips) and all(ip.startswith(BOGUS_PREFIXES) for ip in sys_ips)
    if not sys_ips and not doh_ips:
        steps.append(("DNS", False, "домен не существует или DNS недоступен"))
        res["verdict"] = "down"
        return res
    if not sys_ips or bogus:
        steps.append(("DNS", False, f"системный DNS {'подменяет адрес: ' + ', '.join(sys_ips) if bogus else 'не отвечает'}; "
                                    f"настоящий: {', '.join(doh_ips[:3])}"))
        dns_blocked = True
    else:
        steps.append(("DNS", True, ", ".join(sys_ips[:3])))
        dns_blocked = False
    ip = (doh_ips or sys_ips)[0]
    # TCP
    t0 = time.perf_counter()
    try:
        s = socket.create_connection((ip, 443), timeout=timeout)
        s.close()
        steps.append(("TCP 443", True, f"{ip}, {int((time.perf_counter() - t0) * 1000)} мс"))
    except OSError as e:
        steps.append(("TCP 443", False, f"{ip}: {'таймаут' if isinstance(e, socket.timeout) else (e.strerror or e)}"))
        res["verdict"] = "ip"
        return res
    # TLS с SNI
    try:
        ss, ms = _tls(ip, host, timeout)
        steps.append(("TLS (SNI)", True, f"{ms} мс"))
    except socket.timeout:
        steps.append(("TLS (SNI)", False, "таймаут — похоже на блокировку DPI по имени сайта"))
        res["verdict"] = "dpi"
        return res
    except (ssl.SSLError, OSError) as e:
        steps.append(("TLS (SNI)", False, ("соединение сброшено — блокировка DPI" if isinstance(e, ConnectionResetError)
                                            else f"{e.__class__.__name__}")))
        res["verdict"] = "dpi"
        return res
    # HTTP
    try:
        ss.sendall((f"GET / HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {UA}\r\nAccept: */*\r\nConnection: close\r\n\r\n").encode())
        data = b""
        while b"\r\n" not in data and len(data) < 65536:
            chunk = ss.recv(16384)
            if not chunk:
                break
            data += chunk
        line = data.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        if line.startswith("HTTP/"):
            code = line.split(" ")[1] if " " in line else "?"
            steps.append(("HTTP", True, f"ответ {code}"))
            res["verdict"] = "dns" if dns_blocked else "ok"
            if code in ("451",):
                res["verdict"] = "http"
        else:
            steps.append(("HTTP", False, "сервер не ответил"))
            res["verdict"] = "http"
    except socket.timeout:
        steps.append(("HTTP", False, "таймаут — соединение замедляется или обрывается (DPI)"))
        res["verdict"] = "dpi"
    except (ssl.SSLError, OSError) as e:
        steps.append(("HTTP", False, e.__class__.__name__))
        res["verdict"] = "dpi"
    finally:
        try:
            ss.close()
        except Exception:
            pass
    return res

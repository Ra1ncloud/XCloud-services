"""Свои сайты для пресета: хранение, нормализация доменов, определение IP (DoH)
и подстановка отдельного блока в аргументы пресета при запуске."""
import hashlib
import ipaddress
import json
import re
import ssl
import threading
import urllib.request
from pathlib import Path

AUTO = ""   # автоматический выбор блока
CUSTOM_NAME = "ZapretCloud: мои сайты"

# глобальные опции движка — их не копируем в новый блок
_GLOBAL = ("--wf-", "--lua-init", "--lua-gc", "--ctrack", "--ipcache", "--blob", "--debug",
           "--intercept", "--dry-run", "--comment")
# опции фильтрации по спискам — заменяются своими
_LISTS = ("--hostlist", "--ipset", "--name")

_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$")


# ---------------------------------------------------------------- домены
def normalize(token: str) -> str | None:
    """'https://www.Site.рф/path?x' -> 'site.xn--p1ai'; IP-адреса тоже допускаются."""
    s = token.strip().strip(",;\"'").lower()
    if not s or s.startswith("#"):
        return None
    s = re.sub(r"^[a-z][a-z0-9+.-]*://", "", s)
    if re.match(r"^[0-9a-f:.]+/\d{1,3}$", s):
        try:
            return str(ipaddress.ip_network(s, strict=False))
        except ValueError:
            pass
    s = s.split("/")[0].split("?")[0].split("#")[0]
    s = s.rsplit("@", 1)[-1]
    try:
        net = ipaddress.ip_network(s, strict=False)
        return str(net) if "/" in s else str(net.network_address)
    except ValueError:
        pass
    if s.count(":") == 1:
        s = s.split(":")[0]
    s = s.strip(".")
    if s.startswith("*."):
        s = s[2:]
    if s.startswith("www."):
        s = s[4:]
    try:
        s = s.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    return s if _DOMAIN_RE.match(s) else None


def is_ip(s: str) -> bool:
    try:
        ipaddress.ip_network(s, strict=False)
        return True
    except ValueError:
        return False


def parse_input(text: str) -> tuple[list[str], list[str]]:
    """Разбирает ввод (строки, пробелы, запятые). Возвращает (корректные, ошибочные)."""
    good, bad = [], []
    for tok in re.split(r"[\s,;]+", text):
        if not tok.strip():
            continue
        n = normalize(tok)
        if n and n not in good:
            good.append(n)
        elif not n:
            bad.append(tok)
    return good, bad


def display(domain: str) -> str:
    try:
        return domain.encode("ascii").decode("idna") if "xn--" in domain else domain
    except UnicodeError:
        return domain


# ---------------------------------------------------------------- DoH
_DOH = ("https://cloudflare-dns.com/dns-query?name={}&type={}",
        "https://dns.google/resolve?name={}&type={}")


def resolve(domain: str, timeout=5) -> list[str]:
    out = []
    ctx = ssl.create_default_context()
    for typ, code in (("A", 1), ("AAAA", 28)):
        for url in _DOH:
            try:
                req = urllib.request.Request(url.format(domain, typ), headers={"accept": "application/dns-json"})
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                    d = json.loads(r.read().decode())
                for a in d.get("Answer", []) or []:
                    if a.get("type") == code and is_ip(a.get("data", "")):
                        out.append(a["data"])
                break
            except Exception:
                continue
    return sorted(set(out))


def resolve_many(domains, timeout=5) -> dict[str, list[str]]:
    res, lock = {}, threading.Lock()

    def work(d):
        ips = resolve(d, timeout)
        with lock:
            res[d] = ips
    threads = [threading.Thread(target=work, args=(d,), daemon=True) for d in domains if not is_ip(d)]
    for i in range(0, len(threads), 8):
        batch = threads[i:i + 8]
        for t in batch:
            t.start()
        for t in batch:
            t.join(timeout * 4 + 2)
    return res


# ---------------------------------------------------------------- блоки пресета
def split_blocks(argv: list[str]) -> list[list[str]]:
    blocks = [[]]
    for a in argv:
        if a == "--new":
            blocks.append([])
        else:
            blocks[-1].append(a)
    return blocks


def _val(block, key):
    for a in block:
        if a.startswith(key + "="):
            return a.split("=", 1)[1]
    return None


def _vals(block, key):
    return [a.split("=", 1)[1] for a in block if a.startswith(key + "=")]


def _has_port(spec: str | None, port: int) -> bool:
    if not spec:
        return False
    if spec.strip() == "*":
        return True
    for part in spec.split(","):
        part = part.strip()
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                if int(a) <= port <= int(b):
                    return True
            elif int(part) == port:
                return True
        except ValueError:
            pass
    return False


def describe_blocks(argv: list[str]) -> list[dict]:
    """Список блоков пресета (для выбора в интерфейсе)."""
    out = []
    for i, b in enumerate(split_blocks(argv)):
        tcp, udp, l7 = _val(b, "--filter-tcp"), _val(b, "--filter-udp"), _val(b, "--filter-l7")
        if not (tcp or udp or l7):
            continue
        name = _val(b, "--name") or ""
        if name == CUSTOM_NAME:
            continue
        hl = [Path(x.lstrip("@")).name for x in _vals(b, "--hostlist")]
        ips = [Path(x.lstrip("@")).name for x in _vals(b, "--ipset")]
        proto = ("TCP " + tcp) if tcp else ("UDP " + udp) if udp else ("L7 " + l7)
        if not name:
            name = ", ".join(hl or ips) or f"#{i + 1}"
        out.append({"index": i, "name": name, "proto": proto, "tcp": tcp, "udp": udp,
                    "hostlists": hl, "ipsets": ips, "strategy": any(a.startswith(("--dpi-desync", "--lua-desync")) for a in b)})
    return out


def _score(d: dict) -> int:
    if not d["strategy"]:
        return -100
    txt = (d["name"] + " " + " ".join(d["hostlists"])).lower()
    s = 0
    if d["hostlists"]:
        s += 10
    if re.search(r"general|other|blacklist|russia|мои|my|custom|allzone|основн|общ", txt):
        s += 8
    elif re.search(r"youtube(?!gv)|интерфейс", txt):
        s += 4
    elif re.search(r"google", txt):
        s += 3
    if re.search(r"exclude|исключ", txt):
        s -= 50
    return s


def auto_blocks(argv: list[str]) -> tuple[int | None, int | None]:
    """(TCP-блок, QUIC/UDP-блок) для копирования стратегии."""
    ds = describe_blocks(argv)
    tcp = [d for d in ds if _has_port(d["tcp"], 443)]
    udp = [d for d in ds if _has_port(d["udp"], 443) and d["hostlists"]]
    bt = max(tcp, key=_score) if tcp else None
    bu = max(udp, key=_score) if udp else None
    return (bt["index"] if bt and _score(bt) > -100 else None,
            bu["index"] if bu and _score(bu) > -100 else None)


def _clone(block: list[str], list_opt: str, path: str) -> list[str]:
    nb = [a for a in block if not a.startswith(_GLOBAL) and not a.startswith(_LISTS)]
    return [f"--name={CUSTOM_NAME}"] + nb + [f"{list_opt}={path}"]


def inject(argv: list[str], domains: list[str], ips: list[str], hosts_rel: str, ips_rel: str,
           block_name: str = AUTO) -> list[str]:
    """Добавляет в аргументы пресета блоки для своих сайтов. Возвращает новые аргументы."""
    if not domains and not ips:
        return argv
    blocks = split_blocks(argv)
    ds = describe_blocks(argv)
    chosen = next((d["index"] for d in ds if block_name and d["name"] == block_name), None)
    if chosen is not None:
        src_tcp, src_udp = chosen, None
    else:
        src_tcp, src_udp = auto_blocks(argv)
    if src_tcp is None and src_udp is None:
        return argv
    inserts: dict[int, list[list[str]]] = {}
    host_list = [d for d in domains if not is_ip(d)]
    if host_list:
        for src in (src_tcp, src_udp):
            if src is not None:
                inserts.setdefault(src, []).append(_clone(blocks[src], "--hostlist", hosts_rel))
    if ips:
        src = src_tcp if src_tcp is not None else src_udp
        inserts.setdefault(src, []).append(_clone(blocks[src], "--ipset", ips_rel))
    new_blocks = []
    for i, b in enumerate(blocks):
        new_blocks.extend(inserts.get(i, []))
        new_blocks.append(b)
    out = []
    for i, b in enumerate(new_blocks):
        if i:
            out.append("--new")
        out.extend(b)
    return out


# ---------------------------------------------------------------- хранилище
class SiteStore:
    """data/sites.json: {preset_id: {"domains": [...], "ips": {domain: [ip...]}, "with_ip": bool, "block": ""}}"""

    def __init__(self, data: Path):
        self.path = data / "sites.json"
        self.lock = threading.Lock()
        try:
            self.data = json.loads(self.path.read_text("utf-8"))
        except Exception:
            self.data = {}

    def get(self, pid: str) -> dict:
        e = dict(self.data.get(pid) or {})
        e.setdefault("domains", [])
        e.setdefault("ips", {})
        e.setdefault("with_ip", False)
        e.setdefault("block", AUTO)
        return e

    def count(self, pid: str) -> int:
        return len((self.data.get(pid) or {}).get("domains", []))

    def put(self, pid: str, entry: dict):
        with self.lock:
            if entry.get("domains"):
                self.data[pid] = entry
            else:
                self.data.pop(pid, None)
            self.save()

    def rename(self, old: str, new: str):
        with self.lock:
            if old in self.data and old != new:
                self.data[new] = self.data.pop(old)
                self.save()

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(self.path)

    # подстановка при запуске
    def apply(self, pid: str, argv: list[str], root: Path) -> list[str]:
        e = self.data.get(pid)
        if not e or not e.get("domains"):
            return argv
        domains = list(e["domains"])
        direct_ips = [d for d in domains if is_ip(d)]
        ips = list(direct_ips)
        if e.get("with_ip"):
            for d in domains:
                ips += e.get("ips", {}).get(d, [])
        ips = sorted(set(ips))
        key = hashlib.md5(pid.encode("utf-8")).hexdigest()[:10]
        d = root / "lists" / "zc_custom"
        d.mkdir(parents=True, exist_ok=True)
        hosts_rel, ips_rel = f"lists/zc_custom/{key}_hosts.txt", f"lists/zc_custom/{key}_ips.txt"
        hosts = [x for x in domains if not is_ip(x)]
        (root / hosts_rel).write_text("\n".join(hosts) + "\n", "utf-8")
        (root / ips_rel).write_text("\n".join(ips) + "\n", "utf-8")
        return inject(argv, hosts, ips, hosts_rel, ips_rel, e.get("block", AUTO))

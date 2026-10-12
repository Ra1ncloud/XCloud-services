"""Разбор ссылок и подписок: vless://, vmess://, trojan://, ss://, hysteria2://, vpn:// (Amnezia), JSON Xray/sing-box."""
import base64
import hashlib
import json
import re
import urllib.parse as up
import urllib.request
import zlib


class LinkError(ValueError):
    pass


def b64d(s: str) -> bytes:
    s = re.sub(r"\s+", "", s).replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


def _q(qs, k, d=""):
    v = qs.get(k)
    return v[0] if v and v[0] != "" else d


def sid(link: str) -> str:
    return hashlib.md5(link.strip().encode("utf-8", "replace")).hexdigest()[:10]


# ---------- транспорт и TLS (общие для vless/trojan/vmess) ----------

def _tls(qs, host, security):
    if security in ("", "none"):
        return None
    sni = _q(qs, "sni") or _q(qs, "peer") or (_q(qs, "host") if security != "reality" else "") or host
    t = {"enabled": True, "server_name": sni}
    fp = _q(qs, "fp")
    if fp or security == "reality":
        t["utls"] = {"enabled": True, "fingerprint": fp or "chrome"}
    alpn = _q(qs, "alpn")
    if alpn:
        t["alpn"] = [a for a in alpn.split(",") if a]
    if _q(qs, "allowInsecure") in ("1", "true") or _q(qs, "insecure") in ("1", "true"):
        t["insecure"] = True
    if security == "reality":
        pbk = _q(qs, "pbk")
        if not pbk:
            raise LinkError("в ссылке нет публичного ключа Reality (pbk)")
        t["reality"] = {"enabled": True, "public_key": pbk, "short_id": _q(qs, "sid")}
    return t


def _transport(qs, typ):
    typ = (typ or "tcp").lower()
    host = _q(qs, "host")
    path = up.unquote(_q(qs, "path", "/"))
    if typ in ("tcp", "raw"):
        if _q(qs, "headerType") == "http":
            return {"type": "http", "host": [h for h in host.split(",") if h], "path": path}
        return None
    if typ == "ws":
        tr = {"type": "ws", "path": path}
        m = re.search(r"[?&]ed=(\d+)", path)
        if m:
            tr["path"] = re.sub(r"[?&]ed=\d+", "", path) or "/"
            tr["max_early_data"] = int(m.group(1))
            tr["early_data_header_name"] = "Sec-WebSocket-Protocol"
        if host:
            tr["headers"] = {"Host": host}
        return tr
    if typ == "grpc":
        return {"type": "grpc", "service_name": up.unquote(_q(qs, "serviceName"))}
    if typ in ("http", "h2"):
        return {"type": "http", "host": [h for h in host.split(",") if h], "path": path}
    if typ == "httpupgrade":
        tr = {"type": "httpupgrade", "path": path}
        if host:
            tr["host"] = host
        return tr
    if typ in ("xhttp", "splithttp"):
        raise LinkError("транспорт XHTTP поддерживается только в Xray — переключите сервер на TCP/WS/gRPC")
    if typ == "kcp" or typ == "quic":
        raise LinkError(f"транспорт {typ} не поддерживается")
    return None


def _finish(ob, qs, host, security, typ):
    t = _tls(qs, host, security)
    if t:
        ob["tls"] = t
    tr = _transport(qs, typ)
    if tr:
        ob["transport"] = tr
    return ob


def _srv(proto, name, host, port, link, ob):
    return {"id": sid(link), "name": (name or host or "?").strip()[:80], "proto": proto, "host": host,
            "port": int(port), "link": link.strip(), "outbound": ob}


# ---------- протоколы ----------

def _split(link):
    u = up.urlsplit(link.strip())
    if not u.hostname:
        raise LinkError("не удалось разобрать адрес сервера")
    try:
        port = u.port
    except ValueError:
        raise LinkError("неверный порт")
    return u, up.parse_qs(u.query, keep_blank_values=True), up.unquote(u.fragment)


def parse_vless(link):
    u, qs, name = _split(link)
    port = u.port or 443
    ob = {"type": "vless", "server": u.hostname, "server_port": port, "uuid": up.unquote(u.username or "")}
    if not ob["uuid"]:
        raise LinkError("в ссылке нет UUID")
    flow = _q(qs, "flow")
    if flow:
        ob["flow"] = flow.replace("-udp443", "")
    ob["packet_encoding"] = _q(qs, "packetEncoding", "xudp")
    _finish(ob, qs, u.hostname, _q(qs, "security", "none").lower(), _q(qs, "type", "tcp"))
    return _srv("VLESS" + (" Reality" if _q(qs, "security") == "reality" else ""), name, u.hostname, port, link, ob)


def parse_trojan(link):
    u, qs, name = _split(link)
    port = u.port or 443
    ob = {"type": "trojan", "server": u.hostname, "server_port": port, "password": up.unquote(u.username or "")}
    _finish(ob, qs, u.hostname, _q(qs, "security", "tls").lower(), _q(qs, "type", "tcp"))
    return _srv("Trojan", name, u.hostname, port, link, ob)


def parse_vmess(link):
    body = link.strip()[8:]
    try:
        j = json.loads(b64d(body.split("#")[0]).decode("utf-8"))
    except Exception:
        raise LinkError("не удалось декодировать vmess-ссылку")
    host, port = j.get("add"), int(j.get("port") or 443)
    ob = {"type": "vmess", "server": host, "server_port": port, "uuid": j.get("id"),
          "security": j.get("scy") or "auto", "alter_id": int(j.get("aid") or 0)}
    qs = {"sni": [j.get("sni") or ""], "host": [j.get("host") or ""], "path": [j.get("path") or "/"],
          "alpn": [j.get("alpn") or ""], "fp": [j.get("fp") or ""], "serviceName": [j.get("path") or ""],
          "headerType": [j.get("type") or ""]}
    _finish(ob, qs, host, "tls" if j.get("tls") == "tls" else "none", j.get("net") or "tcp")
    return _srv("VMess", j.get("ps"), host, port, link, ob)


def parse_ss(link):
    s = link.strip()[5:]
    name = ""
    if "#" in s:
        s, name = s.split("#", 1)
        name = up.unquote(name)
    s = s.split("?")[0].rstrip("/")
    if "@" in s:
        userinfo, hp = s.rsplit("@", 1)
        userinfo = up.unquote(userinfo)
        try:
            dec = b64d(userinfo).decode("utf-8")
            if ":" in dec:
                userinfo = dec
        except Exception:
            pass
    else:
        dec = b64d(s).decode("utf-8")
        userinfo, hp = dec.rsplit("@", 1)
    method, password = userinfo.split(":", 1)
    u = up.urlsplit("//" + hp)
    ob = {"type": "shadowsocks", "server": u.hostname, "server_port": u.port, "method": method, "password": password}
    return _srv("Shadowsocks", name, u.hostname, u.port, link, ob)


def parse_hy2(link):
    u, qs, name = _split(link)
    port = u.port or 443
    ob = {"type": "hysteria2", "server": u.hostname, "server_port": port,
          "password": up.unquote(u.username or "") + ((":" + up.unquote(u.password)) if u.password else ""),
          "tls": {"enabled": True, "server_name": _q(qs, "sni", u.hostname),
                  "insecure": _q(qs, "insecure") in ("1", "true")}}
    if _q(qs, "obfs") == "salamander":
        ob["obfs"] = {"type": "salamander", "password": _q(qs, "obfs-password")}
    return _srv("Hysteria2", name, u.hostname, port, link, ob)


# ---------- Xray JSON (и vpn:// от Amnezia) ----------

def xray_to_link(o: dict, name="") -> str | None:
    """Исходящее соединение Xray → эквивалентная vless/trojan-ссылка."""
    proto = o.get("protocol")
    st = o.get("streamSettings") or {}
    sec = st.get("security") or "none"
    net = st.get("network") or "tcp"
    s = o.get("settings") or {}
    q = {"type": net, "security": sec}
    if proto == "vless":
        if s.get("vnext"):
            v = s["vnext"][0]
            addr, port, user = v.get("address"), v.get("port"), (v.get("users") or [{}])[0]
        else:
            addr, port, user = s.get("address"), s.get("port"), s
        uid, flow = user.get("id"), user.get("flow")
        if flow:
            q["flow"] = flow
    elif proto == "trojan":
        v = (s.get("servers") or [s])[0]
        addr, port, uid = v.get("address"), v.get("port"), v.get("password")
    else:
        return None
    if not addr or not uid:
        return None
    if sec == "reality":
        r = st.get("realitySettings") or {}
        q.update({"sni": r.get("serverName", ""), "pbk": r.get("publicKey", ""), "sid": r.get("shortId", ""),
                  "fp": r.get("fingerprint", "chrome")})
        if r.get("spiderX"):
            q["spx"] = r["spiderX"]
    elif sec == "tls":
        t = st.get("tlsSettings") or {}
        q["sni"] = t.get("serverName", "")
        if t.get("fingerprint"):
            q["fp"] = t["fingerprint"]
        if t.get("alpn"):
            q["alpn"] = ",".join(t["alpn"])
        if t.get("allowInsecure"):
            q["allowInsecure"] = "1"
    if net == "ws":
        w = st.get("wsSettings") or {}
        q["path"] = w.get("path", "/")
        h = w.get("host") or (w.get("headers") or {}).get("Host")
        if h:
            q["host"] = h
    elif net == "grpc":
        q["serviceName"] = (st.get("grpcSettings") or {}).get("serviceName", "")
    elif net in ("xhttp", "splithttp"):
        x = st.get("xhttpSettings") or st.get("splithttpSettings") or {}
        q["path"] = x.get("path", "/")
    q = {k: v for k, v in q.items() if v not in ("", None)}
    host = f"[{addr}]" if ":" in str(addr) else addr
    return (f"{proto}://{up.quote(str(uid), safe='')}@{host}:{port}?{up.urlencode(q)}"
            + (f"#{up.quote(name)}" if name else ""))


def from_xray_json(j, name="") -> list[str]:
    outs = j.get("outbounds") if isinstance(j, dict) else None
    links = []
    for o in outs or []:
        lk = xray_to_link(o, name or (j.get("remarks") if isinstance(j, dict) else "") or "")
        if lk:
            links.append(lk)
    return links


def decode_amnezia(link: str) -> tuple[list[str], list[str]]:
    """vpn://… → (ссылки, неподдерживаемые протоколы). Формат: base64url(qCompress(json))."""
    raw = b64d(link.strip()[6:])
    data = None
    for fn in (lambda b: zlib.decompress(b[4:]), zlib.decompress, lambda b: b):
        try:
            data = fn(raw)
            json.loads(data)
            break
        except Exception:
            data = None
    if data is None:
        raise LinkError("не удалось декодировать ссылку vpn://")
    j = json.loads(data)
    name = j.get("description") or j.get("name") or j.get("hostName") or "Amnezia"
    links, unsupported = [], []
    for c in j.get("containers") or []:
        cname = c.get("container", "")
        found = False
        for key, val in c.items():
            if isinstance(val, dict) and "last_config" in val:
                try:
                    cfg = json.loads(val["last_config"])
                except Exception:
                    continue
                if isinstance(cfg, dict) and cfg.get("outbounds"):
                    ls = from_xray_json(cfg, name)
                    if ls:
                        links += ls
                        found = True
        if not found and cname:
            unsupported.append(cname.replace("amnezia-", ""))
    if not links and isinstance(j.get("outbounds"), list):
        links = from_xray_json(j, name)
    return links, unsupported


PARSERS = {"vless": parse_vless, "trojan": parse_trojan, "vmess": parse_vmess, "ss": parse_ss,
           "hysteria2": parse_hy2, "hy2": parse_hy2}


def parse_link(link: str) -> dict:
    link = link.strip()
    scheme = link.split("://", 1)[0].lower()
    fn = PARSERS.get(scheme)
    if not fn:
        raise LinkError(f"протокол {scheme} не поддерживается")
    try:
        s = fn(link)
    except LinkError:
        raise
    except Exception as e:  # noqa
        raise LinkError(f"не удалось разобрать ссылку {scheme}://: {e}")
    if s["outbound"].get("type") in ("vless", "trojan") and s["outbound"].get("tls", {}).get("reality") is None \
            and s["outbound"].get("flow") and "tls" not in s["outbound"]:
        raise LinkError("flow xtls-rprx-vision требует TLS или Reality")
    return s


LINK_RE = re.compile(r"(?:vless|vmess|trojan|ss|hysteria2|hy2|vpn)://[^\s\"'<>]+", re.I)


def parse_text(text: str) -> tuple[list[dict], list[str]]:
    """Текст (одна/много ссылок, base64-блок, JSON) → (серверы, ошибки)."""
    text = (text or "").strip().lstrip("\ufeff")
    servers, errors = [], []
    if not text:
        return servers, errors
    if text[:1] in "{[":
        try:
            j = json.loads(text)
            items = j if isinstance(j, list) else [j]
            for it in items:
                if isinstance(it, dict) and it.get("outbounds"):
                    for o in it["outbounds"]:
                        if isinstance(o, dict) and o.get("type") in ("vless", "vmess", "trojan", "shadowsocks", "hysteria2") \
                                and o.get("server"):   # sing-box
                            o = {k: v for k, v in o.items() if k not in ("tag", "detour")}
                            fake = "singbox:" + json.dumps(o, sort_keys=True)
                            servers.append(_srv(o["type"].upper(), it.get("remarks") or o.get("server"), o["server"],
                                                o.get("server_port", 443), fake, o))
                    for lk in from_xray_json(it, it.get("remarks", "")):
                        try:
                            servers.append(parse_link(lk))
                        except LinkError as e:
                            errors.append(str(e))
            return servers, errors
        except ValueError:
            pass
    links = LINK_RE.findall(text)
    if not links:
        try:
            dec = b64d(text).decode("utf-8", "replace")
            links = LINK_RE.findall(dec)
        except Exception:
            links = []
    for lk in links:
        try:
            if lk.lower().startswith("vpn://"):
                ls, uns = decode_amnezia(lk)
                for x in ls:
                    try:
                        servers.append(parse_link(x))
                    except LinkError as e:
                        errors.append(str(e))
                if uns and not ls:
                    errors.append("протоколы " + ", ".join(uns) + " пока не поддерживаются — используйте XRay (VLESS)")
            else:
                servers.append(parse_link(lk))
        except LinkError as e:
            errors.append(str(e))
        except Exception as e:  # noqa
            errors.append(f"{lk[:20]}…: {e}")
    return servers, errors


def is_subscription(text: str) -> bool:
    t = text.strip()
    return bool(re.match(r"^https?://\S+$", t)) and not LINK_RE.search(t)


def _userinfo(h: str) -> dict:
    out = {}
    for part in (h or "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            try:
                out[k.strip()] = int(float(v.strip()))
            except ValueError:
                pass
    return out


def _title(h: str) -> str:
    h = (h or "").strip()
    if h.startswith("base64:"):
        try:
            return b64d(h[7:]).decode("utf-8")
        except Exception:
            return ""
    return up.unquote(h)


def fetch_subscription(url: str, proxy: str | None = None, timeout=15) -> tuple[list[dict], list[str], dict]:
    """Скачать подписку → (серверы, ошибки, info{title, upload, download, total, expire})."""
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})]
    op = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": "v2rayN/7.10", "Accept": "*/*"})
    with op.open(req, timeout=timeout) as r:
        body = r.read(8 * 1024 * 1024).decode("utf-8", "replace")
        hdr = r.headers
    info = _userinfo(hdr.get("subscription-userinfo", ""))
    info["title"] = _title(hdr.get("profile-title", ""))
    if not info["title"]:
        m = re.search(r"^#\s*profile-title:\s*(.+)$", body, re.M)
        if m:
            info["title"] = _title(m.group(1))
    if "happ://" in body and not LINK_RE.search(body):
        raise LinkError("подписка зашифрована для Happ (happ://crypt) — попросите обычную ссылку подписки")
    servers, errors = parse_text(body)
    return servers, errors, info

"""Сборка конфигурации sing-box и списков маршрутизации."""
import json
from pathlib import Path

TUN_NAME = "ZapretCloud"

# Готовые наборы сайтов, которым zapret не поможет (блокируют Россию сами) или которые чаще блокируют по IP
PACKS = {
    "ai": ("ИИ-сервисы (ChatGPT, Claude, Gemini, Copilot…)",
           ["openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com", "sora.com", "anthropic.com",
            "claude.ai", "claude.com", "gemini.google.com", "aistudio.google.com", "notebooklm.google.com",
            "generativelanguage.googleapis.com", "alkalimakersuite-pa.clients6.google.com",
            "copilot.microsoft.com", "sydney.bing.com", "perplexity.ai", "grok.com", "x.ai", "mistral.ai",
            "cursor.com", "cursor.sh", "elevenlabs.io", "midjourney.com", "suno.com", "poe.com"]),
    "social": ("Соцсети Meta и X (Instagram, Facebook, Threads, X)",
               ["instagram.com", "cdninstagram.com", "facebook.com", "fbcdn.net", "fb.com", "messenger.com",
                "threads.net", "threads.com", "whatsapp.com", "whatsapp.net", "x.com", "twitter.com", "twimg.com",
                "t.co"]),
    "media": ("Стриминг и музыка (Spotify, Netflix, SoundCloud…)",
              ["spotify.com", "scdn.co", "spotifycdn.com", "spotify.link", "netflix.com", "nflxvideo.net",
               "nflximg.net", "nflxext.com", "soundcloud.com", "sndcdn.com", "twitch.tv", "ttvnw.net", "jtvnw.net",
               "patreon.com", "medium.com"]),
    "dev": ("Работа и разработка (Notion, Figma, Docker Hub, JetBrains…)",
            ["docker.com", "docker.io", "notion.so", "notion.com", "notion.site", "notion-static.com",
             "notionusercontent.com", "notion.new",
             "prod-files-secure.s3.us-west-2.amazonaws.com",   # файлы и вложения Notion "figma.com", "intel.com", "jetbrains.com",
             "hashicorp.com", "terraform.io", "canva.com"]),
    "telegram": ("Telegram (сообщения, медиа, звонки)",
                 ["telegram.org", "telegram.me", "t.me", "telegra.ph", "telesco.pe", "tdesktop.com",
                  "cdn-telegram.org", "telegram-cdn.org", "fragment.com", "graph.org", "contest.com"]),
}

# IP-диапазоны (Telegram подключается напрямую по IP, без имени сайта)
PACK_CIDRS = {
    "telegram": ["91.108.56.0/22", "91.108.4.0/22", "91.108.8.0/22", "91.108.16.0/22", "91.108.12.0/22",
                 "149.154.160.0/20", "91.105.192.0/23", "91.108.20.0/22", "185.76.151.0/24", "2001:b28:f23d::/48",
                 "2001:b28:f23f::/48", "2001:67c:4e8::/48", "2001:b28:f23c::/48", "2a0a:f280::/32"],
}

RU_SUFFIX = ["ru", "su", "xn--p1ai", "yandex.net", "yandex.com", "yastatic.net", "ya.ru", "vk.com", "vk.me",
             "userapi.com", "vkuservideo.net", "mycdn.me", "ok.ru", "mail.ru", "gosuslugi.ru", "sberbank.ru",
             "tinkoff.ru", "tbank.ru", "avito.st", "wb.ru", "wbbasket.ru", "ozone.ru", "kaspersky.com",
             "1c.ru", "2gis.com", "rutube.ru", "dzen.ru"]

PRIVATE_EXCLUDE = ["10.0.0.0/8", "192.168.0.0/16", "169.254.0.0/16", "224.0.0.0/4", "fe80::/10"]


def write_ruleset(path: Path, domains, cidrs=None):
    domains = sorted({d.strip(".").lower() for d in domains if d and "." in d or d in ("ru", "su", "xn--p1ai")})
    rules = [{"domain_suffix": domains}] if domains else []
    if cidrs:
        rules.append({"ip_cidr": sorted(set(cidrs))})
    rules = rules or [{"domain": ["zapretcloud.invalid"]}]
    data = json.dumps({"version": 3, "rules": rules}, ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.read_text("utf-8") == data:
            return
    except OSError:
        pass
    tmp = path.with_suffix(".tmp")
    tmp.write_text(data, "utf-8")
    tmp.replace(path)


def build(outbound: dict, *, mode: str, route: str, ports: dict, secret: str, rs_vpn: Path, rs_direct: Path, rs_vpn_ip: Path,
          lan: bool = False, apps=None, log_level: str = "warn", tun_name: str = TUN_NAME,
          probe_auth: tuple | None = None, local_ips=()) -> dict:
    """mode: tun | proxy;  route: smart | list | all."""
    ob = dict(outbound)
    ob["tag"] = "proxy"
    ob.pop("detour", None)
    # Служебные прокси (проверка сайтов, загрузка подписок) — только с паролем: иначе любая
    # программа на ПК (в т.ч. «шпионящие» за VPN приложения) может пройти через них и узнать IP сервера.
    users = [{"username": probe_auth[0], "password": probe_auth[1]}] if probe_auth else []
    inbounds = [
        {"type": "mixed", "tag": "probe-direct", "listen": "127.0.0.1", "listen_port": ports["probe_direct"], "users": users},
        {"type": "mixed", "tag": "probe-vpn", "listen": "127.0.0.1", "listen_port": ports["probe_vpn"], "users": users},
    ]
    # Общий прокси нужен только для режима «прокси» (системный прокси Windows пароль не умеет)
    # и для раздачи в домашнюю сеть. В режиме TUN без раздачи порт вообще не открываем.
    if mode != "tun" or lan:
        inbounds.insert(0, {"type": "mixed", "tag": "mixed-in", "listen": "0.0.0.0" if lan else "127.0.0.1",
                            "listen_port": ports["mixed"]})
    if mode == "tun":
        inbounds.insert(0, {"type": "tun", "tag": "tun-in", "interface_name": tun_name,
                            "address": ["172.29.237.1/30"],
                            # mtu 9000 и stack mixed на части ПК вешают создание адаптера
                            # ("open interface take too much time") — оставляем дефолт и gvisor
                            "auto_route": True, "strict_route": True, "stack": "gvisor",
                            "route_exclude_address": PRIVATE_EXCLUDE})
    vpn_all = route == "all"
    rules = [
        {"action": "sniff"},
        {"protocol": "dns", "action": "hijack-dns"},
        *([{"inbound": ["mixed-in"], "source_ip_cidr": ["127.0.0.0/8", "::1/128"] +
            [f"{ip}/32" for ip in local_ips], "action": "reject"}] if mode == "tun" and lan else []),
        {"inbound": ["probe-direct"], "outbound": "direct"},
        {"inbound": ["probe-vpn"], "outbound": "proxy"},
        {"ip_is_private": True, "outbound": "direct"},
    ]
    for via, tag in (("direct", "direct"), ("vpn", "proxy")):
        names = sorted({a["name"] for a in (apps or []) if a.get("via") == via and a.get("name")})
        if names:
            rules.append({"process_name": names, "outbound": tag})
    rules.append({"rule_set": ["zc-direct"], "outbound": "direct"})
    if vpn_all:
        rules.append({"network": "udp", "port": 443, "action": "reject"})   # QUIC → TCP через VPN (быстрее и стабильнее)
    else:
        rules.append({"rule_set": ["zc-vpn"], "network": "udp", "port": 443, "action": "reject"})
        rules.append({"rule_set": ["zc-vpn"], "outbound": "proxy"})
        rules.append({"rule_set": ["zc-vpn-ip"], "outbound": "proxy"})
    dns_rules = [{"rule_set": ["zc-direct"], "server": "dns-direct"}]
    if not vpn_all:
        dns_rules.append({"rule_set": ["zc-vpn"], "server": "dns-remote"})
    cfg = {
        "log": {"level": log_level, "timestamp": False},
        "dns": {
            "servers": [
                {"type": "https", "tag": "dns-remote", "server": "1.1.1.1", "detour": "proxy"},
                {"type": "local", "tag": "dns-direct"},
                {"type": "local", "tag": "dns-local"},
            ],
            "rules": dns_rules,
            "final": "dns-remote" if vpn_all else "dns-direct",
            "strategy": "ipv4_only",
        },
        "inbounds": inbounds,
        "outbounds": [ob, {"type": "direct", "tag": "direct"}],
        "route": {
            "rules": rules,
            "rule_set": [
                {"type": "local", "tag": "zc-vpn", "format": "source", "path": str(rs_vpn)},
                {"type": "local", "tag": "zc-direct", "format": "source", "path": str(rs_direct)},
                {"type": "local", "tag": "zc-vpn-ip", "format": "source", "path": str(rs_vpn_ip)},
            ],
            "final": "proxy" if vpn_all else "direct",
            "auto_detect_interface": True,
            "default_domain_resolver": "dns-local",
        },
        "experimental": {"clash_api": {"external_controller": f"127.0.0.1:{ports['api']}", "secret": secret}},
    }
    return cfg

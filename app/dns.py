"""Смена DNS-серверов Windows (IPv4) и включение DNS-over-HTTPS (Windows 11)."""
import json
import os
import socket
import struct
import time

from .winutil import IS_WIN, powershell, run, windows_build

PROVIDERS = [
    {"id": "cloudflare", "name": "Cloudflare", "ips": ["1.1.1.1", "1.0.0.1"],
     "doh": "https://cloudflare-dns.com/dns-query", "desc": "dns_desc_cloudflare", "color": "#F38020"},
    {"id": "google", "name": "Google", "ips": ["8.8.8.8", "8.8.4.4"],
     "doh": "https://dns.google/dns-query", "desc": "dns_desc_google", "color": "#4285F4"},
    {"id": "xbox", "name": "Xbox DNS", "ips": ["111.88.96.50", "111.88.96.51"],
     "doh": "https://xbox-dns.ru/dns-query", "desc": "dns_desc_xbox", "color": "#107C10"},
    {"id": "adguard", "name": "AdGuard", "ips": ["94.140.14.14", "94.140.15.15"],
     "doh": "https://dns.adguard-dns.com/dns-query", "desc": "dns_desc_adguard", "color": "#68BC71"},
    {"id": "quad9", "name": "Quad9", "ips": ["9.9.9.9", "149.112.112.112"],
     "doh": "https://dns.quad9.net/dns-query", "desc": "dns_desc_quad9", "color": "#E2447B"},
]


def doh_supported() -> bool:
    return IS_WIN and windows_build() >= 22000


def list_adapters() -> list[dict]:
    """[{name, index, desc, guid, dns:[...]}] — только активные адаптеры."""
    if not IS_WIN:
        return [{"name": "Ethernet (demo)", "index": 1, "desc": "Demo adapter", "guid": "{0}", "dns": ["1.1.1.1"]}]
    script = (
        "$r=@(); foreach($a in Get-NetAdapter | Where-Object {$_.Status -eq 'Up'}){"
        "$d=(Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses;"
        "$r+=[pscustomobject]@{name=$a.Name;index=$a.ifIndex;desc=$a.InterfaceDescription;guid=$a.InterfaceGuid;dns=@($d)}};"
        "ConvertTo-Json -InputObject @($r) -Depth 4 -Compress"
    )
    code, out = powershell(script, timeout=30)
    try:
        data = json.loads(out.strip().splitlines()[-1])
        if isinstance(data, dict):
            data = [data]
        for a in data:
            a["dns"] = [x for x in (a.get("dns") or []) if x]
        return data
    except Exception:
        return []


def _doh_registry(guid: str, ips: list[str], enable: bool) -> str:
    base = (f"HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Dnscache\\InterfaceSpecificParameters\\{guid}"
            "\\DohInterfaceSettings\\Doh")
    s = f"Remove-Item -Path '{base}' -Recurse -Force -ErrorAction SilentlyContinue;"
    if enable:
        for ip in ips:
            s += (f"New-Item -Path '{base}\\{ip}' -Force | Out-Null;"
                  f"New-ItemProperty -Path '{base}\\{ip}' -Name 'DohFlags' -PropertyType QWord -Value 1 -Force | Out-Null;")
    return s


def apply(provider: dict | None, adapters: list[dict], doh: bool = False) -> tuple[bool, str]:
    """provider=None — вернуть автоматическое получение DNS (DHCP)."""
    if not IS_WIN:
        return True, "demo"
    if not adapters:
        return False, "no adapters"
    s = "$ErrorActionPreference='Continue';"
    if provider and doh and doh_supported():
        for ip in provider["ips"]:
            s += (f"if(Get-DnsClientDohServerAddress -ServerAddress '{ip}' -ErrorAction SilentlyContinue)"
                  f"{{Set-DnsClientDohServerAddress -ServerAddress '{ip}' -DohTemplate '{provider['doh']}' "
                  f"-AllowFallbackToUdp $false -AutoUpgrade $true}}else{{Add-DnsClientDohServerAddress "
                  f"-ServerAddress '{ip}' -DohTemplate '{provider['doh']}' -AllowFallbackToUdp $false -AutoUpgrade $true}};")
    for a in adapters:
        idx = int(a["index"])
        if provider:
            ips = ",".join(f"'{ip}'" for ip in provider["ips"])
            s += f"Set-DnsClientServerAddress -InterfaceIndex {idx} -ServerAddresses @({ips});"
        else:
            s += f"Set-DnsClientServerAddress -InterfaceIndex {idx} -ResetServerAddresses;"
        if doh_supported() and a.get("guid"):
            s += _doh_registry(a["guid"], provider["ips"] if provider else [], bool(provider and doh))
    s += "Clear-DnsClientCache; 'DONE'"
    code, out = powershell(s, timeout=60)
    return "DONE" in out, out


def flush_cache() -> tuple[bool, str]:
    if not IS_WIN:
        return True, ""
    code, out = run(["ipconfig", "/flushdns"], timeout=20)
    return code == 0, out


def ping_dns(ip: str, timeout=1.5) -> int | None:
    """Время ответа DNS-сервера на запрос A example.com, мс."""
    q = os.urandom(2) + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" + b"\x07example\x03com\x00" + struct.pack("!HH", 1, 1)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        t0 = time.perf_counter()
        s.sendto(q, (ip, 53))
        data, _ = s.recvfrom(512)
        s.close()
        if data[:2] == q[:2]:
            return int((time.perf_counter() - t0) * 1000)
    except OSError:
        pass
    return None

"""Обновление движка: winws2 (+lua) из bol-van/zapret2, winws из bol-van/zapret,
списки доменов/IP из Flowseal/zapret-discord-youtube (объединение, ничего не удаляется).
WinDivert.dll и драйвер Monkey64.sys не трогаем — они специально подобраны под сборку."""
import hashlib
import io
import json
import os
import re
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .winutil import CREATE_NO_WINDOW

UA = "ZapretCloud-updater"
SOURCES = {
    "zapret2": {"repo": "bol-van/zapret2", "title": "Zapret 2 (winws2 + lua)", "asset": r"^zapret2-v[\d.]+\.zip$"},
    "zapret1": {"repo": "bol-van/zapret", "title": "Zapret 1 (winws)", "asset": r"^zapret-v[\d.]+\.zip$"},
    "lists": {"repo": "Flowseal/zapret-discord-youtube", "title": "Списки сайтов (Flowseal)",
              "asset": r"^zapret-discord-youtube-[\d.]+\.zip$"},
}
EXE = {"zapret2": "winws2.exe", "zapret1": "winws.exe"}
APP_ASSET = r"^ZapretCloud_Setup_[\d.]+\.exe$"
LISTS_VERSION_FILE = ".zc_lists_version"
SKIP_LISTS = {"ipset-all.txt"}   # у Flowseal это заглушка


def _ctx():
    return ssl.create_default_context()


def _get(url: str, timeout=20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
        return r.read()


def _download(url: str, progress=None, timeout=30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
        total = int(r.headers.get("Content-Length") or 0)
        buf = io.BytesIO()
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            buf.write(chunk)
            if progress and total:
                progress(buf.tell() / total)
        return buf.getvalue()


def vkey(v: str):
    nums = re.findall(r"\d+", v or "")
    return tuple(int(x) for x in nums) if nums else (-1,)


# ------------------------------------------------------------ текущие версии
def exe_version(exe: Path) -> str:
    """winws --version → 'github version v1.0.3 (hash)'."""
    if not exe.exists():
        return ""
    try:
        p = subprocess.run([str(exe), "--version"], capture_output=True, timeout=10,
                           creationflags=CREATE_NO_WINDOW, cwd=str(exe.parent))
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        m = re.search(r"version\s+(v?\d+(?:\.\d+)+)", out)
        return m.group(1) if m else ""
    except Exception:
        return ""


def current_versions(root: Path, data: Path) -> dict:
    cache_p = data / "engine_info.json"
    try:
        cache = json.loads(cache_p.read_text("utf-8"))
    except Exception:
        cache = {}
    res = {}
    for comp, name in EXE.items():
        exe = root / "exe" / name
        try:
            st = exe.stat()
            key = f"{st.st_size}:{int(st.st_mtime)}"
        except OSError:
            res[comp] = ""
            continue
        c = cache.get(comp) or {}
        if c.get("key") == key and c.get("version"):
            res[comp] = c["version"]
        else:
            v = exe_version(exe)
            res[comp] = v
            if v:
                cache[comp] = {"key": key, "version": v}
    try:
        res["lists"] = (root / "lists" / LISTS_VERSION_FILE).read_text("utf-8").strip()
    except OSError:
        res["lists"] = ""
    try:
        cache_p.write_text(json.dumps(cache), "utf-8")
    except OSError:
        pass
    return res


# ------------------------------------------------------------ проверка
def latest(comp: str) -> dict:
    src = SOURCES[comp]
    d = json.loads(_get(f"https://api.github.com/repos/{src['repo']}/releases/latest").decode())
    asset = next((a for a in d.get("assets", []) if re.match(src["asset"], a["name"])), None)
    sha = next((a for a in d.get("assets", []) if a["name"].lower().startswith("sha256")), None)
    if not asset:
        raise RuntimeError(f"{src['repo']}: нет подходящего архива")
    return {"comp": comp, "title": src["title"], "version": d.get("tag_name", ""), "url": asset["browser_download_url"],
            "name": asset["name"], "size": asset.get("size", 0), "sha_url": sha["browser_download_url"] if sha else None,
            "page": d.get("html_url", ""), "notes": (d.get("body") or "")[:1500]}


def latest_app() -> dict:
    """Последний релиз самой программы (установщик) из UPDATE_REPO."""
    from .paths import UPDATE_REPO
    try:
        d = json.loads(_get(f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest").decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError("релизов пока нет или репозиторий закрыт")
        raise
    asset = next((a for a in d.get("assets", []) if re.match(APP_ASSET, a["name"])), None)
    if not asset:
        raise RuntimeError("в релизе нет установщика")
    return {"comp": "app", "title": "ZapretCloud", "version": d.get("tag_name", "").lstrip("v"),
            "url": asset["browser_download_url"], "name": asset["name"], "size": asset.get("size", 0),
            "page": d.get("html_url", ""), "notes": (d.get("body") or "")[:1500]}


def download_app(item: dict, data: Path, progress=None) -> Path:
    """Скачивает установщик новой версии во временную папку."""
    blob = _download(item["url"], lambda f: progress and progress(f"ZapretCloud {item['version']}: {int(f * 100)}%", f),
                     timeout=60)
    if item.get("size") and len(blob) != int(item["size"]):
        raise RuntimeError("установщик скачался не полностью")
    if blob[:2] != b"MZ":
        raise RuntimeError("скачанный файл не похож на установщик")
    d = data / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("ZapretCloud_Setup_*.exe"):
        try:
            old.unlink()
        except OSError:
            pass
    path = d / item["name"]
    path.write_bytes(blob)
    return path


def run_installer(path: Path):
    """Тихая установка поверх текущей версии; установщик сам запустит программу после установки."""
    flags = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([str(path), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     creationflags=flags, close_fds=True)


def check(root: Path, data: Path) -> list[dict]:
    """Возвращает список компонентов с полями current/latest/available/error."""
    from .paths import APP_VERSION
    cur = current_versions(root, data)
    out = []
    app = {"comp": "app", "title": "ZapretCloud", "current": APP_VERSION}
    try:
        app.update(latest_app())
        app["available"] = vkey(app["version"]) > vkey(APP_VERSION)
    except Exception as e:  # noqa
        app["error"] = str(e)[:200]
        app["available"] = False
    out.append(app)
    for comp in SOURCES:
        item = {"comp": comp, "title": SOURCES[comp]["title"], "current": cur.get(comp, "")}
        try:
            item.update(latest(comp))
            item["available"] = vkey(item["version"]) > vkey(item["current"])
        except Exception as e:  # noqa
            item["error"] = str(e)[:200]
            item["available"] = False
        out.append(item)
    return out


# ------------------------------------------------------------ установка
def _strip_root(names):
    first = names[0].split("/")[0] + "/" if names else ""
    return first if all(n.startswith(first) for n in names) else ""


def _plan(item: dict, blob: bytes, root: Path) -> dict[str, bytes]:
    """Возвращает {относительный путь в engine: содержимое}."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = z.namelist()
    pre = _strip_root(names)
    files = {}
    comp = item["comp"]
    if comp in EXE:
        b = pre + "binaries/windows-x86_64/"
        exe = EXE[comp]
        if b + exe not in names:
            raise RuntimeError(f"в архиве нет {exe}")
        files["exe/" + exe] = z.read(b + exe)
        if b + "cygwin1.dll" in names:
            files["exe/cygwin1.dll"] = z.read(b + "cygwin1.dll")
        if comp == "zapret2":
            for n in names:
                if n.startswith(pre + "lua/") and n.endswith(".lua"):
                    files["lua/" + n[len(pre) + 4:]] = z.read(n)
    else:  # lists — объединяем строки
        for n in names:
            if n.startswith(pre + "lists/") and n.endswith(".txt") and "/" not in n[len(pre) + 6:]:
                fname = n[len(pre) + 6:]
                if fname in SKIP_LISTS:
                    continue
                new = z.read(n).decode("utf-8", "replace").splitlines()
                dst = root / "lists" / fname
                old = dst.read_text("utf-8", "replace").splitlines() if dst.exists() else []
                seen = set(x.strip() for x in old)
                add = [x.strip() for x in new if x.strip() and not x.strip().startswith("#") and x.strip() not in seen]
                if add or not dst.exists():
                    files["lists/" + fname] = ("\n".join(old + add) + "\n").encode("utf-8")
        files["lists/" + LISTS_VERSION_FILE] = item["version"].encode()
    # не перезаписываем одинаковые файлы
    return {k: v for k, v in files.items() if not ((root / k).exists() and (root / k).read_bytes() == v)}


def apply(items: list[dict], root: Path, data: Path, progress=None) -> Path:
    """Скачивает и устанавливает. Возвращает папку резервной копии. Бросает исключение при ошибке (с откатом)."""
    plan: dict[str, bytes] = {}
    for i, item in enumerate(sorted(items, key=lambda x: x["comp"] != "zapret2")):   # cygwin берём из zapret2
        def pr(f, i=i):
            if progress:
                progress(f"{item['title']}: {int(f * 100)}%", (i + f) / len(items))
        blob = _download(item["url"], pr)
        if item.get("sha_url"):
            try:
                sums = _get(item["sha_url"]).decode("utf-8", "replace")
                want = next((ln.split()[0] for ln in sums.splitlines() if ln.strip().endswith(item["name"])), None)
                if want and hashlib.sha256(blob).hexdigest().lower() != want.lower():
                    raise RuntimeError(f"{item['name']}: контрольная сумма не совпадает")
            except urllib.error.URLError:
                pass
        for k, v in _plan(item, blob, root).items():
            if k == "exe/cygwin1.dll" and k in plan:
                continue
            plan[k] = v
    if not plan:
        return None
    if progress:
        progress("Установка…", 1.0)
    bdir = data / "engine_backup" / time.strftime("%Y%m%d-%H%M%S")
    bdir.mkdir(parents=True, exist_ok=True)
    created = []
    for rel in plan:
        src = root / rel
        if src.exists():
            (bdir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, bdir / rel)
        else:
            created.append(rel)
    (bdir / "manifest.json").write_text(json.dumps({"files": list(plan), "created": created,
                                                    "comps": {i["comp"]: i["version"] for i in items}}), "utf-8")
    try:
        for rel, content in plan.items():
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(dst.name + ".zcnew")
            tmp.write_bytes(content)
            os.replace(tmp, dst)
        for comp, exe in EXE.items():
            if "exe/" + exe in plan and os.name == "nt" and not exe_version(root / "exe" / exe):
                raise RuntimeError(f"{exe} не запускается после обновления")
    except Exception:
        rollback(bdir, root)
        raise
    _cleanup_backups(data)
    return bdir


def last_backup(data: Path) -> Path | None:
    d = data / "engine_backup"
    if not d.is_dir():
        return None
    bs = sorted([p for p in d.iterdir() if (p / "manifest.json").exists()], reverse=True)
    return bs[0] if bs else None


def rollback(bdir: Path, root: Path):
    m = json.loads((bdir / "manifest.json").read_text("utf-8"))
    for rel in m["files"]:
        b = bdir / rel
        if b.exists():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(b, root / rel)
    for rel in m.get("created", []):
        try:
            (root / rel).unlink()
        except OSError:
            pass
    shutil.rmtree(bdir, ignore_errors=True)


def _cleanup_backups(data: Path, keep=3):
    d = data / "engine_backup"
    bs = sorted([p for p in d.iterdir() if p.is_dir()], reverse=True)
    for p in bs[keep:]:
        shutil.rmtree(p, ignore_errors=True)

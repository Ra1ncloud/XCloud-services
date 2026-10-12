"""Пути программы: встроенный движок (engine), ресурсы и папка данных пользователя."""
import os
import sys
from pathlib import Path

APP_NAME = "ZapretCloud"
APP_VERSION = "2.2.13"
UPDATE_REPO = "Ra1ncloud/XCloud-services"   # GitHub-репозиторий с релизами программы (должен быть публичным)
APP_ID = "ZapretCloud"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Папка с assets (в собранной версии — внутри _internal)."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else app_dir()


def asset(name: str) -> Path:
    for d in (resource_dir() / "assets", app_dir() / "assets"):
        if (d / name).exists():
            return d / name
    return resource_dir() / "assets" / name


def engine_dir() -> Path:
    return app_dir() / "engine"


def looks_like_root(p: Path) -> bool:
    try:
        return (p / "exe" / "winws.exe").exists() or (p / "exe" / "winws2.exe").exists()
    except OSError:
        return False


def find_root(saved: str | None = None) -> Path | None:
    """Своя папка движка (если пользователь указал) → встроенный engine."""
    cands = []
    if saved:
        cands.append(Path(saved))
    cands.append(engine_dir())
    a = app_dir()
    cands += [a, a.parent]
    for c in cands:
        if looks_like_root(c):
            return c.resolve()
    return None


def is_portable() -> bool:
    return not getattr(sys, "frozen", False) or (app_dir() / "portable.txt").exists()


def data_dir() -> Path:
    """Данные пользователя: %AppData%\\ZapretCloud (не стираются при переустановке).
    Портативный режим (файл portable.txt рядом с exe) и запуск из исходников — папка data рядом."""
    if is_portable():
        d = app_dir() / "data"
    else:
        d = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_ID
    for sub in ("", "tmp", "logs", "presets/winws1", "presets/winws2"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def user_presets_dir() -> Path:
    return data_dir() / "presets"

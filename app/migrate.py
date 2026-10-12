"""Перенос данных из Zapret Studio (предыдущее название программы) при первом запуске."""
import json
import os
import shutil
from pathlib import Path

from .paths import app_dir, data_dir, user_presets_dir


def _candidates() -> list[Path]:
    out = []
    a = app_dir()
    out += [a / "ZapretStudio_data", a.parent / "ZapretStudio_data", a.parent / "ZapretStudio" / "data"]
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    for base in (home / "Desktop", home / "Downloads", home / "Documents", home / "OneDrive" / "Desktop"):
        if not base.is_dir():
            continue
        for pat in ("*/ZapretStudio_data", "*/*/ZapretStudio_data", "*/ZapretStudio/data", "*/*/ZapretStudio/data"):
            try:
                out += list(base.glob(pat))
            except OSError:
                pass
    return [p for p in out if (p / "settings.json").exists()]


def migrate_from(old: Path) -> bool:
    """old — папка ZapretStudio_data (или папка, где она лежит)."""
    old = Path(old)
    if not (old / "settings.json").exists():
        for sub in ("ZapretStudio_data", "ZapretStudio/data", "data"):
            if (old / sub / "settings.json").exists():
                old = old / sub
                break
        else:
            return False
    d = data_dir()
    try:
        st = json.loads((old / "settings.json").read_text("utf-8"))
    except Exception:
        st = {}
    old_root = st.pop("root", None)
    st.pop("autostart", None)          # задача автозапуска была под старым именем
    cur = {}
    try:
        cur = json.loads((d / "settings.json").read_text("utf-8"))
    except Exception:
        pass
    cur.update(st)
    (d / "settings.json").write_text(json.dumps(cur, ensure_ascii=False, indent=2), "utf-8")
    for n in ("results.json",):
        if (old / n).exists():
            shutil.copy2(old / n, d / n)
    # пользовательские пресеты лежали в папке Zapret: presets/winws1, presets/winws2
    roots = [Path(old_root)] if old_root else []
    roots += [old.parent, old.parent.parent]
    up = user_presets_dir()
    for r in roots:
        for eng in ("winws1", "winws2"):
            src = r / "presets" / eng
            if src.is_dir():
                for f in src.glob("*.txt"):
                    dst = up / eng / f.name
                    if not dst.exists():
                        shutil.copy2(f, dst)
    return True


def auto_migrate():
    d = data_dir()
    if (d / "settings.json").exists() or (d / ".migrated").exists():
        return
    try:
        c = _candidates()
        if c:
            c.sort(key=lambda p: (p / "settings.json").stat().st_mtime, reverse=True)
            migrate_from(c[0])
    except Exception:
        pass
    try:
        (d / ".migrated").write_text("1")
    except OSError:
        pass

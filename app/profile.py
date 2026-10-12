"""Офлайн-профиль: экспорт/импорт всех данных программы в один файл.
.zcprofile — zip (настройки, свои пресеты, свои сайты, результаты тестов);
.json      — только настройки."""
import json
import shutil
import time
import zipfile
from pathlib import Path

from .paths import APP_NAME, APP_VERSION, data_dir, user_presets_dir

PROFILE_EXT = ".zcprofile"
SKIP_KEYS = {"root"}           # путь к движку зависит от компьютера


def _settings_dict() -> dict:
    from .settings import settings
    return {k: v for k, v in settings.data.items() if k not in SKIP_KEYS}


def export_profile(path: Path) -> Path:
    path = Path(path)
    if path.suffix.lower() != PROFILE_EXT:
        path = path.with_suffix(PROFILE_EXT)
    d = data_dir()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps({"app": APP_NAME, "version": APP_VERSION, "type": "full",
                                                "created": int(time.time())}, ensure_ascii=False, indent=1))
        z.writestr("settings.json", json.dumps(_settings_dict(), ensure_ascii=False, indent=2))
        for name in ("sites.json", "results.json"):
            if (d / name).exists():
                z.write(d / name, name)
        up = user_presets_dir()
        for f in up.rglob("*.txt"):
            z.write(f, "presets/" + f.relative_to(up).as_posix())
    return path


def export_settings(path: Path) -> Path:
    path = Path(path)
    if path.suffix.lower() != ".json":
        path = path.with_suffix(".json")
    data = {"app": APP_NAME, "version": APP_VERSION, "type": "settings", "settings": _settings_dict()}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    return path


def _apply_settings(new: dict):
    from .settings import settings
    keep = {k: settings.data.get(k) for k in SKIP_KEYS}
    settings.data.update({k: v for k, v in new.items() if k not in SKIP_KEYS})
    settings.data.update(keep)
    settings.save()


def import_file(path: Path) -> str:
    """Применяет профиль или файл настроек. Возвращает 'full' или 'settings'. Бросает ValueError."""
    path = Path(path)
    d = data_dir()
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            if "settings.json" not in names:
                raise ValueError("not a profile")
            # резервная копия текущих данных
            backup = d / "tmp" / "before_import"
            shutil.rmtree(backup, ignore_errors=True)
            backup.mkdir(parents=True)
            for n in ("settings.json", "sites.json", "results.json"):
                if (d / n).exists():
                    shutil.copy2(d / n, backup / n)
            _apply_settings(json.loads(z.read("settings.json").decode("utf-8")))
            for n in ("sites.json", "results.json"):
                if n in names:
                    (d / n).write_bytes(z.read(n))
            up = user_presets_dir()
            for n in names:
                if n.startswith("presets/") and n.endswith(".txt"):
                    rel = Path(n[len("presets/"):])
                    if ".." in rel.parts or len(rel.parts) != 2 or rel.parts[0] not in ("winws1", "winws2"):
                        continue
                    (up / rel).parent.mkdir(parents=True, exist_ok=True)
                    (up / rel).write_bytes(z.read(n))
        return "full"
    try:
        data = json.loads(path.read_text("utf-8-sig"))
    except Exception:
        raise ValueError("bad file")
    if isinstance(data, dict) and isinstance(data.get("settings"), dict):
        data = data["settings"]
    if not isinstance(data, dict):
        raise ValueError("bad file")
    _apply_settings(data)
    return "settings"

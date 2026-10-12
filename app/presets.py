"""Загрузка, разбор и сохранение пресетов (txt-файлы с аргументами winws/winws2)."""
import re
from dataclasses import dataclass, field
from pathlib import Path

ENGINES = ("winws2", "winws1")
ENGINE_EXE = {"winws1": "winws.exe", "winws2": "winws2.exe"}
ENGINE_LABEL = {"winws1": "Zapret 1", "winws2": "Zapret 2"}
_HDR = re.compile(r"^#\s*([A-Za-z][\w ]*?)\s*:\s*(.*)$")


@dataclass
class Preset:
    name: str
    engine: str
    path: Path
    builtin: bool
    description: str = ""
    color: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.engine}/{'builtin' if self.builtin else 'user'}/{self.path.name}"

    @property
    def game_filter(self) -> bool:
        return "game filter" in self.name.lower()

    def read(self) -> str:
        return self.path.read_text("utf-8", errors="replace")


def parse_header(text: str) -> dict:
    meta = {}
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if not s.startswith("#"):
            break
        m = _HDR.match(s)
        if m:
            meta[m.group(1).strip().lower()] = m.group(2).strip()
    return meta


def preset_dirs(root: Path, user_dir: Path | None = None):
    for eng in ENGINES:
        yield eng, True, root / "presets" / f"{eng}_builtin"
        yield eng, False, (user_dir or root / "presets") / eng


def load_all(root: Path, user_dir: Path | None = None) -> list[Preset]:
    out = []
    for eng, builtin, d in preset_dirs(root, user_dir):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.txt"), key=lambda p: p.name.lower()):
            try:
                with f.open("r", encoding="utf-8", errors="replace") as fh:
                    head = "".join(fh.readline() for _ in range(15))
            except OSError:
                continue
            meta = parse_header(head)
            out.append(Preset(
                name=meta.get("preset") or meta.get("name") or f.stem,
                engine=eng, path=f, builtin=builtin,
                description=meta.get("description", ""),
                color=meta.get("iconcolor", ""), meta=meta))
    return out


_SAFE_RE = re.compile(r"^[A-Za-z0-9_.,:/@%+=\-^]*$")


def _sq(v: str) -> str:
    """Экранирование для wordexp (winws читает @config через wordexp): одинарные кавычки."""
    if v and _SAFE_RE.match(v):
        return v
    return "'" + v.replace("'", "'\\''") + "'"


def build_argv(text: str) -> list[str]:
    """Чистые аргументы (без экранирования) для прямой передачи в командной строке."""
    args = []
    for raw in text.splitlines():
        s = raw.strip().lstrip("\ufeff")
        if not s or s.startswith("#") or s.startswith(";"):
            continue
        if s.startswith("-") and "=" in s:
            k, v = s.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            if k.strip() == "--comment":
                continue  # комментарии движку не нужны
            args.append(f"{k.strip()}={v}")
        else:
            if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
                s = s[1:-1]
            args.append(s)
    return args


def build_args(text) -> list[str]:
    """Экранированные аргументы для @config-файла (winws разбирает его через wordexp).
    text — текст пресета или уже готовый список аргументов."""
    out = []
    for a in (build_argv(text) if isinstance(text, str) else text):
        if a.startswith("-") and "=" in a:
            k, v = a.split("=", 1)
            out.append(f"{k}={_sq(v)}")
        else:
            out.append(_sq(a))
    return out


def cygwin_cmdline(argv: list[str]) -> str:
    """Командная строка для cygwin-программ (winws): всё «небезопасное» — в двойных кавычках,
    чтобы cygwin не раскрывал * ? [ ] и не трогал ' и пробелы."""
    parts = []
    for a in argv:
        if a and _SAFE_RE.match(a):
            parts.append(a)
        else:
            parts.append('"' + a.replace('"', '\\"') + '"')
    return " ".join(parts)


def write_at_config(argv: list[str], engine: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = out_dir / f"active_{engine}.txt"
    cfg.write_text("\n".join(build_args(argv)) + "\n", "utf-8")
    return cfg


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or "preset"


def make_header(name: str, description: str = "", color: str = "") -> str:
    h = [f"# Preset: {name}"]
    if color:
        h.append(f"# IconColor: {color}")
    h.append(f"# Description: {description}")
    return "\n".join(h) + "\n"


def strip_header(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and (not lines[i].strip() or (lines[i].lstrip().startswith("#") and _HDR.match(lines[i].strip()))):
        i += 1
    return "\n".join(lines[i:])


def save_user_preset(user_dir: Path, engine: str, name: str, body: str, description: str = "",
                     color: str = "", old_path: Path | None = None) -> Path:
    """user_dir — папка пользовательских пресетов (data/presets)."""
    d = user_dir / engine
    d.mkdir(parents=True, exist_ok=True)
    path = d / (safe_filename(name) + ".txt")
    text = make_header(name, description, color) + "\n" + strip_header(body).strip() + "\n"
    path.write_text(text, "utf-8")
    if old_path and old_path.resolve() != path.resolve() and old_path.exists():
        old_path.unlink()
    return path


# ---------- Каталоги стратегий ----------
def load_catalog(root: Path, engine: str) -> dict[str, list[tuple[str, str]]]:
    """Возвращает {категория: [(название, текст аргументов), ...]}"""
    res = {}
    d = root / "system" / "strategy_catalogs" / engine
    if not d.is_dir():
        return res
    for f in sorted(d.glob("*.txt")):
        items, cur_name, cur_lines = [], None, []

        def flush():
            if cur_name is not None and cur_lines:
                items.append((cur_name, "\n".join(cur_lines)))
        for line in f.read_text("utf-8", errors="replace").splitlines():
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                flush()
                cur_name, cur_lines = s[1:-1], []
            elif cur_name is not None:
                if s.startswith("name ="):
                    cur_name = s.split("=", 1)[1].strip() or cur_name
                elif s.startswith("--"):
                    cur_lines.append(s)
        flush()
        res[f.stem] = items
    return res


def list_files(root: Path) -> list[str]:
    d = root / "lists"
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.glob("*.txt"))

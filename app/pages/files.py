from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QFileDialog, QPushButton, QCheckBox

from ..i18n import tr
from ..icons import icon
from ..paths import looks_like_root
from ..settings import settings
from ..widgets import label, button, page_header, T
from ..winutil import open_path

# (название, функция пути от core, иконка)
USER = [
    ("Мои пресеты", lambda c: c.user_dir, "edit"),
    ("Списки доменов и IP", lambda c: c.root / "lists" if c.root else None, "list"),
    ("Лог winws", lambda c: c.data / "logs" / "winws.log", "file"),
    ("Логи программы", lambda c: c.data / "logs", "folder"),
]
ADVANCED = [
    ("Встроенные пресеты Zapret 2", lambda c: c.root / "presets/winws2_builtin" if c.root else None, "layers"),
    ("Встроенные пресеты Zapret 1", lambda c: c.root / "presets/winws1_builtin" if c.root else None, "layers"),
    ("Папка движка", lambda c: c.root, "folder"),
    ("Программы winws", lambda c: c.root / "exe" if c.root else None, "cpu"),
    ("Бинарные файлы (bin)", lambda c: c.root / "bin" if c.root else None, "database"),
    ("Lua-скрипты", lambda c: c.root / "lua" if c.root else None, "code"),
    ("Каталоги стратегий", lambda c: c.root / "system/strategy_catalogs" if c.root else None, "sliders"),
    ("Данные программы", lambda c: c.data, "database"),
]


class FilesPage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(14)
        root.addWidget(page_header(tr("Файлы"), tr("Быстрый доступ к вашим пресетам, спискам и логам")))
        root.addLayout(self._grid(USER))

        self.adv_box = QWidget()
        al = QVBoxLayout(self.adv_box)
        al.setContentsMargins(0, 8, 0, 0)
        al.setSpacing(10)
        h = QHBoxLayout()
        self.root_lbl = label(f"{tr('Движок')}: {core.root or '—'}", "muted", wrap=True)
        h.addWidget(self.root_lbl, 1)
        b = button(tr("Сменить папку движка…"), "folder")
        b.clicked.connect(self.change_root)
        h.addWidget(b)
        al.addLayout(h)
        al.addLayout(self._grid(ADVANCED))
        root.addWidget(self.adv_box)
        root.addStretch(1)

        self.adv = QCheckBox(tr("Показать системные файлы (для опытных)"))
        self.adv.setChecked(bool(settings.get("show_system_files")))
        self.adv.toggled.connect(self._toggle)
        root.addWidget(self.adv)
        self.adv_box.setVisible(self.adv.isChecked())

    def _grid(self, entries):
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (name, getp, ic) in enumerate(entries):
            t = QPushButton()
            t.setProperty("kind", "tile")
            t.setProperty("ico", ic)
            t.setIcon(icon(ic, T().text, 22))
            t.setIconSize(QSize(22, 22))
            t.setText("  " + tr(name))
            t.setMinimumHeight(64)
            t.setCursor(Qt.CursorShape.PointingHandCursor)
            t.clicked.connect(lambda _=False, g=getp: self.open(g(self.core)))
            grid.addWidget(t, i // 3, i % 3)
        return grid

    def _toggle(self, v):
        settings.set("show_system_files", v)
        self.adv_box.setVisible(v)

    def open(self, p: Path | None):
        if p is None:
            return
        if p.suffix:
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text("", "utf-8")
        else:
            p.mkdir(parents=True, exist_ok=True)
        open_path(p)

    def change_root(self):
        d = QFileDialog.getExistingDirectory(self, tr("Выберите папку движка"), str(self.core.root or ""))
        if not d:
            return
        if not looks_like_root(Path(d)):
            self.core.toast.emit(tr("В папке нет exe\\winws.exe или exe\\winws2.exe"), "error")
            return
        self.core.set_root(Path(d))
        self.root_lbl.setText(f"{tr('Движок')}: {d}")

"""Диалог «Обнаружены мешающие программы»."""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout

from .i18n import tr
from .widgets import label, button


class ConflictDialog(QDialog):
    STOP, IGNORE = 2, 3

    def __init__(self, items, parent=None, start_text=True):
        super().__init__(parent)
        self.setWindowTitle(tr("Обнаружены мешающие программы"))
        self.setMinimumWidth(620)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)
        lay.addWidget(label(tr("Обнаружены мешающие программы"), "h2"))
        lay.addWidget(label(tr("Они используют тот же драйвер или тоже обходят блокировки — вместе с ZapretCloud обход "
                               "может не работать."), "muted", wrap=True))
        rows = []
        for it in items:
            c = "#EF4444" if it["blocking"] else "#F59E0B"
            extra = f" (PID {it['pid']})" if it.get("pid") else ""
            rows.append(f"<span style='color:{c}'>●</span> {tr(it['title']) if it['kind'] != 'vpn' else it['title']}{extra}")
        l = label("<br>".join(rows), wrap=True)
        lay.addWidget(l)
        if any(i["kind"] == "vpn" for i in items):
            lay.addWidget(label(tr("VPN останавливать не нужно — просто учтите, что он может мешать."), "small", wrap=True))
        bb = QHBoxLayout()
        bb.addStretch(1)
        b0 = button(tr("Отмена"))
        b0.clicked.connect(self.reject)
        b1 = button(tr("Запустить всё равно") if start_text else tr("Пропустить"))
        b1.clicked.connect(lambda: self.done(self.IGNORE))
        b2 = button(tr("Остановить мешающее и запустить") if start_text else tr("Остановить мешающее"), "power", "primary")
        b2.clicked.connect(lambda: self.done(self.STOP))
        for b in (b0, b1, b2):
            bb.addWidget(b)
        lay.addLayout(bb)

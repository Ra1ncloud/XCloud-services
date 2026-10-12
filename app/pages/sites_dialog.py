"""Диалог «Свои сайты» для выбранного пресета."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QListWidget, QListWidgetItem,
                             QComboBox, QCheckBox, QAbstractItemView, QLineEdit)

from ..core import run_async
from ..i18n import tr
from ..presets import build_argv
from .. import sites as S
from ..widgets import label, button, T


class SitesDialog(QDialog):
    def __init__(self, core, preset, parent=None):
        super().__init__(parent)
        self.core, self.preset = core, preset
        self.entry = core.sites.get(preset.id)
        self.domains = list(self.entry["domains"])
        self.ips = dict(self.entry["ips"])
        self.setWindowTitle(tr("Свои сайты"))
        self.resize(620, 640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)
        lay.addWidget(label(tr("Свои сайты"), "h2"))
        lay.addWidget(label(f"{tr('Пресет')}: {preset.name}", "muted", wrap=True))

        # добавление
        self.inp = QPlainTextEdit()
        self.inp.setPlaceholderText(tr("Вставьте один или несколько сайтов — по одному на строку, через пробел или запятую.\n"
                                       "Например: example.com, https://site.org/page, 1.2.3.4"))
        self.inp.setFixedHeight(84)
        lay.addWidget(self.inp)
        h = QHBoxLayout()
        self.msg = label("", "small", wrap=True)
        h.addWidget(self.msg, 1)
        b_add = button(tr("Добавить"), "plus", "primary")
        b_add.clicked.connect(self.add)
        h.addWidget(b_add)
        lay.addLayout(h)

        # список
        h2 = QHBoxLayout()
        self.cnt = label("", "small")
        h2.addWidget(self.cnt, 1)
        self.flt = QLineEdit()
        self.flt.setPlaceholderText(tr("Поиск…"))
        self.flt.setClearButtonEnabled(True)
        self.flt.setFixedWidth(200)
        self.flt.textChanged.connect(self.refill)
        h2.addWidget(self.flt)
        lay.addLayout(h2)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.itemDoubleClicked.connect(self.edit_item)
        lay.addWidget(self.list, 1)
        h3 = QHBoxLayout()
        b_del = button(tr("Удалить выбранные"), "trash")
        b_del.clicked.connect(self.remove)
        b_clr = button(tr("Очистить всё"), "x")
        b_clr.clicked.connect(self.clear)
        h3.addWidget(b_del)
        h3.addWidget(b_clr)
        h3.addStretch(1)
        lay.addLayout(h3)

        # параметры
        lay.addWidget(label(tr("Стратегия"), "small"))
        self.block = QComboBox()
        self.block.addItem(tr("Авто — как у основного блока пресета"), S.AUTO)
        try:
            for d in S.describe_blocks(build_argv(preset.read())):
                if d["strategy"]:
                    self.block.addItem(f"{d['name']}  ·  {d['proto']}", d["name"])
        except OSError:
            pass
        i = self.block.findData(self.entry.get("block", S.AUTO))
        self.block.setCurrentIndex(max(0, i))
        lay.addWidget(self.block)
        h4 = QHBoxLayout()
        self.with_ip = QCheckBox(tr("Также добавлять IP-адреса сайтов (ipset)"))
        self.with_ip.setChecked(bool(self.entry.get("with_ip")))
        self.with_ip.setToolTip(tr("IP определяются через DoH. Осторожно: у сайтов на Cloudflare/CDN один IP "
                                   "общий для множества других сайтов — обход будет работать и на них."))
        h4.addWidget(self.with_ip, 1)
        self.b_ip = button(tr("Обновить IP"), "refresh")
        self.b_ip.clicked.connect(lambda: self.resolve(force=True))
        h4.addWidget(self.b_ip)
        lay.addLayout(h4)
        self.ip_lbl = label("", "small", wrap=True)
        lay.addWidget(self.ip_lbl)

        bb = QHBoxLayout()
        bb.addStretch(1)
        b_cancel = button(tr("Отмена"))
        b_cancel.clicked.connect(self.reject)
        self.b_save = button(tr("Сохранить"), "save", "primary")
        self.b_save.clicked.connect(self.save)
        bb.addWidget(b_cancel)
        bb.addWidget(self.b_save)
        lay.addLayout(bb)
        self.refill()

    # ------------------------------------------------------------
    def refill(self):
        f = self.flt.text().strip().lower()
        self.list.clear()
        for d in self.domains:
            shown = S.display(d)
            if f and f not in shown.lower() and f not in d:
                continue
            ips = self.ips.get(d, [])
            text = shown + (f"    ({len(ips)} IP)" if ips and not S.is_ip(d) else "")
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, d)
            if ips:
                it.setToolTip("\n".join(ips))
            self.list.addItem(it)
        self.cnt.setText(f"{tr('Добавлено сайтов')}: {len(self.domains)}")
        n_ip = sum(len(self.ips.get(d, [])) for d in self.domains)
        self.ip_lbl.setText(f"{tr('Найдено IP')}: {n_ip}" if n_ip else "")

    def add(self):
        good, bad = S.parse_input(self.inp.toPlainText())
        new = [d for d in good if d not in self.domains]
        self.domains += new
        self.inp.clear()
        parts = [f"{tr('Добавлено')}: {len(new)}"]
        if len(good) - len(new):
            parts.append(f"{tr('уже были')}: {len(good) - len(new)}")
        if bad:
            parts.append(f"{tr('не распознано')}: {', '.join(bad[:5])}")
        self.msg.setText("  ·  ".join(parts))
        self.msg.setStyleSheet(f"color:{'#F59E0B' if bad else '#22C55E'};")
        self.refill()

    def selected(self):
        return [it.data(Qt.ItemDataRole.UserRole) for it in self.list.selectedItems()]

    def remove(self):
        sel = set(self.selected())
        self.domains = [d for d in self.domains if d not in sel]
        for d in sel:
            self.ips.pop(d, None)
        self.refill()

    def clear(self):
        self.domains, self.ips = [], {}
        self.refill()

    def edit_item(self, it):
        self.inp.setPlainText(S.display(it.data(Qt.ItemDataRole.UserRole)))
        self.domains.remove(it.data(Qt.ItemDataRole.UserRole))
        self.refill()
        self.inp.setFocus()

    def resolve(self, force=False, then=None):
        todo = [d for d in self.domains if not S.is_ip(d) and (force or d not in self.ips)]
        if not todo:
            if then:
                then()
            return
        self.b_ip.setEnabled(False)
        self.b_save.setEnabled(False)
        self.ip_lbl.setText(tr("Определяю IP-адреса…"))

        def done(res):
            self.ips.update({k: v for k, v in res.items() if v})
            fails = [k for k, v in res.items() if not v]
            self.b_ip.setEnabled(True)
            self.b_save.setEnabled(True)
            self.refill()
            if fails:
                self.ip_lbl.setText(self.ip_lbl.text() + f"  ·  {tr('не удалось определить')}: {', '.join(fails[:5])}")
            if then:
                then()
        run_async(S.resolve_many, todo, done=done,
                  fail=lambda e: (self.b_ip.setEnabled(True), self.b_save.setEnabled(True), self.ip_lbl.setText(e)))

    def save(self):
        if self.inp.toPlainText().strip():
            self.add()
        if self.with_ip.isChecked():
            self.resolve(then=self._commit)
        else:
            self._commit()

    def _commit(self):
        entry = {"domains": self.domains, "ips": {d: v for d, v in self.ips.items() if d in self.domains},
                 "with_ip": self.with_ip.isChecked(), "block": self.block.currentData()}
        self.core.sites.put(self.preset.id, entry)
        self.accept()

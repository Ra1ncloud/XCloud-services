from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QSplitter)

from .. import tester
from ..core import run_async
from ..i18n import tr, cat_label
from ..settings import settings
from ..widgets import Card, label, button, page_header, T


class DiagnosticsPage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(14)
        hdr = QHBoxLayout()
        hdr.addWidget(page_header(tr("Диагностика"), tr("Проверяется текущее состояние сети с активным пресетом.")), 1)
        self.state_lbl = label("", "badge")
        hdr.addWidget(self.state_lbl, 0, Qt.AlignmentFlag.AlignBottom)
        self.btn_check = button(tr("Проверить сейчас"), "activity", "primary")
        self.btn_check.clicked.connect(self.check)
        hdr.addWidget(self.btn_check, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(hdr)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(14)
        # дерево результатов
        left = Card(pad=12)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels([tr("Сервис"), tr("Статус"), tr("Время"), tr("Подробности")])
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in (1, 2, 3):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(12)
        self.tree.setUniformRowHeights(True)
        left.lay.addWidget(self.tree, 1)
        add = QHBoxLayout()
        self.add_edit = QLineEdit()
        self.add_edit.setPlaceholderText(tr("домен, например example.com"))
        self.add_edit.returnPressed.connect(self.add_custom)
        b_add = button(tr("Добавить сайт"), "plus")
        b_add.clicked.connect(self.add_custom)
        b_del = button(tr("Удалить выбранный"), "trash")
        b_del.clicked.connect(self.del_custom)
        add.addWidget(self.add_edit, 1)
        add.addWidget(b_add)
        add.addWidget(b_del)
        left.lay.addLayout(add)
        split.addWidget(left)

        # DNS-подмена
        right = Card(pad=14)
        rh = QHBoxLayout()
        rh.addWidget(label(tr("Проверка DNS-подмены"), "h2"), 1)
        self.btn_dns = button("", "refresh", tip=tr("Проверить сейчас"))
        self.btn_dns.clicked.connect(self.check_dns)
        rh.addWidget(self.btn_dns)
        right.lay.addLayout(rh)
        self.dns_tree = QTreeWidget()
        self.dns_tree.setHeaderLabels(["", tr("Системный DNS"), tr("Через DoH (Google)")])
        self.dns_tree.setRootIsDecorated(False)
        dh = self.dns_tree.header()
        dh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        right.lay.addWidget(self.dns_tree, 1)
        self.dns_note = label("", "small", wrap=True)
        right.lay.addWidget(self.dns_note)
        split.addWidget(right)
        split.setSizes([700, 380])
        root.addWidget(split, 1)

        self.build_tree()
        core.state_changed.connect(self.update_state)
        self.update_state()

    def targets(self):
        return tester.DEFAULT_TARGETS + tester.custom_targets(settings.get("custom_targets"))

    def build_tree(self, results=None):
        self.tree.clear()
        groups = {}
        t = T()
        for tg in self.targets():
            g = groups.get(tg.category)
            if g is None:
                g = QTreeWidgetItem([cat_label(tg.category), "", "", ""])
                f = g.font(0)
                f.setBold(True)
                g.setFont(0, f)
                g.setFirstColumnSpanned(False)
                self.tree.addTopLevelItem(g)
                g.setExpanded(True)
                groups[tg.category] = g
                g._ok = [0, 0]
            name = tg.name + ("" if tg.required else f"  ({tr('необязательно')})")
            it = QTreeWidgetItem([name, "", "", f"{tg.host}:{tg.port}" if tg.kind in ("tcp", "stun") else tg.host])
            it.setData(0, Qt.ItemDataRole.UserRole, tg)
            r = (results or {}).get(tg.id)
            if r is None and results is not None:
                it.setText(1, "…")
            elif r is not None:
                it.setText(1, ("✓ " + tr("Доступен")) if r.ok else ("× " + tr("Недоступен")))
                it.setForeground(1, QColor("#22C55E" if r.ok else "#EF4444"))
                it.setText(2, f"{r.ms} ms")
                it.setText(3, r.detail)
                g._ok[1] += 1
                g._ok[0] += 1 if r.ok else 0
            g.addChild(it)
        for c, g in groups.items():
            if g._ok[1]:
                ok, tot = g._ok
                g.setText(1, f"{ok}/{tot}")
                g.setForeground(1, QColor("#22C55E" if ok == tot else "#F59E0B" if ok else "#EF4444"))

    def update_state(self):
        a = self.core.active()
        self.state_lbl.setText(f"● {a.name}" if a else tr("Пресет не запущен"))
        self.btn_check.setEnabled(not self.core.busy)

    def check(self):
        self.btn_check.setEnabled(False)
        self.btn_check.setText(tr("Проверка…"))
        self.build_tree({})

        def done(res):
            self.btn_check.setEnabled(True)
            self.btn_check.setText(tr("Проверить сейчас"))
            self.build_tree(res)
        run_async(tester.run_checks, self.targets(), 6.0, done=done,
                  fail=lambda e: (self.btn_check.setEnabled(True), self.btn_check.setText(tr("Проверить сейчас"))))
        self.check_dns()

    def check_dns(self):
        self.btn_dns.setEnabled(False)

        def done(rows):
            self.btn_dns.setEnabled(True)
            self.dns_tree.clear()
            bad = 0
            for r in rows:
                it = QTreeWidgetItem([r["name"], ", ".join(r["system"][:2]) or "—", ", ".join(r["doh"][:2]) or "—"])
                it.setForeground(1, QColor("#EF4444" if r["suspicious"] else "#22C55E"))
                it.setToolTip(1, "\n".join(r["system"]))
                it.setToolTip(2, "\n".join(r["doh"]))
                bad += r["suspicious"]
                self.dns_tree.addTopLevelItem(it)
            self.dns_note.setText(("⚠ " + tr("Подозрительно") + ": " + str(bad) + ". " +
                                   (tr("Попробуйте сменить DNS на вкладке DNS.") if bad else ""))
                                  if bad else "✓ " + tr("Норма"))
        run_async(tester.dns_check, done=done, fail=lambda e: self.btn_dns.setEnabled(True))

    def add_custom(self):
        s = self.add_edit.text().strip()
        if not s:
            return
        lst = list(settings.get("custom_targets"))
        if s not in lst:
            lst.append(s)
            settings.set("custom_targets", lst)
        self.add_edit.clear()
        self.build_tree()

    def del_custom(self):
        it = self.tree.currentItem()
        tg = it.data(0, Qt.ItemDataRole.UserRole) if it else None
        if not tg or tg.category != "custom":
            return
        lst = [x for x in settings.get("custom_targets") if tester.custom_targets([x])[0].id != tg.id]
        settings.set("custom_targets", lst)
        self.build_tree()

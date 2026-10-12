from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QCheckBox, QGridLayout

from .. import dns
from ..core import run_async
from ..i18n import tr
from ..settings import settings
from ..widgets import Card, label, button, page_header, Dot


class DnsPage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.adapters = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(14)
        root.addWidget(page_header(tr("DNS")))

        top = Card(pad=16, horizontal=True, spacing=12)
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(label(tr("Сетевой адаптер"), "small"))
        self.adapter = QComboBox()
        self.adapter.setMinimumWidth(320)
        self.adapter.currentIndexChanged.connect(self.show_current)
        col.addWidget(self.adapter)
        top.lay.addLayout(col)
        col2 = QVBoxLayout()
        col2.setSpacing(6)
        col2.addWidget(label(tr("Текущие DNS"), "small"))
        self.current = label("—", "h2")
        col2.addWidget(self.current)
        top.lay.addLayout(col2, 1)
        b_ref = button("", "refresh", tip=tr("Обновить"))
        b_ref.clicked.connect(self.refresh)
        top.lay.addWidget(b_ref)
        root.addWidget(top)

        opts = QHBoxLayout()
        self.doh = QCheckBox(tr("Использовать DNS-over-HTTPS (Windows 11)"))
        self.doh.setChecked(bool(settings.get("dns_doh")) and dns.doh_supported())
        self.doh.setEnabled(dns.doh_supported())
        if not dns.doh_supported():
            self.doh.setToolTip(tr("DoH доступен только в Windows 11"))
        self.doh.toggled.connect(lambda v: settings.set("dns_doh", v))
        opts.addWidget(self.doh)
        opts.addStretch(1)
        b_flush = button(tr("Очистить кэш DNS"), "refresh")
        b_flush.clicked.connect(self.flush)
        b_reset = button(tr("Сбросить (автоматически)"), "x")
        b_reset.clicked.connect(lambda: self.apply(None))
        opts.addWidget(b_flush)
        opts.addWidget(b_reset)
        root.addLayout(opts)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.ping_lbls = {}
        self.cards = {}
        for i, pv in enumerate(dns.PROVIDERS):
            c = Card(pad=16, spacing=6)
            head = QHBoxLayout()
            head.addWidget(Dot(pv["color"], 12))
            head.addWidget(label(pv["name"], "h2"), 1)
            pl = label("", "small")
            self.ping_lbls[pv["id"]] = pl
            head.addWidget(pl)
            c.lay.addLayout(head)
            c.lay.addWidget(label(tr(pv["desc"]), "muted", wrap=True))
            c.lay.addWidget(label("  ·  ".join(pv["ips"]), "small"))
            c.lay.addStretch(1)
            b = button(tr("Применить"), "check", "primary")
            b.clicked.connect(lambda _=False, p=pv: self.apply(p))
            c.lay.addWidget(b)
            c.setMinimumHeight(170)
            self.cards[pv["id"]] = c
            grid.addWidget(c, i // 3, i % 3)
        root.addLayout(grid)
        root.addStretch(1)
        self._loaded = False

    def showEvent(self, e):
        super().showEvent(e)
        if not self._loaded:
            self._loaded = True
            self.refresh()

    def refresh(self):
        def done(ads):
            self.adapters = ads or []
            cur = self.adapter.currentData()
            self.adapter.blockSignals(True)
            self.adapter.clear()
            self.adapter.addItem(tr("Все активные адаптеры"), "all")
            for a in self.adapters:
                self.adapter.addItem(f"{a['name']} — {a.get('desc', '')}", a["index"])
            i = self.adapter.findData(cur)
            self.adapter.setCurrentIndex(i if i >= 0 else 0)
            self.adapter.blockSignals(False)
            self.show_current()
        run_async(dns.list_adapters, done=done)
        self.ping_all()

    def selected(self):
        d = self.adapter.currentData()
        return self.adapters if d == "all" else [a for a in self.adapters if a["index"] == d]

    def show_current(self):
        ips = []
        for a in self.selected():
            for ip in a.get("dns", []):
                if ip not in ips:
                    ips.append(ip)
        self.current.setText(", ".join(ips) if ips else tr("автоматически"))
        for pv in dns.PROVIDERS:
            active = bool(ips) and ips[0] in pv["ips"]
            c = self.cards[pv["id"]]
            c.setStyleSheet(f"QFrame[card='true']{{border:1px solid {pv['color']};}}" if active else "")

    def ping_all(self):
        def work():
            return {pv["id"]: dns.ping_dns(pv["ips"][0]) for pv in dns.PROVIDERS}

        def done(res):
            for k, v in res.items():
                self.ping_lbls[k].setText(f"{tr('Пинг')}: {v} ms" if v is not None else f"{tr('Пинг')}: —")
        run_async(work, done=done)

    def apply(self, provider):
        ads = self.selected()

        def done(r):
            ok, out = r
            if ok:
                self.core.toast.emit(f"{tr('DNS изменён')}: {provider['name']}" if provider else tr("DNS сброшен на автоматический"), "ok")
            else:
                self.core.toast.emit(f"{tr('Ошибка')}: {out[-300:]}", "error")
            self.refresh()
        run_async(dns.apply, provider, ads, self.doh.isChecked(), done=done)

    def flush(self):
        run_async(dns.flush_cache, done=lambda r: self.core.toast.emit(tr("Кэш DNS очищен"), "ok"))

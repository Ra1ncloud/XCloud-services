from PyQt6.QtCore import Qt, QRectF, QSize, QAbstractListModel, QModelIndex, QSortFilterProxyModel, QTimer
from PyQt6.QtGui import QColor, QPainter, QFont, QFontMetrics, QPen
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QListView,
                             QStyledItemDelegate, QStyle, QCheckBox, QSizePolicy)

from ..i18n import tr, cat_label
from ..icons import pixmap, icon
from ..presets import ENGINE_LABEL
from ..settings import settings
from ..widgets import Card, Dot, label, button, T
from ..winutil import open_path

ROLE = Qt.ItemDataRole.UserRole


class PresetModel(QAbstractListModel):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.items = []

    def reload(self):
        self.beginResetModel()
        self.items = list(self.core.presets)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        p = self.items[idx.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return p.name
        if role == ROLE:
            return p
        return None


class PresetFilter(QSortFilterProxyModel):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.text, self.engine, self.kind, self.fav = "", "all", "all", False

    def set(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        p = self.sourceModel().items[row]
        if self.engine != "all" and p.engine != self.engine:
            return False
        if self.kind == "builtin" and not p.builtin or self.kind == "user" and p.builtin:
            return False
        if self.fav and not self.core.is_fav(p):
            return False
        if self.text and self.text.lower() not in (p.name + " " + p.description).lower():
            return False
        return True

    def lessThan(self, a, b):
        pa, pb = self.sourceModel().items[a.row()], self.sourceModel().items[b.row()]
        ka = (not self.core.is_fav(pa), pa.builtin, pa.engine != "winws2", pa.name.lower())
        kb = (not self.core.is_fav(pb), pb.builtin, pb.engine != "winws2", pb.name.lower())
        return ka < kb


class PresetDelegate(QStyledItemDelegate):
    H = 58

    def __init__(self, core):
        super().__init__()
        self.core = core

    def sizeHint(self, opt, idx):
        return QSize(200, self.H)

    def paint(self, p: QPainter, opt, idx):
        t = T()
        pr = idx.data(ROLE)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(opt.rect).adjusted(2, 2, -6, -2)
        sel = opt.state & QStyle.StateFlag.State_Selected
        hov = opt.state & QStyle.StateFlag.State_MouseOver
        active = self.core.active()
        is_active = active is not None and active.id == pr.id
        if sel or hov:
            c = QColor(t.accent)
            c.setAlphaF(0.20 if sel else 0.08)
            p.setBrush(c)
            p.setPen(QPen(QColor(t.accent), 1) if sel else Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 10, 10)
        # цветная метка
        col = QColor(pr.color) if pr.color else QColor(t.accent if pr.engine == "winws2" else "#60A5FA")
        if not col.isValid():
            col = QColor(t.accent)
        col.setAlpha(255)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(QRectF(r.left() + 12, r.center().y() - 14, 4, 28), 2, 2)
        # тексты
        f = QFont(opt.font)
        f.setPointSizeF(10.5)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(QColor(t.text))
        right_w = 150
        name_rect = QRectF(r.left() + 26, r.top() + 8, r.width() - 26 - right_w, 22)
        p.drawText(name_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   QFontMetrics(f).elidedText(pr.name, Qt.TextElideMode.ElideRight, int(name_rect.width())))
        f2 = QFont(opt.font)
        f2.setPointSizeF(8.8)
        p.setFont(f2)
        p.setPen(QColor(t.muted_hex))
        sub = ENGINE_LABEL[pr.engine] + ("  ·  " + tr("Мои") if not pr.builtin else "")
        if pr.description:
            sub += "  ·  " + pr.description
        sr = QRectF(r.left() + 26, r.top() + 30, r.width() - 26 - right_w, 18)
        p.drawText(sr, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   QFontMetrics(f2).elidedText(sub, Qt.TextElideMode.ElideRight, int(sr.width())))
        # справа: активен / оценка / избранное
        x = r.right() - 12
        if self.core.is_fav(pr):
            x -= 18
            p.drawPixmap(int(x), int(r.center().y() - 9), pixmap("star", "#FBBF24", 18, fill="#FBBF24"))
            x -= 8
        res = self.core.results.get(self.core.isp_key, pr.id)
        pills = []
        if is_active:
            pills.append((tr("Активен"), "#22C55E"))
        if res:
            s = res.get("score", 0)
            pills.append((f"{s}%", "#22C55E" if s >= 90 else "#F59E0B" if s >= 50 else "#EF4444"))
        f3 = QFont(opt.font)
        f3.setPointSizeF(8.5)
        f3.setWeight(QFont.Weight.Bold)
        p.setFont(f3)
        fm = QFontMetrics(f3)
        for text, c in pills:
            w = fm.horizontalAdvance(text) + 16
            x -= w
            pr_rect = QRectF(x, r.center().y() - 11, w, 22)
            bc = QColor(c)
            bc.setAlphaF(0.18)
            p.setBrush(bc)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(pr_rect, 6, 6)
            p.setPen(QColor(c))
            p.drawText(pr_rect, Qt.AlignmentFlag.AlignCenter, text)
            x -= 6
        p.restore()


class HomePage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(16)

        # --- карточка статуса ---
        self.status = Card(horizontal=True, pad=18, spacing=14)
        self.dot = Dot("#9CA3AF", 12)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.st_title = label("", "h2")
        self.st_sub = label("", "muted")
        col.addWidget(self.st_title)
        col.addWidget(self.st_sub)
        self.btn_stop = button(tr("Остановить winws"), "power", "danger")
        self.btn_stop.clicked.connect(core.stop)
        self.status.lay.addWidget(self.dot)
        self.status.lay.addLayout(col, 1)
        self.status.lay.addWidget(self.btn_stop)
        root.addWidget(self.status)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        # --- список ---
        left = Card(pad=12, spacing=10)
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Поиск пресетов…"))
        self.search.addAction(icon("search", T().muted_hex, 16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setClearButtonEnabled(True)
        self.engine = QComboBox()
        for k, v in (("all", tr("Все движки")), ("winws2", "Zapret 2"), ("winws1", "Zapret 1")):
            self.engine.addItem(v, k)
        self.kind = QComboBox()
        for k, v in (("all", tr("Все")), ("builtin", tr("Встроенные")), ("user", tr("Мои"))):
            self.kind.addItem(v, k)
        self.fav = QCheckBox(tr("Только избранные"))
        bar.addWidget(self.search, 1)
        bar.addWidget(self.engine)
        bar.addWidget(self.kind)
        bar.addWidget(self.fav)
        left.lay.addLayout(bar)

        self.model = PresetModel(core)
        self.proxy = PresetFilter(core)
        self.proxy.setSourceModel(self.model)
        self.view = QListView()
        self.view.setModel(self.proxy)
        self.view.setItemDelegate(PresetDelegate(core))
        self.view.setMouseTracking(True)
        self.view.setUniformItemSizes(True)
        self.view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.view.verticalScrollBar().setSingleStep(18)
        self.view.selectionModel().currentChanged.connect(lambda *_: self.show_details())
        self.view.doubleClicked.connect(lambda *_: self.activate())
        left.lay.addWidget(self.view, 1)
        self.count = label("", "small")
        left.lay.addWidget(self.count)
        body.addWidget(left, 1)

        # --- детали ---
        right = Card(pad=18, spacing=10)
        right.setFixedWidth(320)
        self.d_name = label("", "h2", wrap=True)
        self.d_badges = QHBoxLayout()
        self.d_badges.setSpacing(6)
        self.d_desc = label("", "muted", wrap=True)
        self.d_res_title = label(tr("Результаты тестов у вашего провайдера"), "small")
        self.d_res = label("", wrap=True)
        self.d_res.setTextFormat(Qt.TextFormat.RichText)
        right.lay.addWidget(self.d_name)
        right.lay.addLayout(self.d_badges)
        right.lay.addWidget(self.d_desc)
        right.lay.addSpacing(6)
        right.lay.addWidget(self.d_res_title)
        right.lay.addWidget(self.d_res)
        right.lay.addStretch(1)
        self.btn_sites = button(tr("Свои сайты"), "globe")
        self.btn_sites.setToolTip(tr("Добавить сайты, на которых этот пресет будет обходить блокировку"))
        self.btn_fav = button(tr("В избранное"), "star")
        self.btn_copy = button(tr("Копировать и изменить"), "copy")
        self.btn_file = button(tr("Открыть файл"), "file")
        self.btn_act = button(tr("Активировать"), "play", "primary")
        self.btn_act.setMinimumHeight(44)
        for b in (self.btn_sites, self.btn_fav, self.btn_copy, self.btn_file):
            right.lay.addWidget(b)
        right.lay.addSpacing(4)
        right.lay.addWidget(self.btn_act)
        body.addWidget(right)

        self.btn_act.clicked.connect(self.activate)
        self.btn_sites.clicked.connect(self.edit_sites)
        self.btn_fav.clicked.connect(lambda: self.cur() and core.toggle_fav(self.cur()))
        self.btn_copy.clicked.connect(lambda: self.cur() and core.edit_preset.emit(self.cur()))
        self.btn_file.clicked.connect(lambda: self.cur() and open_path(self.cur().path))
        self.search.textChanged.connect(lambda s: self._filter(text=s))
        self.engine.currentIndexChanged.connect(lambda: self._filter(engine=self.engine.currentData()))
        self.kind.currentIndexChanged.connect(lambda: self._filter(kind=self.kind.currentData()))
        self.fav.toggled.connect(lambda v: self._filter(fav=v))

        core.presets_changed.connect(self.reload)
        core.state_changed.connect(self.update_state)
        core.results_changed.connect(lambda: (self.view.viewport().update(), self.show_details()))
        self._tick = QTimer(self)
        self._tick.timeout.connect(self.update_state)
        self._tick.start(1000)
        self.reload()
        self.update_state()

    # ---------------------------------------------------------------
    def _filter(self, **kw):
        self.proxy.set(**kw)
        self.proxy.sort(0)
        self.count.setText(f"{self.proxy.rowCount()} {tr('пресетов')}")

    def reload(self):
        cur = self.cur()
        self.model.reload()
        self.proxy.sort(0)
        self._filter()
        target = cur.id if cur else settings.get("last_preset")
        self.select_id(target)
        self.show_details()

    def select_id(self, pid):
        for r in range(self.proxy.rowCount()):
            ix = self.proxy.index(r, 0)
            if ix.data(ROLE).id == pid:
                self.view.setCurrentIndex(ix)
                self.view.scrollTo(ix, QListView.ScrollHint.PositionAtCenter)
                return
        if self.proxy.rowCount():
            self.view.setCurrentIndex(self.proxy.index(0, 0))

    def cur(self):
        ix = self.view.currentIndex()
        return ix.data(ROLE) if ix.isValid() else None

    def activate(self):
        p = self.cur()
        if p:
            self.core.activate(p)

    def edit_sites(self):
        from .sites_dialog import SitesDialog
        p = self.cur()
        if not p:
            return
        d = SitesDialog(self.core, p, self.window())
        if d.exec():
            self.show_details()
            a = self.core.active()
            if a and a.id == p.id:
                self.core.toast.emit(tr("Сайты сохранены, пресет перезапускается"), "ok")
                self.core.activate(p, quiet=True)
            else:
                self.core.toast.emit(tr("Сайты сохранены"), "ok")

    def show_details(self):
        p = self.cur()
        while self.d_badges.count():
            w = self.d_badges.takeAt(0).widget()
            if w:
                w.hide()
                w.deleteLater()
        for b in (self.btn_act, self.btn_sites, self.btn_fav, self.btn_copy, self.btn_file):
            b.setEnabled(p is not None)
        if not p:
            self.d_name.setText("—")
            self.d_desc.setText("")
            self.d_res.setText("")
            return
        self.d_name.setText(p.name)
        badges = [ENGINE_LABEL[p.engine]] + ([] if p.builtin else [tr("Пользовательский")])
        if p.game_filter:
            badges.append(tr("Игровой фильтр"))
        if self.core.results.best(self.core.isp_key) == p.id:
            badges.append("★ " + tr("Лучший для провайдера"))
        for b in badges:
            self.d_badges.addWidget(label(b, "badge"))
        self.d_badges.addStretch(1)
        self.d_desc.setText(p.description or tr("Описание отсутствует"))
        n = self.core.sites.count(p.id)
        self.btn_sites.setText(f"{tr('Свои сайты')} ({n})" if n else tr("Свои сайты"))
        self.btn_fav.setText(tr("Убрать из избранного") if self.core.is_fav(p) else tr("В избранное"))
        res = self.core.results.get(self.core.isp_key, p.id)
        if res:
            rows = []
            for c, (ok, tot) in res.get("cats", {}).items():
                color = "#22C55E" if ok == tot else "#F59E0B" if ok else "#EF4444"
                mark = "●"
                rows.append(f"<tr><td style='color:{color}; padding-right:6px'>{mark}</td>"
                            f"<td style='padding-right:12px'>{cat_label(c)}</td><td align='right'>{ok}/{tot}</td></tr>")
            self.d_res.setText(f"<b style='font-size:20px'>{res.get('score', 0)}%</b>"
                               f"<table style='margin-top:6px'>{''.join(rows)}</table>")
        else:
            self.d_res.setText(f"<span style='color:{T().muted_hex}'>"
                               f"{tr('Пресет ещё не тестировался. Запустите автоподбор.')}</span>")

    def update_state(self):
        if not self.isVisible() and self.sender() is self._tick:
            return   # окно скрыто — не тратим ресурсы
        c = self.core
        a = c.active()
        if c.starting:
            self.dot.set_color("#F59E0B")
            self.dot.set_pulse(True)
            self.st_title.setText(tr("Запускается…"))
            self.st_sub.setText("")
        elif a:
            self.dot.set_color("#22C55E")
            self.dot.set_pulse(True)
            up = c.runner.uptime()
            self.st_title.setText(f"{tr('Активен')}: {a.name}")
            self.st_sub.setText(f"{ENGINE_LABEL[a.engine]}  ·  PID {c.runner.proc.pid}  ·  "
                                f"{tr('Работает')} {up // 3600:02d}:{up % 3600 // 60:02d}:{up % 60:02d}")
        elif c.external:
            self.dot.set_color("#F59E0B")
            self.dot.set_pulse(False)
            self.st_title.setText(tr("Обнаружен запущенный winws (запущен не из программы)"))
            self.st_sub.setText(", ".join(f"{n} (PID {pid})" for n, pid in c.external))
        else:
            self.dot.set_color("#9CA3AF")
            self.dot.set_pulse(False)
            self.st_title.setText(tr("Пресет не запущен"))
            self.st_sub.setText(tr("Выберите пресет в списке и нажмите «Активировать»"))
        self.btn_stop.setEnabled(bool(a or c.external) and not c.busy)
        self.btn_act.setEnabled(self.cur() is not None and not c.busy and not c.starting)
        if not self._tick.isActive() or a is None:
            pass
        self.view.viewport().update()

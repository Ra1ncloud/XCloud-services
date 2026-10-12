import time

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout,
                             QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)

from .. import tester
from ..core import run_async
from ..i18n import tr, cat_label
from ..presets import ENGINE_LABEL
from ..settings import settings
from ..widgets import Card, label, button, page_header, T

CATS = ["youtube", "discord", "telegram", "games", "ai"]


class TuneWorker(QThread):
    progress = pyqtSignal(int, int, str)
    result = pyqtSignal(object, object)      # preset, summary
    finished_all = pyqtSignal(bool)

    def __init__(self, core, presets, targets, timeout, warmup, stop_on_perfect):
        super().__init__()
        self.core, self.presets, self.targets = core, presets, targets
        self.timeout, self.warmup, self.stop_on_perfect = timeout, warmup, stop_on_perfect
        self.cancel = False

    def run(self):
        runner = self.core.runner
        completed = True
        for i, p in enumerate(self.presets):
            if self.cancel:
                completed = False
                break
            self.progress.emit(i, len(self.presets), f"{p.name} · {ENGINE_LABEL.get(p.engine, p.engine)}")
            ok, msg = runner.start(p, wait=1.2)
            if not ok:
                self.result.emit(p, {"ok": 0, "total": 0, "score": 0, "cats": {}, "error": msg[:200], "ms": 0})
                continue
            t_end = time.time() + self.warmup
            while time.time() < t_end and not self.cancel:
                time.sleep(0.1)
            t0 = time.perf_counter()
            res = tester.run_checks(self.targets, self.timeout)
            summ = tester.summarize(self.targets, res)
            summ["ms"] = int((time.perf_counter() - t0) * 1000)
            summ["details"] = {k: [v.ok, v.ms, v.detail] for k, v in res.items()}
            self.result.emit(p, summ)
            if self.stop_on_perfect and summ["score"] == 100:
                break
        runner.stop(full=False)
        self.progress.emit(len(self.presets), len(self.presets), "")
        self.finished_all.emit(completed)


class AutotunePage(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.worker = None
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(14)
        root.addWidget(page_header(tr("Автоподбор"),
                                   tr("Во время подбора текущий пресет будет остановлен.") + " " +
                                   tr("Результаты сохраняются для каждого провайдера отдельно.")))

        top = QHBoxLayout()
        top.setSpacing(14)
        # провайдер
        isp = Card(pad=16)
        isp.setFixedWidth(260)
        isp.lay.addWidget(label(tr("Провайдер"), "small"))
        self.isp_name = label("", "h2", wrap=True)
        self.isp_sub = label("", "muted", wrap=True)
        self.btn_isp = button(tr("Определить"), "wifi")
        self.btn_isp.clicked.connect(self.detect_isp)
        isp.lay.addWidget(self.isp_name)
        isp.lay.addWidget(self.isp_sub)
        isp.lay.addStretch(1)
        isp.lay.addWidget(self.btn_isp)
        top.addWidget(isp)

        # настройки
        opt = Card(pad=16)
        opt.lay.addWidget(label(tr("Что должно работать"), "small"))
        cats = QHBoxLayout()
        self.cat_boxes = {}
        for c in CATS:
            cb = QCheckBox(cat_label(c))
            cb.setChecked(c in settings.get("autotune_categories"))
            cb.toggled.connect(self.save_opts)
            self.cat_boxes[c] = cb
            cats.addWidget(cb)
        self.cb_custom = QCheckBox(cat_label("custom"))
        self.cb_custom.setChecked("custom" in settings.get("autotune_categories"))
        self.cb_custom.toggled.connect(self.save_opts)
        cats.addWidget(self.cb_custom)
        cats.addStretch(1)
        opt.lay.addLayout(cats)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.scope = QComboBox()
        for k, v in (("all", tr("Все пресеты")), ("winws2", tr("Только Zapret 2")), ("winws1", tr("Только Zapret 1")),
                     ("nogame", tr("Без игрового фильтра")), ("fav", tr("Избранные")), ("user", tr("Мои"))):
            self.scope.addItem(v, k)
        self.scope.setMinimumWidth(200)
        self.scope.setCurrentIndex(max(0, self.scope.findData(settings.get("autotune_scope"))))
        self.scope.currentIndexChanged.connect(self.save_opts)
        self.scope.currentIndexChanged.connect(lambda: self.fill_table())
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(2, 15)
        self.timeout.setDecimals(1)
        self.timeout.setFixedWidth(70)
        self.timeout.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.timeout.setValue(float(settings.get("autotune_timeout")))
        self.timeout.valueChanged.connect(self.save_opts)
        self.warmup = QDoubleSpinBox()
        self.warmup.setRange(0.5, 10)
        self.warmup.setDecimals(1)
        self.warmup.setFixedWidth(70)
        self.warmup.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.warmup.setValue(float(settings.get("autotune_warmup")))
        self.warmup.valueChanged.connect(self.save_opts)
        grid.addWidget(label(tr("Набор пресетов"), "muted"), 0, 0)
        grid.addWidget(self.scope, 0, 1)
        grid.addWidget(label(tr("Таймаут проверки, с"), "muted"), 0, 3)
        grid.addWidget(self.timeout, 0, 4)
        grid.addWidget(label(tr("Прогрев после запуска, с"), "muted"), 1, 3)
        grid.addWidget(self.warmup, 1, 4)
        grid.setColumnStretch(2, 1)
        opt.lay.addLayout(grid)
        self.cb_stop = QCheckBox(tr("Остановиться на первом, где работает всё"))
        self.cb_stop.setChecked(bool(settings.get("autotune_stop_on_perfect")))
        self.cb_stop.toggled.connect(self.save_opts)
        grid.addWidget(self.cb_stop, 1, 0, 1, 2)
        prow = QHBoxLayout()
        self.prog = QProgressBar()
        self.prog.setFixedHeight(8)
        self.prog_text = label(tr("Готов к подбору"), "muted")
        self.btn_start = button(tr("Начать подбор"), "zap", "primary")
        self.btn_stop = button(tr("Остановить"), "stop", "danger")
        self.btn_stop.hide()
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(self.prog_text)
        col.addWidget(self.prog)
        prow.addLayout(col, 1)
        prow.addSpacing(12)
        prow.addWidget(self.btn_start)
        prow.addWidget(self.btn_stop)
        opt.lay.addLayout(prow)
        top.addWidget(opt, 1)
        root.addLayout(top)

        # таблица результатов
        tab = Card(pad=12)
        hdr = QHBoxLayout()
        hdr.addWidget(label(tr("Матрица совместимости"), "h2"))
        hdr.addWidget(label(tr("Какие сервисы работают на каждом проверенном пресете у текущего провайдера."), "muted"), 1)
        tab.lay.addLayout(hdr)
        self.table = QTableWidget(0, 3 + len(CATS) + 1)
        self.table.setHorizontalHeaderLabels([tr("Пресет"), tr("Движок"), tr("Итог")] + [cat_label(c) for c in CATS] + [cat_label("custom")])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, self.table.columnCount()):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(i, 104 if i == 7 else 84 if i > 2 else 78)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.doubleClicked.connect(self.activate_selected)
        tab.lay.addWidget(self.table, 1)
        brow = QHBoxLayout()
        self.best_lbl = label("", "muted")
        brow.addWidget(self.best_lbl, 1)
        self.btn_clear = button(tr("Очистить результаты"), "trash")
        self.btn_clear.clicked.connect(self.clear)
        self.btn_sel = button(tr("Активировать выбранный"), "play")
        self.btn_sel.clicked.connect(self.activate_selected)
        self.btn_best = button(tr("Применить лучший"), "zap", "primary")
        self.btn_best.clicked.connect(self.apply_best)
        for b in (self.btn_clear, self.btn_sel, self.btn_best):
            brow.addWidget(b)
        tab.lay.addLayout(brow)
        root.addWidget(tab, 1)

        core.isp_changed.connect(self.refresh)
        core.results_changed.connect(self.fill_table)
        core.presets_changed.connect(self.fill_table)
        self.refresh()

    # ---------------------------------------------------------------
    def save_opts(self):
        cats = [c for c, cb in self.cat_boxes.items() if cb.isChecked()]
        if self.cb_custom.isChecked():
            cats.append("custom")
        settings.data.update(autotune_categories=cats, autotune_scope=self.scope.currentData(),
                             autotune_timeout=self.timeout.value(), autotune_warmup=self.warmup.value(),
                             autotune_stop_on_perfect=self.cb_stop.isChecked())
        settings.save()
        self.update_estimate()

    def scope_presets(self):
        s = self.scope.currentData()
        ps = self.core.presets
        if s in ("winws1", "winws2"):
            ps = [p for p in ps if p.engine == s]
        elif s == "nogame":
            ps = [p for p in ps if not p.game_filter]
        elif s == "fav":
            ps = [p for p in ps if self.core.is_fav(p)]
        elif s == "user":
            ps = [p for p in ps if not p.builtin]
        return ps

    def targets(self):
        cats = settings.get("autotune_categories")
        ts = [t for t in tester.DEFAULT_TARGETS if t.category in cats]
        if "custom" in cats:
            ts += tester.custom_targets(settings.get("custom_targets"))
        return ts

    def update_estimate(self):
        if self.worker:
            return
        n = len(self.scope_presets())
        sec = n * (1.2 + self.warmup.value() + min(self.timeout.value(), 3.0) + 0.6)
        self.prog_text.setText(f"{tr('Готов к подбору')}: {n} {tr('пресетов')} · "
                               f"{tr('Подбор займёт примерно')} {max(1, round(sec / 60))} {tr('мин')}")

    def refresh(self):
        i = self.core.isp_info
        if i and i.get("isp"):
            self.isp_name.setText(i.get("isp"))
            self.isp_sub.setText("  ·  ".join(x for x in (i.get("as", "").split(" ")[0], i.get("city", ""), i.get("ip", "")) if x))
        else:
            self.isp_name.setText(tr("Неизвестно"))
            self.isp_sub.setText("")
        self.fill_table()
        self.update_estimate()

    def detect_isp(self, then=None):
        self.btn_isp.setEnabled(False)
        self.btn_isp.setText(tr("Определение…"))

        def done(info):
            self.btn_isp.setEnabled(True)
            self.btn_isp.setText(tr("Определить"))
            if info.get("isp"):
                self.core.isp_info = info
                settings.set("isp_info", info)
                self.core.isp_changed.emit()
            if then:
                then()
        run_async(tester.detect_isp, done=done, fail=lambda e: done({}))

    def start(self):
        if not self.core.runner:
            return
        presets = self.scope_presets()
        targets = self.targets()
        if not presets or not targets:
            return
        if not self.core.isp_info.get("isp"):
            # определяем провайдера до запуска winws
            self.core.runner.stop()
            return self.detect_isp(then=self.start)
        v = self.core.vpn
        if v.state in ("on", "starting"):
            # VPN исказил бы результаты (часть сайтов пошла бы через сервер) — выключаем на время подбора
            self._vpn_resume = True
            self.core.toast.emit(tr("VPN выключен на время автоподбора и включится после него"), "info")
            v.stop(done=self.start, remember=False)
            return
        self.core.busy = True
        self.core.state_changed.emit()
        self.btn_start.hide()
        self.btn_stop.show()
        self.prog.setRange(0, len(presets))
        self.prog.setValue(0)
        self.worker = TuneWorker(self.core, presets, targets, self.timeout.value(), self.warmup.value(),
                                 self.cb_stop.isChecked())
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.finished_all.connect(self.on_done)
        self.worker.start()

    def stop(self):
        if self.worker:
            self.worker.cancel = True
            self.btn_stop.setEnabled(False)

    def on_progress(self, i, n, name):
        self.prog.setValue(i)
        if name:
            self.prog_text.setText(f"{tr('Проверяется')} {i + 1}/{n}: {name}")
        self.core.state_changed.emit()

    def on_result(self, preset, summ):
        self.core.results.put(self.core.isp_key, self.core.isp_info.get("isp", ""), preset.id, summ)
        self.core.results_changed.emit()

    def on_done(self, completed):
        self.worker = None
        self.core.busy = False
        if getattr(self, "_vpn_resume", False):
            self._vpn_resume = False
            self.core.vpn.start()
        self.btn_stop.setEnabled(True)
        self.btn_stop.hide()
        self.btn_start.show()
        best = self.core.by_id(self.core.results.best(self.core.isp_key))
        self.prog_text.setText(tr("Подбор завершён") if completed else tr("Подбор остановлен"))
        self.core.state_changed.emit()
        if best:
            self.core.toast.emit(f"{tr('Лучший пресет')}: {best.name}", "ok")

    def fill_table(self):
        d = self.core.results.data.get(self.core.isp_key, {})
        rows = d.get("presets", {})
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        t = T()
        # таблица показывает только выбранный набор (иначе видны старые результаты другого движка
        # и кажется, что подбор шёл по всем пресетам)
        scope_ids = {p.id for p in self.scope_presets()}
        for pid, s in rows.items():
            p = self.core.by_id(pid)
            if not p or pid not in scope_ids:
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            it = QTableWidgetItem(("★ " if pid == d.get("best") else "") + p.name)
            it.setData(Qt.ItemDataRole.UserRole, pid)
            if s.get("error"):
                it.setToolTip(s["error"])
            self.table.setItem(r, 0, it)
            self.table.setItem(r, 1, QTableWidgetItem(ENGINE_LABEL[p.engine]))
            score = s.get("score", 0)
            txt = f"{score}%" if not s.get("error") else tr("ошибка запуска")
            col = QColor("#22C55E" if score >= 90 else "#F59E0B" if score >= 50 else "#EF4444")
            self.table.setItem(r, 2, _NumItem(score, txt, col))
            for j, c in enumerate(CATS + ["custom"]):
                v = s.get("cats", {}).get(c)
                if not v:
                    self.table.setItem(r, 3 + j, QTableWidgetItem("—"))
                    continue
                ok, tot = v
                cell = _NumItem(ok / tot if tot else 0, ("✓ " if ok == tot else "× " if ok == 0 else "● ") + f"{ok}/{tot}",
                                QColor("#22C55E" if ok == tot else "#EF4444" if ok == 0 else "#F59E0B"))
                det = s.get("details", {})
                tip = [f"{'✓' if dv[0] else '×'} {tid}: {dv[2]} ({dv[1]} ms)" for tid, dv in det.items()
                       if any(tt.id == tid and tt.category == c for tt in tester.DEFAULT_TARGETS) or (c == "custom" and tid.startswith("c_"))]
                cell.setToolTip("\n".join(tip))
                self.table.setItem(r, 3 + j, cell)
        self.table.setSortingEnabled(True)
        self.table.sortItems(2, Qt.SortOrder.DescendingOrder)
        best = self.core.by_id(d.get("best"))
        self.best_lbl.setText(f"{tr('Лучший пресет')}: {best.name}" if best else "")
        self.btn_best.setEnabled(best is not None)

    def selected(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        return self.core.by_id(self.table.item(r, 0).data(Qt.ItemDataRole.UserRole))

    def activate_selected(self, *_):
        p = self.selected()
        if p and not self.core.busy:
            self.core.activate(p)

    def apply_best(self):
        p = self.core.by_id(self.core.results.best(self.core.isp_key))
        if p and not self.core.busy:
            self.core.activate(p)

    def clear(self):
        if not self.core.busy:
            self.core.results.clear(self.core.isp_key)
            self.core.results_changed.emit()


class _NumItem(QTableWidgetItem):
    def __init__(self, num, text, color):
        super().__init__(text)
        self.num = num
        self.setForeground(color)
        self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def __lt__(self, other):
        if isinstance(other, _NumItem):
            return self.num < other.num
        return super().__lt__(other)

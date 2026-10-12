"""Общее состояние приложения: пресеты, запуск, результаты тестов, сигналы для интерфейса."""
import json
import threading
import time
import traceback
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, QTimer

from . import presets as P
from .paths import data_dir, user_presets_dir
from .runner import Runner, find_winws
from .settings import settings
from .i18n import tr


class _Sig(QObject):
    done = pyqtSignal(object)
    fail = pyqtSignal(str)


class Task(QRunnable):
    def __init__(self, fn, *a, **kw):
        super().__init__()
        self.fn, self.a, self.kw = fn, a, kw
        self.sig = _Sig()

    def run(self):
        try:
            r = self.fn(*self.a, **self.kw)
        except Exception as e:  # noqa
            traceback.print_exc()
            try:
                self.sig.fail.emit(str(e))
            except RuntimeError:
                pass
            return
        try:
            self.sig.done.emit(r)
        except RuntimeError:
            pass


_keep = set()


def run_async(fn, *a, done=None, fail=None, **kw):
    t = Task(fn, *a, **kw)
    _keep.add(t.sig)

    def _d(r):
        _keep.discard(t.sig)
        if done:
            done(r)

    def _f(e):
        _keep.discard(t.sig)
        if fail:
            fail(e)
    t.sig.done.connect(_d)
    t.sig.fail.connect(_f)
    QThreadPool.globalInstance().start(t)


class Results:
    """Результаты тестов пресетов по провайдерам: data/results.json"""

    def __init__(self):
        self.path = data_dir() / "results.json"
        self.lock = threading.Lock()
        try:
            self.data = json.loads(self.path.read_text("utf-8"))
        except Exception:
            self.data = {}

    def isp(self, key) -> dict:
        return self.data.setdefault(key, {"isp": "", "presets": {}, "best": None})

    def put(self, key, isp_name, preset_id, summary):
        with self.lock:
            d = self.isp(key)
            d["isp"] = isp_name or d.get("isp", "")
            summary = dict(summary, time=int(time.time()))
            d["presets"][preset_id] = summary
            best = max(d["presets"].items(), key=lambda kv: (kv[1].get("score", 0), -kv[1].get("ms", 10**9)))
            d["best"] = best[0]
            self.save()

    def get(self, key, preset_id):
        return self.data.get(key, {}).get("presets", {}).get(preset_id)

    def best(self, key):
        return self.data.get(key, {}).get("best")

    def clear(self, key):
        with self.lock:
            self.data.pop(key, None)
            self.save()

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(self.path)


class Core(QObject):
    state_changed = pyqtSignal()
    presets_changed = pyqtSignal()
    theme_changed = pyqtSignal()
    isp_changed = pyqtSignal()
    results_changed = pyqtSignal()
    toast = pyqtSignal(str, str)        # текст, тип: info|ok|error
    navigate = pyqtSignal(str)
    edit_preset = pyqtSignal(object)    # Preset для копирования в редактор
    conflicts_found = pyqtSignal(object, object)   # preset, [конфликты]
    watchdog_alert = pyqtSignal(object)            # {"failed": [...], "suggest": Preset|None, ...}
    watch_changed = pyqtSignal()
    updates_found = pyqtSignal(object)             # [компоненты с обновлением]
    app_update_ready = pyqtSignal(str)             # путь к скачанному установщику новой версии
    update_progress = pyqtSignal(str, float)
    update_done = pyqtSignal(bool, str)

    def __init__(self, root: Path | None):
        super().__init__()
        self.root = root
        self.data = data_dir()
        self.user_dir = user_presets_dir()
        from .sites import SiteStore
        self.sites = SiteStore(self.data)
        self.runner = Runner(root, self.data, self.sites) if root else None
        from .vpn.manager import VpnManager
        self.vpn = VpnManager(self.data)
        self.vpn.toast.connect(self.toast.emit)
        self.vpn.state_changed.connect(self._on_vpn_state)
        self._vpn_tun_seen = False
        self._iface_fix_at = 0
        if self.runner:
            self.runner.extra_args = self.vpn.winws_args
        self.presets: list[P.Preset] = []
        self.results = Results()
        self.isp_info = settings.get("isp_info") or {}
        self.busy = False          # идёт автоподбор
        self.starting = False
        self.external = []         # winws, запущенные не нами
        self.reload_presets()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(3000)
        self._was_alive = False
        self.vpn_warned = False
        self.updating = False
        # сторож
        from .watchdog import Watchdog
        self.watchdog = Watchdog()
        self._watch_running = False
        self._wd_timer = QTimer(self)
        self._wd_timer.timeout.connect(self._watch_tick)
        self.apply_watchdog_settings()
        # автопроверка обновлений (раз в 24 часа, пока программа запущена)
        self._upd_timer = QTimer(self)
        self._upd_timer.timeout.connect(self._update_tick)
        self._upd_timer.start(30 * 60 * 1000)
        QTimer.singleShot(90 * 1000, self._update_tick)

    @property
    def isp_key(self):
        from .tester import isp_key
        return isp_key(self.isp_info) if self.isp_info else "unknown"

    def set_root(self, root: Path):
        self.root = root
        self.runner = Runner(root, self.data, self.sites)
        self.runner.extra_args = self.vpn.winws_args
        settings.set("root", str(root))
        self.reload_presets()

    def reload_presets(self):
        self.presets = P.load_all(self.root, self.user_dir) if self.root else []
        self.presets_changed.emit()

    def by_id(self, pid):
        return next((p for p in self.presets if p.id == pid), None)

    def active(self):
        return self.runner.preset if self.runner and self.runner.alive() else None

    # ---- избранное ----
    def is_fav(self, p):
        return p.id in settings.get("favorites")

    def toggle_fav(self, p):
        fav = list(settings.get("favorites"))
        fav.remove(p.id) if p.id in fav else fav.append(p.id)
        settings.set("favorites", fav)
        self.presets_changed.emit()

    # ---- запуск ----
    def activate(self, preset, quiet=False, skip_conflicts=False):
        if not self.runner or self.busy or self.starting or self.updating:
            return
        self.starting = True
        self.state_changed.emit()

        def work():
            if not skip_conflicts:
                from . import conflicts
                own = [self.runner.proc.pid] if self.runner.alive() else []
                found = conflicts.detect(own)
                if any(c["blocking"] for c in found):
                    return "conflict", found
                vpn = [c for c in found if c["kind"] == "vpn"]
            else:
                vpn = []
            ok, msg = self.runner.start(preset)
            return ("ok" if ok else "fail", msg if not vpn else (msg, vpn))

        def done(r):
            kind, payload = r
            self.starting = False
            if kind == "conflict":
                self.state_changed.emit()
                self.conflicts_found.emit(preset, payload)
                return
            vpn = []
            if isinstance(payload, tuple):
                payload, vpn = payload
            ok, msg = kind == "ok", payload
            if vpn and not self.vpn_warned:
                self.vpn_warned = True
                self.toast.emit(tr("Включён VPN — он может мешать обходу") + f": {vpn[0]['id']}", "info")
            if ok:
                self.watchdog.reset(preset.id)
                QTimer.singleShot(20 * 1000, self._watch_tick)
                settings.set("last_preset", preset.id)
                if not quiet:
                    self.toast.emit(f"{preset.name}", "ok")
            else:
                self.toast.emit(msg[:400], "error")
            self.state_changed.emit()
        run_async(work, done=done,
                  fail=lambda e: (setattr(self, "starting", False), self.toast.emit(e, "error"), self.state_changed.emit()))

    def stop(self):
        if not self.runner:
            return
        run_async(self.runner.stop, full=bool(settings.get("full_stop")),
                  done=lambda r: (self.state_changed.emit()))

    def _poll(self):
        alive = bool(self.runner and self.runner.alive())
        if alive and not (self.busy or self.starting or self.updating) and self.vpn.state in ("on", "off") \
                and self.runner.extra_used != self.vpn.winws_args() and time.time() - self._iface_fix_at > 10:
            # winws запущен с устаревшим фильтром интерфейса (VPN TUN включили/выключили) — перезапускаем
            self._iface_fix_at = time.time()
            self.activate(self.runner.preset, quiet=True, skip_conflicts=True)
            return
        ext_before = bool(self.external)
        if alive and self._was_alive and not ext_before:
            return   # наш winws работает — сканировать процессы не нужно

        def done(found):
            self.external = [] if alive else found
            if alive != self._was_alive or bool(self.external) != ext_before:
                if self._was_alive and not alive and self.runner and not self.busy:
                    self.toast.emit("winws завершился", "error")
                self._was_alive = alive
                self.state_changed.emit()
        if not self.busy and not self.updating:
            run_async(find_winws, done=done)

    # ---- сторож ----
    def apply_watchdog_settings(self):
        if settings.get("watchdog"):
            self._wd_timer.start(max(1, int(settings.get("watchdog_interval") or 5)) * 60 * 1000)
        else:
            self._wd_timer.stop()

    def _watch_tick(self):
        a = self.active()
        if not settings.get("watchdog") or not a or self.busy or self.starting or self._watch_running:
            return
        if self.watchdog.preset_id != a.id:
            self.watchdog.reset(a.id)
        self._watch_running = True
        cats = [c for c in settings.get("autotune_categories") if c != "custom"] or ["youtube", "discord"]

        def done(r):
            self._watch_running = False
            self.watch_changed.emit()
            if r.get("status") == "alert" and self.active() and self.active().id == a.id:
                r["preset"] = a
                r["suggest"] = self.suggest_preset(a)
                self.watchdog_alert.emit(r)
        run_async(self.watchdog.run, cats, done=done, fail=lambda e: setattr(self, "_watch_running", False))

    def suggest_preset(self, current):
        d = self.results.data.get(self.isp_key, {}).get("presets", {})
        cur = d.get(current.id, {}).get("score", -1)
        best = None
        for pid, r in sorted(d.items(), key=lambda kv: -kv[1].get("score", 0)):
            if pid == current.id:
                continue
            p = self.by_id(pid)
            if p and r.get("score", 0) > max(cur, 0) - 1 and r.get("score", 0) >= 50:
                best = (p, r.get("score", 0))
                break
        return best

    # ---- VPN ----
    def _on_vpn_state(self):
        """При включении/выключении TUN перезапускаем winws: ему нужен фильтр по физическому интерфейсу."""
        tun = self.vpn.state == "on" and self.vpn.mode == "tun"
        if self.vpn.state in ("on", "off") and tun != self._vpn_tun_seen:
            self._vpn_tun_seen = tun
            a = self.active()
            if a and not self.busy:
                self.activate(a, quiet=True, skip_conflicts=True)
        self.state_changed.emit()

    def vpn_startup(self):
        v = self.vpn
        if v.installed() and v.store.server() and (settings.get("vpn_autostart") or False):
            v.start()
        if v.store.subs:
            QTimer.singleShot(20000, lambda: v.refresh_subs(only_old=True))

    # ---- обновления движка ----
    def _update_tick(self):
        if not settings.get("auto_update") or not self.root or self.updating:
            return
        if time.time() - float(settings.get("update_last_check") or 0) < 24 * 3600:
            return
        self.check_updates(auto=True)

    def check_updates(self, auto=False, done=None):
        from . import updater

        def ok(items):
            settings.set("update_last_check", time.time())
            skip = settings.get("update_skip") or {}
            avail = [i for i in items if i.get("available") and not (auto and skip.get(i["comp"]) == i.get("version"))]
            if done:
                done(items)
            if auto and avail:
                self.updates_found.emit(avail)

        def bad(e):
            if done:
                done([{"comp": "error", "error": e}])
        run_async(updater.check, self.root, self.data, done=ok, fail=bad)

    def apply_updates(self, items):
        from . import updater
        if self.updating:
            return
        app = next((i for i in items if i.get("comp") == "app"), None)
        if app:
            # новая версия программы: установщик и так содержит свежий движок
            self.updating = True
            self.state_changed.emit()

            def work():
                return str(updater.download_app(app, self.data, progress=lambda t, f: self.update_progress.emit(t, f)))

            def done(path):
                self.updating = False
                self.update_done.emit(True, tr("Устанавливаю новую версию…"))
                self.app_update_ready.emit(path)

            def fail(e):
                self.updating = False
                self.update_done.emit(False, f"{tr('Не удалось скачать обновление')}: {e}")
                self.state_changed.emit()
            run_async(work, done=done, fail=fail)
            return
        if not self.runner:
            return
        self.updating = True
        prev = self.active()
        self.state_changed.emit()

        def work():
            self.runner.stop(full=False)
            bdir = updater.apply(items, self.root, self.data,
                                 progress=lambda t, f: self.update_progress.emit(t, f))
            msg = "OK"
            if prev:
                ok, m = self.runner.start(prev)
                if not ok and bdir:
                    updater.rollback(bdir, self.root)
                    self.runner.start(prev)
                    return False, tr("Новая версия не запустилась с пресетом — выполнен откат") + f"\n{m[:300]}"
            return True, msg if bdir else tr("Всё уже актуально")

        def done(r):
            self.updating = False
            ok, msg = r
            self.update_done.emit(ok, msg)
            self.state_changed.emit()

        def fail(e):
            self.updating = False
            if prev and not self.runner.alive():
                run_async(self.runner.start, prev, done=lambda r: self.state_changed.emit())
            self.update_done.emit(False, e)
            self.state_changed.emit()
        run_async(work, done=done, fail=fail)

    def rollback_update(self):
        from . import updater
        b = updater.last_backup(self.data)
        if not b or self.updating:
            return False
        prev = self.active()

        def work():
            self.runner.stop(full=False)
            updater.rollback(b, self.root)
            if prev:
                self.runner.start(prev)
            return True
        self.updating = True
        run_async(work, done=lambda r: (setattr(self, "updating", False), self.update_done.emit(True, tr("Откат выполнен")),
                                        self.state_changed.emit()),
                  fail=lambda e: (setattr(self, "updating", False), self.update_done.emit(False, e)))
        return True

    def stop_conflicts_and_activate(self, preset, items):
        from . import conflicts

        def work():
            errs = conflicts.stop([i for i in items if i["blocking"]])
            time.sleep(0.8)
            return errs

        def done(errs):
            if errs:
                self.toast.emit("; ".join(errs)[:300], "error")
            self.activate(preset, skip_conflicts=True)
        run_async(work, done=done)

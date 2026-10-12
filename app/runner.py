"""Запуск и остановка winws / winws2."""
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from .presets import Preset, ENGINE_EXE, write_at_config, build_argv, cygwin_cmdline
from .winutil import CREATE_NO_WINDOW, IS_WIN, run

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

PROC_NAMES = ("winws.exe", "winws2.exe")
DRIVER_SERVICES = ("Monkey", "WinDivert", "WinDivert14")


def find_winws() -> list[tuple[str, int]]:
    res = []
    if psutil:
        for p in psutil.process_iter(["name", "pid"]):
            n = (p.info.get("name") or "").lower()
            if n in PROC_NAMES:
                res.append((n, p.info["pid"]))
        return res
    if IS_WIN:
        code, out = run(["tasklist", "/FO", "CSV", "/NH"], timeout=15)
        for line in out.splitlines():
            parts = [x.strip('"') for x in line.split('","')]
            if parts and parts[0].lower() in PROC_NAMES:
                try:
                    res.append((parts[0].lower(), int(parts[1])))
                except (IndexError, ValueError):
                    pass
    return res


class Runner:
    def __init__(self, root: Path, data: Path, sites=None):
        self.root = root
        self.sites = sites
        self.data = data
        self.proc: subprocess.Popen | None = None
        self.preset: Preset | None = None
        self.started_at: float | None = None
        self.output: list[str] = []
        self.lock = threading.RLock()
        self.log_path = data / "logs" / "winws.log"
        self.extra_used = []
        self.extra_args = None      # () -> list[str], например --wf-iface при VPN в режиме TUN

    # ---- состояние ----
    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def uptime(self) -> int:
        return int(time.time() - self.started_at) if self.alive() and self.started_at else 0

    def _reader(self, proc):
        try:
            with open(self.log_path, "a", encoding="utf-8", errors="replace") as log:
                for raw in iter(proc.stdout.readline, b""):
                    line = raw.decode("utf-8", errors="replace").rstrip()
                    self.output.append(line)
                    del self.output[:-300]
                    log.write(line + "\n")
                    log.flush()
        except Exception:
            pass

    # ---- запуск ----
    def start(self, preset: Preset, wait: float = 1.5) -> tuple[bool, str]:
        with self.lock:
            self.stop(full=False)
            exe = self.root / "exe" / ENGINE_EXE[preset.engine]
            if not exe.exists():
                return False, f"Не найден {exe}"
            argv = build_argv(preset.read())
            if self.sites is not None:
                try:
                    argv = self.sites.apply(preset.id, argv, self.root)
                except Exception as e:  # noqa
                    self.output.append(f"sites: {e}")
            self.extra_used = []
            if self.extra_args:
                try:
                    self.extra_used = list(self.extra_args())
                    argv = self.extra_used + argv
                except Exception:  # noqa
                    pass
            try:
                # копия конфига для отладки (и запасной вариант для очень длинных пресетов)
                cfg = write_at_config(argv, preset.engine, self.data / "tmp")
            except OSError as e:
                return False, str(e)
            # Аргументы передаём напрямую: @file в winws разбирается через wordexp(),
            # который в cygwin делает fork и на части систем падает
            # ("child_copy: cygheap read copy failed ... failed to split command line options").
            cmd = '"' + str(exe) + '" ' + cygwin_cmdline(argv)
            if len(cmd) > 32000:
                cmd = '"' + str(exe) + '" "@' + str(cfg) + '"'
            try:
                (self.data / "tmp" / f"cmdline_{preset.engine}.txt").write_text(cmd, "utf-8")
            except OSError:
                pass
            self.output = []
            with open(self.log_path, "a", encoding="utf-8") as log:
                log.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} {preset.engine}: {preset.name} =====\n")
            try:
                self.proc = subprocess.Popen(
                    cmd, cwd=str(self.root),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW)
            except OSError as e:
                self.proc = None
                return False, str(e)
            threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()
            self.preset = preset
            self.started_at = time.time()
            t0 = time.time()
            while time.time() - t0 < wait:
                if self.proc.poll() is not None:
                    break
                time.sleep(0.1)
            if self.proc.poll() is not None:
                time.sleep(0.2)
                tail = "\n".join(self.output[-8:]) or f"код выхода {self.proc.returncode}"
                self.proc = None
                self.preset = None
                return False, tail
            return True, "OK"

    # ---- остановка ----
    def stop(self, full: bool = False):
        with self.lock:
            if self.proc is not None:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=3)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
            self.proc = None
            self.preset = None
            self.started_at = None
            if find_winws():
                if IS_WIN:
                    run(["taskkill", "/F", "/T", "/IM", "winws.exe", "/IM", "winws2.exe"], timeout=15)
                elif psutil:
                    for _, pid in find_winws():
                        try:
                            psutil.Process(pid).kill()
                        except Exception:
                            pass
            if full and IS_WIN:
                for svc in DRIVER_SERVICES:
                    run(["sc", "stop", svc], timeout=10)
                    run(["sc", "delete", svc], timeout=10)

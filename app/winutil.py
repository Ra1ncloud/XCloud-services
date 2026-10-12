"""Windows-специфичные функции: права администратора, запуск команд, размытие окна, автозапуск."""
import ctypes
import os
import subprocess
import sys
from pathlib import Path

IS_WIN = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0
TASK_NAME = "ZapretCloud"
OLD_TASK_NAMES = ("ZapretStudio",)


def is_admin() -> bool:
    if not IS_WIN:
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def launch_command(extra_args=None) -> tuple[str, list[str]]:
    """Команда для повторного запуска самой программы."""
    extra_args = list(extra_args or [])
    if getattr(sys, "frozen", False):
        return sys.executable, extra_args
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        w = exe[:-10] + "pythonw.exe"
        if os.path.exists(w):
            exe = w
    main = str(Path(__file__).resolve().parent.parent / "main.py")
    return exe, [main] + extra_args


def relaunch_as_admin(extra_args=None) -> bool:
    exe, args = launch_command(extra_args if extra_args is not None else sys.argv[1:])
    params = subprocess.list2cmdline(args)
    r = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return r > 32


def run(cmd, timeout=60, cwd=None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd,
                           creationflags=CREATE_NO_WINDOW)
        out = p.stdout + p.stderr
        enc = "oem" if IS_WIN else "utf-8"
        try:
            text = out.decode(enc, errors="replace")
        except LookupError:
            text = out.decode("utf-8", errors="replace")
        return p.returncode, text
    except Exception as e:  # noqa
        return -1, str(e)


def powershell(script: str, timeout=60) -> tuple[int, str]:
    pre = "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;$ErrorActionPreference='Stop';"
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                            "-Command", pre + script],
                           capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW)
        return p.returncode, (p.stdout + p.stderr).decode("utf-8", errors="replace")
    except Exception as e:  # noqa
        return -1, str(e)


def open_path(path):
    path = str(path)
    if IS_WIN:
        os.startfile(path)  # noqa
    else:
        subprocess.Popen(["xdg-open", path])


def windows_build() -> int:
    if not IS_WIN:
        return 0
    try:
        return sys.getwindowsversion().build
    except Exception:
        return 0


# ---------- Эффекты окна ----------
class _ACCENT(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]


class _WCAD(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.POINTER(_ACCENT)),
                ("SizeOfData", ctypes.c_size_t)]


def set_window_effect(hwnd: int, effect: str, tint_rgb=(20, 20, 28), alpha=0x99) -> bool:
    """effect: acrylic | blur | none"""
    if not IS_WIN:
        return False
    try:
        state = {"acrylic": 4, "blur": 3}.get(effect, 0)
        r, g, b = tint_rgb
        color = (alpha << 24) | (b << 16) | (g << 8) | r
        accent = _ACCENT(state, 2 if state == 4 else 0, color, 0)
        data = _WCAD(19, ctypes.pointer(accent), ctypes.sizeof(accent))
        ctypes.windll.user32.SetWindowCompositionAttribute(ctypes.c_void_p(hwnd), ctypes.byref(data))
        # скругление углов в Windows 11
        pref = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 33, ctypes.byref(pref), 4)
        return True
    except Exception:
        return False


# ---------- Автозапуск через планировщик (с правами администратора, без окна UAC) ----------
def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def set_autostart(enabled: bool) -> tuple[bool, str]:
    if not IS_WIN:
        return False, "Windows only"
    if not enabled:
        code, out = powershell(f"Unregister-ScheduledTask -TaskName {_ps_quote(TASK_NAME)} -Confirm:$false")
        return code == 0 or "No MSFT_ScheduledTask" in out, out
    for old in OLD_TASK_NAMES:
        powershell(f"Unregister-ScheduledTask -TaskName {_ps_quote(old)} -Confirm:$false", timeout=20)
    exe, args = launch_command(["--autostart"])
    workdir = str(Path(exe).parent if getattr(sys, "frozen", False) else Path(args[0]).parent)
    arg_line = subprocess.list2cmdline(args)
    script = (
        f"$a=New-ScheduledTaskAction -Execute {_ps_quote(exe)} -Argument {_ps_quote(arg_line)} "
        f"-WorkingDirectory {_ps_quote(workdir)};"
        "$t=New-ScheduledTaskTrigger -AtLogOn -User \"$env:USERDOMAIN\\$env:USERNAME\";"
        "$p=New-ScheduledTaskPrincipal -UserId \"$env:USERDOMAIN\\$env:USERNAME\" -LogonType Interactive -RunLevel Highest;"
        "$s=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew;"
        f"Register-ScheduledTask -TaskName {_ps_quote(TASK_NAME)} -Action $a -Trigger $t -Principal $p "
        "-Settings $s -Force | Out-Null; 'OK'"
    )
    code, out = powershell(script)
    return code == 0 and "OK" in out, out


def autostart_enabled() -> bool:
    if not IS_WIN:
        return False
    code, out = run(["schtasks", "/Query", "/TN", TASK_NAME], timeout=15)
    return code == 0

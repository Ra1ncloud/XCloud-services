"""Сторож: раз в N минут лёгкая проверка нескольких сервисов при активном пресете.
Ничего не переключает сам — только сообщает о проблеме и предлагает пресет."""
import time

from .tester import DEFAULT_TARGETS, Target, run_checks

PICK = {"youtube": "yt_web", "discord": "ds_web", "telegram": "tg_web", "games": "gm_steam", "ai": "ai_gpt"}
CONTROL = [Target("ctl_ya", "ya.ru", "control", "https", "ya.ru"),
           Target("ctl_vk", "vk.com", "control", "https", "vk.com")]


def targets_for(categories) -> list[Target]:
    by_id = {t.id: t for t in DEFAULT_TARGETS}
    return [by_id[PICK[c]] for c in categories if c in PICK and PICK[c] in by_id]


class Watchdog:
    def __init__(self):
        self.reset()

    def reset(self, preset_id=None):
        self.preset_id = preset_id
        self.baseline: set[str] | None = None   # что работало после запуска
        self.fail_streak: dict[str, int] = {}
        self.last = None                        # {"time", "ok", "total", "ms", "failed": [...]}
        self.snooze_until = 0.0
        self.alerted: frozenset = frozenset()

    def run(self, categories, timeout=5.0) -> dict:
        """Выполняется в фоне. Возвращает {"status": ok|alert|offline|skip, ...}."""
        ts = targets_for(categories)
        if not ts:
            return {"status": "skip"}
        res = run_checks(ts + CONTROL, timeout=timeout, workers=len(ts) + len(CONTROL))
        ok_ids = {t.id for t in ts if res[t.id].ok}
        ms = [res[t.id].ms for t in ts if res[t.id].ok]
        self.last = {"time": time.time(), "ok": len(ok_ids), "total": len(ts),
                     "ms": int(sum(ms) / len(ms)) if ms else 0,
                     "failed": [t.name for t in ts if t.id not in ok_ids]}
        if not any(res[c.id].ok for c in CONTROL):
            self.last["offline"] = True
            return {"status": "offline"}
        if self.baseline is None:
            self.baseline = ok_ids
            if not ok_ids:
                return self._alert(ts, [t.id for t in ts], first=True)
            return {"status": "ok"}
        for t in ts:
            self.fail_streak[t.id] = 0 if t.id in ok_ids else self.fail_streak.get(t.id, 0) + 1
        broken = [tid for tid in self.baseline if self.fail_streak.get(tid, 0) >= 2]
        if broken:
            return self._alert(ts, broken)
        self.alerted = frozenset()
        return {"status": "ok"}

    def _alert(self, ts, ids, first=False):
        key = frozenset(ids)
        if time.time() < self.snooze_until or key == self.alerted:
            return {"status": "ok"}
        self.alerted = key
        names = [t.name for t in ts if t.id in ids]
        return {"status": "alert", "failed": names, "first": first}

    def snooze(self, minutes=60):
        self.snooze_until = time.time() + minutes * 60

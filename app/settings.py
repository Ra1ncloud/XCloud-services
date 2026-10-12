import json
from .paths import data_dir

DEFAULTS = {
    "language": "ru",
    "theme": "dark",
    "accent": "#7C5CFF",
    "effect": "acrylic",       # acrylic | blur | none
    "opacity": 0.80,
    "tray": True,
    "close_to_tray": True,
    "autostart": False,
    "start_last": True,
    "last_preset": None,
    "favorites": [],
    "root": None,
    "custom_targets": [],
    "autotune_categories": ["youtube", "discord", "telegram", "games", "ai"],
    "autotune_scope": "all",
    "autotune_timeout": 5,
    "autotune_warmup": 2.5,
    "autotune_stop_on_perfect": False,
    "dns_doh": False,
    "full_stop": True,
    "show_system_files": False,
    "watchdog": True,
    "watchdog_interval": 5,      # минут
    "mini_widget": False,
    "mini_pos": None,
    "auto_update": True,
    "update_last_check": 0,
    "update_skip": {},           # {comp: version} — «пропустить эту версию»
    "wizard_done": False,
    "vpn_mode": "tun",           # tun | proxy
    "vpn_route": "smart",        # smart | list | all
    "vpn_learn": True,           # умный режим: сам переводить на VPN сайты, которые не открываются
    "vpn_ru_direct": True,
    "vpn_autostart": False,
    "vpn_was_on": False,
    "vpn_lan": False,
    "vpn_port": 10808,
    "vpn_proxy_backup": None,
}


class Settings:
    def __init__(self):
        self.path = data_dir() / "settings.json"
        self.data = dict(DEFAULTS)
        try:
            self.data.update(json.loads(self.path.read_text("utf-8")))
        except Exception:
            pass

    def get(self, k, default=None):
        return self.data.get(k, DEFAULTS.get(k, default))

    def set(self, k, v):
        self.data[k] = v
        self.save()

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.path)


settings = Settings()

"""
settings_service.py — Notification settings schema, persistence, and defaults.

Settings are stored in a user-friendly JSON file in the OS-appropriate config
directory so they survive app updates and are easy to find or back up.
"""

import json
import os
import sys
import copy

SCHEMA_VERSION = 1

DEFAULTS = {
    "schema_version": SCHEMA_VERSION,
    "alert_motion": True,
    "alert_person": True,
    "alert_vehicle": False,
    "alert_sound": True,
    "debounce_seconds": 30,
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "poll_interval_seconds": 15,
    # first_run is used for the welcome dialog; reset to False after first launch
    "first_run": True,
    # Future: "start_on_login": False, "minimise_to_tray": False
}


def _config_dir() -> str:
    """Return an OS-appropriate writable config directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(base, "TapoDesktopClient")
    elif sys.platform == "darwin":
        path = os.path.expanduser("~/Library/Application Support/TapoDesktopClient")
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        path = os.path.join(xdg, "TapoDesktopClient")
    os.makedirs(path, exist_ok=True)
    return path


def _settings_path() -> str:
    return os.path.join(_config_dir(), "notifications_config.json")


def load_settings() -> dict:
    """Load settings from disk, merging missing keys with defaults."""
    path = _settings_path()
    settings = copy.deepcopy(DEFAULTS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            settings = _migrate(settings, data)
        except (json.JSONDecodeError, OSError):
            pass  # corrupt or unreadable — use defaults
    return settings


def save_settings(settings: dict) -> None:
    """Persist settings to disk atomically."""
    path = _settings_path()
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
        os.replace(tmp_path, path)
    except OSError:
        pass  # non-fatal — in-memory settings still work


def reset_to_defaults() -> dict:
    """Overwrite saved settings with built-in defaults and return them."""
    settings = copy.deepcopy(DEFAULTS)
    save_settings(settings)
    return settings


def _migrate(base: dict, loaded: dict) -> dict:
    """Apply loaded values onto defaults, filling gaps from schema upgrades."""
    merged = copy.deepcopy(base)
    for key, value in loaded.items():
        if key in merged:
            merged[key] = value
    merged["schema_version"] = SCHEMA_VERSION
    return merged


def get_config_dir() -> str:
    """Expose the config directory path for display in the UI."""
    return _config_dir()

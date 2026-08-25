"""
Unit tests for SettingsService.

Uses a temporary directory so tests never touch the real config.
"""

import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import settings_service as svc


def _patch_config_dir(tmp_dir):
    """Context manager that redirects _config_dir to a temp directory."""
    return patch.object(svc, "_config_dir", return_value=tmp_dir)


class TestDefaults(unittest.TestCase):

    def test_all_default_keys_present(self):
        settings = copy.deepcopy(svc.DEFAULTS)
        required = [
            "schema_version", "alert_motion", "alert_person", "alert_vehicle",
            "alert_sound", "debounce_seconds", "quiet_hours_enabled",
            "quiet_hours_start", "quiet_hours_end", "poll_interval_seconds",
            "first_run",
        ]
        for key in required:
            self.assertIn(key, settings, f"Missing default key: {key}")
        # These are future-work features, not yet in DEFAULTS
        for key in ("start_on_login", "minimise_to_tray"):
            self.assertNotIn(key, settings, f"Unimplemented key should not be in DEFAULTS: {key}")

    def test_default_alert_motion_is_true(self):
        self.assertTrue(svc.DEFAULTS["alert_motion"])

    def test_default_alert_person_is_true(self):
        self.assertTrue(svc.DEFAULTS["alert_person"])

    def test_default_alert_vehicle_is_false(self):
        self.assertFalse(svc.DEFAULTS["alert_vehicle"])

    def test_default_debounce_is_30(self):
        self.assertEqual(svc.DEFAULTS["debounce_seconds"], 30)

    def test_default_sound_is_on(self):
        self.assertTrue(svc.DEFAULTS["alert_sound"])


class TestLoadSave(unittest.TestCase):

    def test_load_returns_defaults_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _patch_config_dir(tmp):
                settings = svc.load_settings()
        for key, val in svc.DEFAULTS.items():
            self.assertEqual(settings[key], val, f"Default mismatch for {key}")

    def test_save_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _patch_config_dir(tmp):
                original = svc.load_settings()
                original["debounce_seconds"] = 60
                original["alert_sound"] = False
                svc.save_settings(original)
                loaded = svc.load_settings()
        self.assertEqual(loaded["debounce_seconds"], 60)
        self.assertFalse(loaded["alert_sound"])

    def test_load_handles_corrupt_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "notifications_config.json")
            with open(path, "w") as fh:
                fh.write("{invalid json{{")
            with _patch_config_dir(tmp):
                settings = svc.load_settings()
        # Should fall back to defaults without raising
        self.assertEqual(settings["debounce_seconds"], svc.DEFAULTS["debounce_seconds"])

    def test_load_merges_missing_keys(self):
        """Loading a file that's missing new keys fills them from defaults."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "notifications_config.json")
            partial = {"alert_motion": False, "debounce_seconds": 10}
            with open(path, "w") as fh:
                json.dump(partial, fh)
            with _patch_config_dir(tmp):
                settings = svc.load_settings()
        self.assertFalse(settings["alert_motion"])
        self.assertEqual(settings["debounce_seconds"], 10)
        # Key that wasn't in file should come from defaults
        self.assertIn("poll_interval_seconds", settings)


class TestResetToDefaults(unittest.TestCase):

    def test_reset_overwrites_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _patch_config_dir(tmp):
                s = svc.load_settings()
                s["debounce_seconds"] = 999
                svc.save_settings(s)
                reset = svc.reset_to_defaults()
                loaded_after = svc.load_settings()
        self.assertEqual(reset["debounce_seconds"], svc.DEFAULTS["debounce_seconds"])
        self.assertEqual(loaded_after["debounce_seconds"], svc.DEFAULTS["debounce_seconds"])


class TestMigration(unittest.TestCase):

    def test_migration_preserves_known_keys(self):
        base = copy.deepcopy(svc.DEFAULTS)
        loaded = {"alert_motion": False, "debounce_seconds": 45, "unknown_key": "ignored"}
        merged = svc._migrate(base, loaded)
        self.assertFalse(merged["alert_motion"])
        self.assertEqual(merged["debounce_seconds"], 45)
        # Unknown keys from old file are not carried forward
        self.assertNotIn("unknown_key", merged)

    def test_schema_version_always_updated(self):
        base = copy.deepcopy(svc.DEFAULTS)
        loaded = {"schema_version": 0}
        merged = svc._migrate(base, loaded)
        self.assertEqual(merged["schema_version"], svc.SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()

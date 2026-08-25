"""
Unit tests for NotificationService.

Runs without a real camera, display, or sound hardware.
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from notification_service import NotificationService, EVENT_LABELS


def _base_settings(**overrides):
    s = {
        "alert_motion": True,
        "alert_person": True,
        "alert_vehicle": False,
        "alert_sound": False,   # silence sound in tests
        "debounce_seconds": 30,
        "quiet_hours_enabled": False,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00",
    }
    s.update(overrides)
    return s


class TestNotificationServiceDispatch(unittest.TestCase):

    def setUp(self):
        self.svc = NotificationService(_base_settings())
        # Patch internal _dispatch so no real OS notification fires
        self._dispatch_calls = []
        self.svc._dispatch = lambda msg, snd: self._dispatch_calls.append((msg, snd))

    def test_motion_alert_fires_when_enabled(self):
        result = self.svc.notify("Front Door", "dev1", "motion")
        self.assertTrue(result)
        # Allow background thread to run
        time.sleep(0.1)
        self.assertEqual(len(self._dispatch_calls), 1)

    def test_vehicle_alert_suppressed_when_disabled(self):
        result = self.svc.notify("Front Door", "dev1", "vehicle")
        self.assertFalse(result)
        time.sleep(0.1)
        self.assertEqual(len(self._dispatch_calls), 0)

    def test_notification_message_format(self):
        self.svc.notify("Driveway Cam", "dev2", "person")
        time.sleep(0.1)
        self.assertEqual(len(self._dispatch_calls), 1)
        msg = self._dispatch_calls[0][0]
        self.assertIn("Driveway Cam", msg)
        self.assertIn("Person Detected", msg)
        # Timestamp pattern HH:MM
        import re
        self.assertRegex(msg, r"\d{2}:\d{2}")

    def test_vehicle_enabled_after_settings_update(self):
        self.svc.update_settings(_base_settings(alert_vehicle=True))
        result = self.svc.notify("Back Yard", "dev3", "vehicle")
        self.assertTrue(result)


class TestDebounce(unittest.TestCase):

    def setUp(self):
        self.svc = NotificationService(_base_settings(debounce_seconds=5))
        self._dispatch_calls = []
        self.svc._dispatch = lambda msg, snd: self._dispatch_calls.append((msg, snd))

    def test_second_alert_same_camera_event_suppressed(self):
        self.svc.notify("Cam", "dev1", "motion")
        self.svc.notify("Cam", "dev1", "motion")
        time.sleep(0.1)
        self.assertEqual(len(self._dispatch_calls), 1)

    def test_different_event_types_not_suppressed(self):
        self.svc.update_settings(_base_settings(debounce_seconds=5, alert_vehicle=True))
        self.svc.notify("Cam", "dev1", "motion")
        self.svc.notify("Cam", "dev1", "person")
        time.sleep(0.1)
        self.assertEqual(len(self._dispatch_calls), 2)

    def test_different_cameras_not_suppressed(self):
        self.svc.notify("Cam A", "dev1", "motion")
        self.svc.notify("Cam B", "dev2", "motion")
        time.sleep(0.1)
        self.assertEqual(len(self._dispatch_calls), 2)

    def test_debounce_zero_allows_every_alert(self):
        self.svc.update_settings(_base_settings(debounce_seconds=0))
        self.svc.notify("Cam", "dev1", "motion")
        self.svc.notify("Cam", "dev1", "motion")
        time.sleep(0.1)
        self.assertEqual(len(self._dispatch_calls), 2)


class TestQuietHours(unittest.TestCase):

    def setUp(self):
        self.svc = NotificationService(_base_settings())
        self._dispatch_calls = []
        self.svc._dispatch = lambda msg, snd: self._dispatch_calls.append((msg, snd))

    def _patch_now(self, hour, minute):
        from unittest.mock import patch
        from datetime import datetime, time as dtime
        fake_now = datetime(2025, 1, 1, hour, minute, 0)
        return patch("notification_service.datetime", wraps=datetime,
                     **{"now.return_value": fake_now})

    def test_quiet_hours_suppress_notification(self):
        self.svc.update_settings(_base_settings(
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        ))
        # Simulate 23:30 (inside quiet hours)
        with self._patch_now(23, 30):
            result = self.svc.notify("Cam", "dev1", "motion")
        self.assertFalse(result)

    def test_outside_quiet_hours_allows_notification(self):
        self.svc.update_settings(_base_settings(
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        ))
        # Simulate 12:00 (outside quiet hours)
        with self._patch_now(12, 0):
            result = self.svc.notify("Cam", "dev1", "motion")
        self.assertTrue(result)

    def test_quiet_hours_disabled_allows_notification(self):
        self.svc.update_settings(_base_settings(quiet_hours_enabled=False))
        result = self.svc.notify("Cam", "dev1", "motion")
        self.assertTrue(result)


class TestTestNotification(unittest.TestCase):

    def test_test_notification_always_fires(self):
        svc = NotificationService(_base_settings(
            alert_motion=False,
            alert_person=False,
            alert_vehicle=False,
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
        ))
        calls = []
        svc._dispatch = lambda msg, snd: calls.append(msg)
        svc.test_notification("Test Camera")
        time.sleep(0.1)
        self.assertEqual(len(calls), 1)
        self.assertIn("Test Camera", calls[0])


if __name__ == "__main__":
    unittest.main()

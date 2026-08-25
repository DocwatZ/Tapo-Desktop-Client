"""
Unit tests for EventAdapter and helpers.

All network calls are mocked — no real camera or internet required.
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from event_adapter import EventAdapter, _parse_ts, _fetch_events


class TestParseTsHelper(unittest.TestCase):

    def test_integer_passthrough(self):
        self.assertEqual(_parse_ts(1700000000), 1700000000)

    def test_string_integer(self):
        self.assertEqual(_parse_ts("1700000000"), 1700000000)

    def test_none_returns_zero(self):
        self.assertEqual(_parse_ts(None), 0)

    def test_unknown_string_returns_zero(self):
        self.assertEqual(_parse_ts("not-a-timestamp"), 0)

    def test_iso_string(self):
        # 2024-01-15T10:30:00Z → should return a positive epoch
        result = _parse_ts("2024-01-15T10:30:00Z")
        self.assertGreater(result, 0)

    def test_float_cast(self):
        self.assertEqual(_parse_ts(1700000000.9), 1700000000)


class TestFetchEvents(unittest.TestCase):

    def _make_response(self, motion_ts=None, person_ts=None, vehicle_ts=None):
        """Build a fake Tapo API response for _fetch_events."""
        responses = [
            {
                "method": "getMotionDetection",
                "error_code": 0,
                "result": {
                    "motion_detection": {
                        "motion_det": {
                            "enabled": "on",
                            "last_trigger_time": motion_ts,
                        }
                    }
                },
            },
            {
                "method": "getDetectionConfig",
                "error_code": 0,
                "result": {
                    "detection": {
                        "person_detection": {"last_trigger_time": person_ts},
                        "vehicle_detection": {"last_trigger_time": vehicle_ts},
                    }
                },
            },
        ]
        return {
            "outputParams": {
                "responseData": {
                    "result": {"responses": responses}
                }
            }
        }

    def test_parses_motion_timestamp(self):
        fake_data = self._make_response(motion_ts=1700000100)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = fake_data
        with patch("event_adapter.requests.post", return_value=mock_resp):
            result = _fetch_events("dev1", {})
        self.assertIn("motion", result)
        self.assertEqual(result["motion"], 1700000100)

    def test_parses_person_timestamp(self):
        fake_data = self._make_response(person_ts=1700000200)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = fake_data
        with patch("event_adapter.requests.post", return_value=mock_resp):
            result = _fetch_events("dev1", {})
        self.assertIn("person", result)
        self.assertEqual(result["person"], 1700000200)

    def test_missing_timestamp_not_included(self):
        fake_data = self._make_response(motion_ts=None)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = fake_data
        with patch("event_adapter.requests.post", return_value=mock_resp):
            result = _fetch_events("dev1", {})
        self.assertNotIn("motion", result)


class TestEventAdapterCallbacks(unittest.TestCase):

    def _headers(self):
        return {"Authorization": "******"}

    def test_on_event_called_when_new_trigger(self):
        """Adapter fires on_event when last_trigger_time increases."""
        events_seen = []

        def on_event(device_id, cam_name, event_type):
            events_seen.append((device_id, cam_name, event_type))

        call_count = [0]

        def fake_fetch(device_id, headers):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"motion": 1000}   # seed (should NOT fire)
            return {"motion": 2000}       # new trigger (should fire)

        adapter = EventAdapter(
            get_headers_fn=self._headers,
            on_event=on_event,
        )
        adapter.update_settings({"poll_interval_seconds": 0})

        with patch("event_adapter._fetch_events", side_effect=fake_fetch):
            adapter.start([{"device_id": "dev1", "name": "Front Cam"}],
                          settings={"poll_interval_seconds": 0})
            time.sleep(0.3)
            adapter.stop()

        self.assertGreater(len(events_seen), 0)
        self.assertEqual(events_seen[0], ("dev1", "Front Cam", "motion"))

    def test_no_event_when_timestamp_unchanged(self):
        events_seen = []

        def on_event(*args):
            events_seen.append(args)

        def fake_fetch(device_id, headers):
            return {"motion": 1000}  # never changes

        adapter = EventAdapter(get_headers_fn=self._headers, on_event=on_event)
        with patch("event_adapter._fetch_events", side_effect=fake_fetch):
            adapter.start([{"device_id": "dev1", "name": "Cam"}],
                          settings={"poll_interval_seconds": 0})
            time.sleep(0.3)
            adapter.stop()

        self.assertEqual(len(events_seen), 0)

    def test_status_connected_on_success(self):
        statuses = []

        def on_status(s):
            statuses.append(s)

        def fake_fetch(device_id, headers):
            return {}

        adapter = EventAdapter(
            get_headers_fn=self._headers,
            on_status_change=on_status,
        )
        with patch("event_adapter._fetch_events", side_effect=fake_fetch):
            adapter.start([{"device_id": "dev1", "name": "Cam"}],
                          settings={"poll_interval_seconds": 0})
            time.sleep(0.2)
            adapter.stop()

        self.assertIn("connected", statuses)

    def test_status_disconnected_when_no_headers(self):
        statuses = []

        def on_status(s):
            statuses.append(s)

        adapter = EventAdapter(
            get_headers_fn=lambda: None,
            on_status_change=on_status,
        )
        adapter.start([{"device_id": "dev1", "name": "Cam"}],
                      settings={"poll_interval_seconds": 0})
        time.sleep(0.2)
        adapter.stop()

        self.assertIn("disconnected", statuses)

    def test_stop_joins_threads(self):
        adapter = EventAdapter(get_headers_fn=lambda: None)
        adapter.start([{"device_id": "dev1", "name": "Cam"}],
                      settings={"poll_interval_seconds": 60})
        adapter.stop()
        self.assertEqual(len(adapter._threads), 0)


if __name__ == "__main__":
    unittest.main()

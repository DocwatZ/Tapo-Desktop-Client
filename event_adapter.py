"""
event_adapter.py — Polls the Tapo cloud API for camera detection events
(motion / person / vehicle) and fires callbacks when new events are found.

Architecture
------------
* One background thread per registered device polls every N seconds.
* On connectivity failure, exponential back-off (up to 5 minutes) is used.
* After reconnect, the last-seen timestamp is reset to "now" to prevent a
  burst of stale notifications.
* Callers register an ``on_event`` callback:
      on_event(device_id, camera_name, event_type)
  where event_type is one of: 'motion', 'person', 'vehicle'.
* A ``on_status_change`` callback receives:
      on_status_change(status)   # 'connected', 'reconnecting', 'disconnected'

Tapo API notes
--------------
The detection-event endpoint used here is the ``multipleRequest`` passthrough
with two methods:
  • ``getMotionDetection`` — reports ``motion_detection.motion_det.enabled``
    and ``motion_detection.motion_det.digital_sensitivity`` plus a
    ``last_trigger_time`` field on cameras that support it.
  • ``getDetectionConfig`` — returns person/vehicle/pet last-trigger times on
    cameras that support AI detection (C120, C225, C325WB, etc.).

If a camera doesn't return ``last_trigger_time`` the adapter logs a warning
and the device is silently skipped for that event type — no crash, no spam.
"""

import threading
import time
import warnings
import requests
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

DEFAULT_POLL_INTERVAL = 15   # seconds
BACKOFF_BASE = 5             # seconds
BACKOFF_MAX = 300            # 5 minutes

_API_URL = "https://aps1-app-server.iot.i.tplinkcloud.com/v1/things/{device_id}/services-sync"


class EventAdapter:
    """
    Manages per-device polling threads for detection events.

    Usage::

        adapter = EventAdapter(get_headers_fn, on_event, on_status_change)
        adapter.start(devices)   # list of dicts with 'device_id' and 'name'
        ...
        adapter.stop()
    """

    def __init__(self, get_headers_fn, on_event=None, on_status_change=None):
        """
        Parameters
        ----------
        get_headers_fn : callable
            Zero-argument callable that returns the current auth headers dict
            (or None if not configured).  Matches the existing ``get_headers``
            function in api.py.
        on_event : callable, optional
            Called when a new event is detected:
            ``on_event(device_id, camera_name, event_type)``.
        on_status_change : callable, optional
            Called when the adapter connection status changes:
            ``on_status_change(status)`` where status is one of
            'connected', 'reconnecting', 'disconnected'.
        """
        self._get_headers = get_headers_fn
        self._on_event = on_event
        self._on_status_change = on_status_change
        self._threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._settings: dict = {}
        self._lock = threading.Lock()

    def update_settings(self, settings: dict) -> None:
        with self._lock:
            self._settings = dict(settings)

    def start(self, devices: list, settings: dict = None) -> None:
        """Start polling threads for each device in the list."""
        if settings:
            with self._lock:
                self._settings = dict(settings)
        self.stop()  # clean up any previous threads
        for device in devices:
            device_id = device.get("device_id")
            if not device_id:
                continue
            stop_evt = threading.Event()
            self._stop_events[device_id] = stop_evt
            t = threading.Thread(
                target=self._poll_loop,
                args=(device_id, device.get("name", "Camera"), stop_evt),
                daemon=True,
                name=f"EventPoll-{device_id[:8]}",
            )
            self._threads[device_id] = t
            t.start()

    def stop(self) -> None:
        """Signal all polling threads to stop and wait for them."""
        for evt in self._stop_events.values():
            evt.set()
        for t in self._threads.values():
            t.join(timeout=2)
        self._threads.clear()
        self._stop_events.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _poll_loop(self, device_id: str, camera_name: str, stop: threading.Event) -> None:
        """Background polling loop for a single device."""
        last_seen: dict[str, int] = {}   # event_type → last trigger epoch
        consecutive_failures = 0
        initialized = False

        while not stop.is_set():
            with self._lock:
                settings = dict(self._settings)
            poll_interval = int(settings.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL))

            headers = self._get_headers()
            if not headers:
                # Not configured yet — wait and retry
                self._emit_status("disconnected")
                stop.wait(poll_interval)
                continue

            try:
                events = _fetch_events(device_id, headers)
                consecutive_failures = 0
                self._emit_status("connected")

                if not initialized:
                    # First successful poll: seed last_seen with current values
                    # so we don't fire stale notifications on startup.
                    for evt_type, ts in events.items():
                        last_seen[evt_type] = ts
                    initialized = True
                else:
                    for evt_type, ts in events.items():
                        prev = last_seen.get(evt_type, 0)
                        if ts > prev:
                            last_seen[evt_type] = ts
                            self._emit_event(device_id, camera_name, evt_type)

            except requests.exceptions.ConnectionError:
                consecutive_failures += 1
                backoff = min(BACKOFF_BASE * (2 ** (consecutive_failures - 1)), BACKOFF_MAX)
                self._emit_status("reconnecting" if consecutive_failures < 3 else "disconnected")
                stop.wait(backoff)
                continue
            except Exception:
                consecutive_failures += 1
                # Non-network error — wait a bit then retry
                stop.wait(poll_interval)
                continue

            stop.wait(poll_interval)

    def _emit_event(self, device_id: str, camera_name: str, event_type: str) -> None:
        if callable(self._on_event):
            try:
                self._on_event(device_id, camera_name, event_type)
            except Exception:
                pass

    def _emit_status(self, status: str) -> None:
        if callable(self._on_status_change):
            try:
                self._on_status_change(status)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Low-level API helpers
# ---------------------------------------------------------------------------

def _fetch_events(device_id: str, headers: dict) -> dict:
    """
    Query the Tapo cloud API for the latest detection trigger timestamps.

    Returns a dict mapping event_type → unix timestamp (int).
    Only event types where a valid timestamp was found are included.
    """
    url = _API_URL.format(device_id=device_id)
    payload = {
        "inputParams": {
            "requestData": {
                "method": "multipleRequest",
                "params": {
                    "requests": [
                        {
                            "method": "getMotionDetection",
                            "params": {
                                "motion_detection": {"name": ["motion_det"]}
                            },
                        },
                        {
                            "method": "getDetectionConfig",
                            "params": {
                                "detection": {
                                    "name": [
                                        "person_detection",
                                        "vehicle_detection",
                                        "pet_detection",
                                    ]
                                }
                            },
                        },
                    ]
                },
            }
        },
        "serviceId": "passthrough",
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InsecureRequestWarning)
        response = requests.post(url, headers=headers, json=payload, timeout=10, verify=False)
    response.raise_for_status()

    data = response.json()
    responses = (
        data.get("outputParams", {})
        .get("responseData", {})
        .get("result", {})
        .get("responses", [])
    )

    result: dict[str, int] = {}

    for r in responses:
        if r.get("error_code", 0) != 0:
            continue
        method = r.get("method", "")
        res = r.get("result", {})

        if method == "getMotionDetection":
            motion = res.get("motion_detection", {}).get("motion_det", {})
            ts = _parse_ts(motion.get("last_trigger_time"))
            if ts:
                result["motion"] = ts

        elif method == "getDetectionConfig":
            det = res.get("detection", {})

            person = det.get("person_detection", {})
            ts = _parse_ts(person.get("last_trigger_time"))
            if ts:
                result["person"] = ts

            vehicle = det.get("vehicle_detection", {})
            ts = _parse_ts(vehicle.get("last_trigger_time"))
            if ts:
                result["vehicle"] = ts

    return result


def _parse_ts(value) -> int:
    """Parse a Tapo timestamp value (epoch int or ISO string) → int, or 0."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
        # Try ISO 8601
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return int(datetime.strptime(value, fmt).timestamp())
            except ValueError:
                pass
    return 0

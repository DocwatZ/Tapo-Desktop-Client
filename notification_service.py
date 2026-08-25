"""
notification_service.py — Desktop notification dispatch, optional sound, and
debounce/rate-limiting.

Responsibilities:
  - Send a native desktop pop-up via plyer (cross-platform, Windows-first).
  - Optionally play a brief alert sound (stdlib winsound on Windows, fallback
    on other platforms — no extra dependency).
  - Rate-limit: at most one alert per camera + event type per N seconds
    (default 30 s, configurable).
  - Respect a configurable "quiet hours" window.
"""

import time
import platform
import threading
from datetime import datetime, time as dtime

# --- optional plyer import (graceful degradation) ---
try:
    from plyer import notification as _plyer_notification
    _PLYER_AVAILABLE = True
except ImportError:
    _PLYER_AVAILABLE = False

EVENT_LABELS = {
    "motion": "Motion Detected",
    "person": "Person Detected",
    "vehicle": "Vehicle Detected",
}

APP_TITLE = "Tapo Desktop Client"
APP_ICON = ""  # set at runtime by main.py if needed


class NotificationService:
    """Thread-safe notification dispatcher with debounce and quiet hours."""

    def __init__(self, settings: dict):
        self._settings = settings
        self._last_sent: dict[str, float] = {}  # key: "{device_id}:{event_type}"
        self._lock = threading.Lock()
        self._icon_path: str = ""

    def update_settings(self, settings: dict) -> None:
        """Hot-swap settings without restarting."""
        with self._lock:
            self._settings = settings

    def set_icon_path(self, path: str) -> None:
        self._icon_path = path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notify(self, camera_name: str, device_id: str, event_type: str) -> bool:
        """
        Fire a desktop notification for *event_type* on *camera_name*.

        Returns True if a notification was dispatched, False if suppressed.
        *event_type* must be one of: 'motion', 'person', 'vehicle'.
        """
        with self._lock:
            settings = dict(self._settings)

        # Check alert type is enabled
        if not self._event_enabled(event_type, settings):
            return False

        # Check quiet hours
        if self._in_quiet_hours(settings):
            return False

        # Check debounce
        key = f"{device_id}:{event_type}"
        now = time.monotonic()
        debounce = int(settings.get("debounce_seconds", 30))
        with self._lock:
            last = self._last_sent.get(key, 0.0)
            if now - last < debounce:
                return False
            self._last_sent[key] = now

        # Build message
        timestamp = datetime.now().strftime("%H:%M")
        label = EVENT_LABELS.get(event_type, event_type.title())
        message = f"{camera_name} • {label} • {timestamp}"

        # Dispatch in a background thread so we never block the UI
        threading.Thread(
            target=self._dispatch,
            args=(message, settings.get("alert_sound", True)),
            daemon=True,
        ).start()
        return True

    def test_notification(self, camera_name: str = "Test Camera") -> None:
        """Fire a sample notification regardless of debounce/quiet hours."""
        timestamp = datetime.now().strftime("%H:%M")
        message = f"{camera_name} • Motion Detected • {timestamp}"
        with self._lock:
            settings = dict(self._settings)
        threading.Thread(
            target=self._dispatch,
            args=(message, settings.get("alert_sound", True)),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _event_enabled(self, event_type: str, settings: dict) -> bool:
        map_ = {
            "motion": "alert_motion",
            "person": "alert_person",
            "vehicle": "alert_vehicle",
        }
        key = map_.get(event_type)
        if key is None:
            return True  # unknown type — allow through
        return bool(settings.get(key, True))

    def _in_quiet_hours(self, settings: dict) -> bool:
        if not settings.get("quiet_hours_enabled", False):
            return False
        try:
            now_t = datetime.now().time()
            start_s = settings.get("quiet_hours_start", "22:00")
            end_s = settings.get("quiet_hours_end", "07:00")
            start = dtime(*map(int, start_s.split(":")))
            end = dtime(*map(int, end_s.split(":")))
            if start <= end:
                return start <= now_t < end
            else:  # wraps midnight
                return now_t >= start or now_t < end
        except Exception:
            return False

    def _dispatch(self, message: str, play_sound: bool) -> None:
        """Runs in a background thread."""
        self._send_desktop_notification(message)
        if play_sound:
            self._play_sound()

    def _send_desktop_notification(self, message: str) -> None:
        if _PLYER_AVAILABLE:
            try:
                _plyer_notification.notify(
                    title=APP_TITLE,
                    message=message,
                    app_name=APP_TITLE,
                    app_icon=self._icon_path or None,
                    timeout=8,
                )
                return
            except Exception:
                pass

        # Fallback: Windows toast via PowerShell (no extra dependency)
        if platform.system() == "Windows":
            _windows_toast_fallback(APP_TITLE, message)

    def _play_sound(self) -> None:
        try:
            if platform.system() == "Windows":
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"],
                               check=False, capture_output=True)
            else:
                import subprocess
                # try paplay / aplay (no extra deps on most Linux desktops)
                for cmd in [["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                             ["aplay", "/usr/share/sounds/alsa/Front_Left.wav"]]:
                    r = subprocess.run(cmd, check=False, capture_output=True)
                    if r.returncode == 0:
                        break
        except Exception:
            pass  # sound failure is never fatal


def _windows_toast_fallback(title: str, message: str) -> None:
    """Trigger a Windows 10/11 toast notification via PowerShell."""
    try:
        import subprocess
        safe_title = title.replace("'", "").replace('"', "")
        safe_msg = message.replace("'", "").replace('"', "")
        script = (
            "[Windows.UI.Notifications.ToastNotificationManager,"
            " Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;"
            "[Windows.Data.Xml.Dom.XmlDocument,"
            " Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null;"
            "$xml = [Windows.UI.Notifications.ToastNotificationManager]::"
            "GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
            f"$xml.SelectSingleNode('//text[@id=1]').AppendChild($xml.CreateTextNode('{safe_title}')) | Out-Null;"
            f"$xml.SelectSingleNode('//text[@id=2]').AppendChild($xml.CreateTextNode('{safe_msg}')) | Out-Null;"
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml);"
            "$toast.Tag = 'TapoDesktopClient';"
            "[Windows.UI.Notifications.ToastNotificationManager]::"
            "CreateToastNotifier('Tapo Desktop Client').Show($toast);"
        )
        subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-Command", script],
            check=False, capture_output=True, timeout=5,
        )
    except Exception:
        pass

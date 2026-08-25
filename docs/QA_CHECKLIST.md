# QA Checklist — Tapo Desktop Client (Notifications Feature)

Manual test checklist for the alert/notification feature. Run through this
before each release or when notification-related code changes.

---

## Setup & First Run

- [ ] Fresh install on Windows with no prior config → first-run welcome dialog appears.
- [ ] Welcome dialog explains how to obtain Authorization token in plain English.
- [ ] Dismissing the welcome dialog prevents it from showing again on next launch.
- [ ] App loads and displays "Configure settings first" if credentials are empty.
- [ ] Clicking ⚙ Settings from the header opens the Settings page.

---

## Alert Settings UI

- [ ] "Alert & Notification Settings" section is visible in Settings.
- [ ] "Any Movement" checkbox defaults to **checked**.
- [ ] "A Person" checkbox defaults to **checked**.
- [ ] "A Vehicle" checkbox defaults to **unchecked**.
- [ ] "Play a sound with each alert" defaults to **checked**.
- [ ] Debounce field defaults to **30** seconds.
- [ ] "Don't disturb me between" quiet hours toggle defaults to **unchecked**.
- [ ] Quiet hours start/end fields default to 22:00 and 07:00.
- [ ] Clicking **Restore Defaults** resets all fields to the values above (without saving).
- [ ] Clicking **Save** persists all notification settings across app restart.
- [ ] Note about AI cameras (person/vehicle) is visible and readable.

---

## Test Notification Button

- [ ] Clicking **🔔 Test Notification** fires a desktop pop-up with:
      - Title: "Tapo Desktop Client"
      - Message containing "Test Camera", "Motion Detected", and current time HH:MM.
- [ ] Test notification fires even when "Any Movement" is unchecked.
- [ ] Test notification fires even when quiet hours are active.
- [ ] (Windows) A toast notification appears in the notification centre.
- [ ] (If sound is on) A brief alert sound is played alongside the pop-up.

---

## Live Event Monitoring

- [ ] After login and device load, status indicator in header turns 🟢 **Monitoring**.
- [ ] When credentials are removed/cleared, status turns 🔴 **Disconnected**.
- [ ] Simulated motion event (via API or test stub) triggers a desktop pop-up with
      format: `{Camera Name} • Motion Detected • HH:MM`.
- [ ] Person event triggers pop-up with "Person Detected".
- [ ] Vehicle event triggers pop-up with "Vehicle Detected" (if enabled).
- [ ] Disabled event types do NOT produce a pop-up.

---

## Debounce / Rate Limiting

- [ ] Two motion events for the same camera within the debounce window produce
      only ONE notification.
- [ ] Motion events on different cameras within the debounce window each produce
      their own notification.
- [ ] Motion and person events on the same camera within the debounce window each
      produce their own notification (different event types are independent).
- [ ] Setting debounce to 0 allows every event to produce a notification.

---

## Quiet Hours

- [ ] With quiet hours 22:00–07:00 enabled, no notification fires at 23:30.
- [ ] With quiet hours 22:00–07:00 enabled, notification fires at 12:00.
- [ ] Quiet hours spanning midnight (start > end) work correctly.
- [ ] Test Notification button still works during quiet hours.

---

## Status Indicator

- [ ] Status dot shows grey (no colour) before devices are loaded.
- [ ] Status dot shows 🟢 green and "Monitoring" when polling succeeds.
- [ ] Status dot shows 🟡 amber and "Reconnecting…" on temporary network failure.
- [ ] Status dot shows 🔴 red and "Disconnected" on sustained failure (3+ retries).
- [ ] Status recovers to 🟢 green after network is restored.

---

## Settings Persistence

- [ ] Settings survive app restart.
- [ ] Settings file is located in `%APPDATA%\TapoDesktopClient\notifications_config.json`
      on Windows (or the OS-appropriate path on macOS/Linux).
- [ ] Deleting the settings file causes app to use defaults on next launch.
- [ ] A partially-written settings file (missing keys) loads cleanly using defaults
      for the missing keys.

---

## Regression — Existing Features

- [ ] Live camera view still loads and plays after notification changes.
- [ ] PTZ controls (up/down/left/right) still work.
- [ ] Presets still load and work.
- [ ] Privacy mode toggle still works.
- [ ] RTSP settings still save and load.
- [ ] Going back from Settings to main view restores the previously selected camera.

---

## Platform Notes

| Platform | Expected notification method |
|---|---|
| Windows 10/11 | plyer → Windows Toast (notification centre) |
| macOS | plyer → macOS notification centre |
| Linux | plyer → libnotify / notify-send |
| Any (plyer unavailable) | PowerShell toast fallback (Windows only) or silent |

- [ ] Sound plays on Windows via `winsound.MessageBeep`.
- [ ] App does not crash if sound playback fails.
- [ ] App does not crash if notification dispatch fails (e.g. no display on CI).

---

*Last updated: 2025. Update this checklist whenever the notification feature changes.*

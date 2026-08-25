# Tapo Desktop Client

<p align="center">
  <img src="logo.png" alt="Tapo Desktop Client Logo">
</p>

## About the Project
Tapo Desktop Client is a third-party desktop application designed to manage and view your Tapo smart cameras from your PC, with **desktop pop-up alerts** for motion, person, and vehicle detection events.

**Disclaimer:** This is **not** an official TP-Link application. This project was developed by reverse-engineering the Tapo Android application (specifically based on version 3.15.117 / Android 11) to understand and utilize the internal API protocols.

---

## ⚡ 2-Minute Quick Start

1. **Install Python 3.10+** from https://www.python.org if you haven't already.
2. **Download this app** — click the green "Code" button on GitHub, then "Download ZIP". Unzip it anywhere (e.g. your Desktop).
3. **Open a terminal / command prompt** in the unzipped folder and run:
   ```
   pip install -r requirements.txt
   ```
4. **Start the app:**
   ```
   python main.py
   ```
5. **Click ⚙ Settings** (top-right corner) and enter your **Authorization token** and **X-Term-Id** — see [Configuration](#configuration-essential) below for how to get these.
6. **Click Save.** Your cameras will appear in the left panel.
7. **Choose your alerts** in the *Alert & Notification Settings* section of Settings, then Save again.
8. Walk in front of a camera — a desktop notification will pop up!

---

## 🏠 For Family Users — Recommended Setup

> *For Mum, Dad, grandparents, or anyone who just wants alerts without the technical details.*

**Step-by-step (with pictures):**

1. Ask a family member to complete the initial setup for you (steps 1–5 above).
2. Once cameras are showing on screen, click **⚙ Settings**.
3. Under **Alert & Notification Settings**:
   - ✅ Tick **Any Movement**
   - ✅ Tick **A Person**
   - ✅ Tick **Play a sound with each alert**
   - Leave everything else as-is
4. Click **🔔 Test Notification** — a pop-up should appear in the corner of your screen.
5. Click **Save** and close Settings.

That's it! You'll now get a pop-up (and a sound) every time someone is detected near your cameras. The alert will say something like:
> **Driveway Cam • Person Detected • 14:32**

**Recommended defaults:**

| Setting | Recommended |
|---|---|
| Alert on movement | ✅ On |
| Alert on person | ✅ On |
| Alert on vehicle | Off (turn on if you want it) |
| Sound | ✅ On |
| Wait between alerts | 30 seconds (prevents spam) |
| Quiet hours | Set to your sleeping hours, e.g. 23:00–07:00 |

---

## Installation

* **Clone the repository:**
  ```
  git clone https://github.com/DocwatZ/Tapo-Desktop-Client.git
  ```

* **Install dependencies:**
  ```
  pip install -r requirements.txt
  ```

* **Run the application:**
  ```
  python main.py
  ```

---

## Configuration (Essential)

For the app to communicate with your cameras you must provide your unique cloud credentials.

You need to provide:
* **Authorization Token**
* **X-Term-Id**

### How to get your tokens

These values are obtained by **capturing one network request** from the official Tapo Android app while it is active on your phone. Recommended tools:

* **PCAPDroid** (Android, free) — captures packets without root.
* **Charles Proxy** (PC + phone on same Wi-Fi) — intercepts HTTPS traffic.

Look for any request to `*.iot.i.tplinkcloud.com` and copy the `Authorization` and `X-Term-Id` headers.

### Setup Options

* **In-App:** Click ⚙ Settings, enter the values directly.
* **Environment File:** Create a `.env` file in the project root:
  ```
  Authorization=YOUR_TOKEN_HERE
  X-Term-Id=YOUR_ID_HERE
  ```

---

## Alert Notifications

The app polls your cameras every 15 seconds (configurable) for detection events and sends a native desktop notification when one is found.

**Notification format:**
> `{Camera Name} • {Event Type} • HH:MM`

**Supported event types:**
| Type | All cameras | AI cameras only* |
|---|---|---|
| Motion | ✅ | ✅ |
| Person | ❌ | ✅ |
| Vehicle | ❌ | ✅ |

\* AI cameras include models such as C120, C225, C325WB, and others with AI detection capability. Older models support motion detection only.

**Status indicator** (top-right corner):
* 🟢 **Monitoring** — connected and watching for events
* 🟡 **Reconnecting…** — temporary network issue, auto-retrying
* 🔴 **Disconnected** — check your internet connection and credentials

---

## Video Streaming

The application uses **RTSP** (Real Time Streaming Protocol) for live camera feeds.

* **Enable RTSP** in the official Tapo app under Camera Settings → Camera Account.
* **Local network only** by default — your PC must be on the same Wi-Fi as the cameras.
* **Remote access:** Use a VPN, port forwarding, or a reverse proxy to reach cameras from outside your home network.

---

## Troubleshooting

### "Configure settings first" appears / no cameras load
* Open ⚙ Settings and make sure both **Authorization** and **X-Term-Id** are filled in.
* Re-capture your tokens from the Tapo app — they expire after a few weeks.

### No desktop notifications appear
* Click **🔔 Test Notification** in Settings → Alert Settings. If that works, your notification settings are fine and the issue is with event detection.
* Make sure **"Any Movement"** is ticked in Alert Settings.
* Check the status indicator — if it shows 🔴 Disconnected, your tokens have expired.
* On Windows, check that notifications are enabled in Windows Settings → System → Notifications.

### Notification spam / too many alerts
* Increase the **Wait between alerts** value (default is 30 seconds).
* Enable **Quiet Hours** to suppress alerts overnight.

### Video stream won't play
* Make sure RTSP is enabled in the Tapo app.
* Confirm your PC is on the same network as the cameras.
* Check the username and password in ⚙ Settings → RTSP Configuration match those set in the Tapo app.

### "Person Detected" or "Vehicle Detected" never fires
* Your camera model may not support AI detection. Check the model number — AI detection is available on C120, C225, C325WB, and similar models.
* Make sure **"A Person"** / **"A Vehicle"** is ticked in Alert Settings.

### Tokens keep expiring
* This is a known limitation — Tapo cloud tokens expire periodically. Re-capture from the app when needed. Future versions may support direct username/password login.

---

## Video Streaming Notes

* **Activation:** Enable RTSP in the official Tapo app settings first.
* **Local Network:** By default the video stream only works if your PC is on the same private network as the cameras.
* **Remote Access:** Use a Proxy, Port Forwarding, or VPN to bridge the connection to your home network.

---

## New Dependencies Added

| Package | Version | Purpose |
|---|---|---|
| `plyer` | 2.1.0 | Cross-platform desktop notifications (Windows Toast, macOS, Linux notify-send). Chosen as the single lightest dependency for native OS notifications. Sound uses `winsound` (stdlib on Windows) — no additional package required. |

---

## Contributions
Open to contributions! If you have ideas for new features, bug fixes, or performance improvements, feel free to open an issue or submit a pull request.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

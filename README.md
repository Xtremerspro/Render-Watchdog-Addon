# Blender Local Web Render Monitor

A zero-dependency Blender addon that spins up a lightweight, background HTTP server directly inside Blender's Python instance. It hosts a modern, glassmorphic web dashboard accessible from your phone or any local device to monitor animation renders without needing to sit at your workstation.

Unlike decoupled trackers, this monitor hooks directly into Blender's core pipeline hooks to provide absolute, real-time frame tracking and immediate connection-drop alerts if Blender encounters a crash or system memory exhaustion.

## Features

* **Dark-Mode UI:** A mobile, responsive dashboard optimized for glancing at across the room.
* **Real-Time Frame & Progress Tracking:** Tracks frame steps precisely using native engine hooks (`render_pre`) to eliminate off-by-one frame lag.
* **Instant Crash/Offline Alarm:** If Blender crashes due to System RAM/VRAM exhaustion or a GPU driver timeout, the web UI automatically catches the connection failure within 1.5 seconds and flags an unmistakable crimson crash state.
* **Persistent Addon Architecture:** Uses `@persistent` decorators to survive project shifts (`Ctrl + N` or changing `.blend` files) without needing to restart the monitor script.
* **Zero External Dependencies:** Built entirely on standard Python libraries (`http.server`, `threading`, `json`). No external pip dependencies required.

---

## Installation

1. Download the `RenderWatchdog.py` script from this repository.
2. In Blender, navigate to **Edit > Preferences > Add-ons**.
3. Click **Install...** in the top-right corner, select the downloaded script, and click **Install Add-on**.
4. Click the bottom-left menu icon in the Preferences window and choose **Save Preferences** to keep it active across all future Blender sessions.

---

## How to Use

### 1. Find Your PC's Local Network IP
Because the server opens itself to your local network (`0.0.0.0`), you need your computer's local physical IP address to access it from another device.

* **Windows:** Open Command Prompt, type `ipconfig`, and find the **IPv4 Address** under your active connection adapter (e.g., *Wireless LAN adapter Wi-Fi* or *Ethernet adapter*). It typically looks like `10.0.0.XX` or `192.168.1.XX`.
* *Note: Ignore virtual interface adapters like WSL, VMware, or Mobile Hotspot (e.g., `192.168.137.1`).*

### 2. Connect via Phone
1. Ensure your mobile device is connected to the **same Wi-Fi network** as your workstation.
2. Open your phone's web browser and navigate to:
   ```text
   http://<YOUR_PC_IP>:5000/

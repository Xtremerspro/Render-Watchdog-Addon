bl_info = {
    "name": "Render Watchdog",
    "author": "Digiform",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Background Core",
    "description": "Hosts a local dashboard webserver to track render progress on mobile devices.",
    "category": "System",
}

import bpy
import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from bpy.app.handlers import persistent

PORT = 5000
_server_instance = None

monitor_data = {
    "status": "IDLE",
    "current_frame": 0,
    "start_frame": 0,
    "end_frame": 0,
    "percent": 0,
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blender Core Monitor</title>
    <style>
        :root {
            --bg: #0a0b10;
            --card-bg: rgba(25, 28, 41, 0.65);
            --border: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-idle: #3b82f6;
            --accent-render: #10b981;
            --accent-crash: #ef4444;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            box-sizing: border-box;
        }
        .container {
            width: 100%;
            max-width: 420px;
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 32px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            text-align: center;
        }
        h1 {
            font-size: 1.2rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-muted);
            margin: 0 0 24px 0;
        }
        .status-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 30px;
            font-weight: 700;
            font-size: 0.9rem;
            letter-spacing: 1px;
            margin-bottom: 32px;
            transition: all 0.4s ease;
        }
        .status-idle { background: rgba(59, 130, 246, 0.15); color: var(--accent-idle); border: 1px solid rgba(59, 130, 246, 0.3); }
        .status-rendering { background: rgba(16, 185, 129, 0.15); color: var(--accent-render); border: 1px solid rgba(16, 185, 129, 0.3); animation: pulse 2s infinite; }
        .status-crashed { background: rgba(239, 68, 68, 0.15); color: var(--accent-crash); border: 1px solid rgba(239, 68, 68, 0.3); animation: shake 0.4s infinite; }
        
        .progress-container {
            position: relative;
            margin: 20px 0;
        }
        .progress-bar-bg {
            background: rgba(255,255,255,0.05);
            height: 12px;
            border-radius: 6px;
            width: 100%;
            overflow: hidden;
        }
        .progress-bar-fill {
            height: 100%;
            width: 0%;
            background: var(--accent-idle);
            border-radius: 6px;
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .render-active .progress-bar-fill {
            background: var(--accent-render);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 32px;
        }
        .stat-card {
            background: rgba(255,255,255,0.02);
            border: 1px solid var(--border);
            padding: 16px;
            border-radius: 16px;
        }
        .stat-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 6px;
            letter-spacing: 0.5px;
        }
        .stat-value {
            font-size: 1.3rem;
            font-weight: 600;
            font-family: monospace;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
            70% { box-shadow: 0 0 0 12px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-2px); }
            75% { transform: translateX(2px); }
        }
    </style>
</head>
<body>
    <div class="container" id="main-container">
        <h1>Workstation Pipeline</h1>
        <div id="status" class="status-badge status-idle">IDLE</div>
        
        <div class="progress-container">
            <div class="progress-bar-bg">
                <div id="progress-fill" class="progress-bar-fill"></div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Progress</div>
                <div id="percentage" class="stat-value">0%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Frame Range</div>
                <div id="frame-range" class="stat-value">-- / --</div>
            </div>
        </div>
    </div>

    <script>
        async function fetchUpdate() {
            try {
                const response = await fetch('/api', { signal: AbortSignal.timeout(1500) });
                const data = await response.json();
                
                const statusEl = document.getElementById('status');
                const container = document.getElementById('main-container');
                
                statusEl.innerText = data.status;
                statusEl.className = 'status-badge status-' + data.status.toLowerCase();
                
                if(data.status === 'RENDERING') {
                    container.classList.add('render-active');
                } else {
                    container.classList.remove('render-active');
                }
                
                document.getElementById('progress-fill').style.width = data.percent + '%';
                document.getElementById('percentage').innerText = Math.round(data.percent) + '%';
                document.getElementById('frame-range').innerText = data.current_frame + ' / ' + data.end_frame;
                
            } catch (error) {
                const statusEl = document.getElementById('status');
                statusEl.innerText = 'CRASHED / OFFLINE';
                statusEl.className = 'status-badge status-crashed';
                document.getElementById('progress-fill').style.backgroundColor = '#ef4444';
            }
        }
        setInterval(fetchUpdate, 1000);
    </script>
</body>
</html>
"""


class AddonServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/api":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(monitor_data).encode("utf-8"))
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    global _server_instance
    server_address = ("0.0.0.0", PORT)
    HTTPServer.allow_reuse_address = True
    _server_instance = HTTPServer(server_address, AddonServerHandler)
    print(f"[Pipeline Monitor] Server listening on port {PORT}...")
    _server_instance.serve_forever()


def update_state(status):
    scene = bpy.context.scene if bpy.context else None
    if not scene:
        return

    total = max(1, (scene.frame_end - scene.frame_start))
    current_progress_frame = scene.frame_current - scene.frame_start

    global monitor_data
    monitor_data["status"] = status
    monitor_data["current_frame"] = scene.frame_current
    monitor_data["start_frame"] = scene.frame_start
    monitor_data["end_frame"] = scene.frame_end
    monitor_data["percent"] = max(0, min(((current_progress_frame / total) * 100), 100))


@persistent
def on_render_init(scene):
    update_state("RENDERING")


@persistent
def on_frame_render(scene):
    update_state("RENDERING")


@persistent
def on_render_exit(scene):
    global monitor_data
    monitor_data["status"] = "IDLE"


def register():
    bpy.app.handlers.render_init.append(on_render_init)
    # Changed from render_post to render_pre to eliminate the 1-frame lag display bug
    bpy.app.handlers.render_pre.append(on_frame_render)
    bpy.app.handlers.render_complete.append(on_render_exit)
    bpy.app.handlers.render_cancel.append(on_render_exit)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()


def unregister():
    global _server_instance

    if on_render_init in bpy.app.handlers.render_init:
        bpy.app.handlers.render_init.remove(on_render_init)
    if on_frame_render in bpy.app.handlers.render_pre:
        bpy.app.handlers.render_pre.remove(on_frame_render)
    if on_render_exit in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(on_render_exit)
    if on_render_exit in bpy.app.handlers.render_cancel:
        bpy.app.handlers.render_cancel.remove(on_render_exit)

    if _server_instance:
        _server_instance.shutdown()
        _server_instance.server_close()
        print("[Pipeline Monitor] Server cleanly destroyed.")


if __name__ == "__main__":
    register()

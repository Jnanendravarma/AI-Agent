import os
import json
import socket
import threading
import http.server
import psutil
from utils.logger import logger

# Store reference to executor dynamically
_executor_ref = None

def set_executor_reference(executor):
    global _executor_ref
    _executor_ref = executor

def get_dashboard_stats() -> dict:
    """Gathers real-time performance and application statistics."""
    stats = {
        "cpu": 0,
        "ram": 0,
        "disk": 0,
        "net_sent": 0,
        "net_recv": 0,
        "online": False,
        "running_apps": 0,
        "discovered_apps": 0,
        "command_patterns": 0,
        "last_commands": [],
        "system_status": "Idle"
    }
    
    try:
        # 1. System specs (psutil)
        stats["cpu"] = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        stats["ram"] = ram.percent
        disk = psutil.disk_usage('/')
        stats["disk"] = disk.percent
        
        net_io = psutil.net_io_counters()
        stats["net_sent"] = net_io.bytes_sent
        stats["net_recv"] = net_io.bytes_recv
        stats["running_apps"] = len(list(psutil.process_iter()))
    except Exception as e:
        logger.log_error(f"Dashboard failed to gather psutil metrics: {e}")

    # 2. Assistant stats
    global _executor_ref
    if _executor_ref:
        stats["online"] = getattr(_executor_ref, "online", True)
        stats["discovered_apps"] = len(getattr(_executor_ref, "discovered_apps", {}))
        stats["command_patterns"] = len(getattr(_executor_ref, "commands_lookup", {}))
        stats["system_status"] = "Active Chat" if getattr(_executor_ref, "in_chat_mode", False) else "Automation Mode"

    # 3. Read command history
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    history_path = os.path.join(base_dir, "history", "command_history.json")
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
                stats["last_commands"] = history[-8:] # get last 8 commands
        except Exception:
            pass

    return stats

class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute standard HTTP log spam on console
        pass

    def do_GET(self):
        # 1. API endpoint for performance statistics
        if self.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = get_dashboard_stats()
            self.wfile.write(json.dumps(data).encode())
            return
            
        # 2. Serve index page
        if self.path in ["/", "/index.html", "/dashboard"]:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dashboard_html_path = os.path.join(base_dir, "dashboard", "dashboard.html")
            
            if os.path.exists(dashboard_html_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                with open(dashboard_html_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        super().do_GET()

class DashboardServer:
    def __init__(self, port: int = 8000):
        self.port = port
        self.server = None
        self.thread = None
        self.running = False

    def start(self):
        """Starts the local dashboard server in a daemon thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        logger.log_info(f"Dashboard web server active at http://localhost:{self.port}")

    def _run_server(self):
        try:
            self.server = http.server.HTTPServer(("localhost", self.port), DashboardRequestHandler)
            self.server.serve_forever()
        except Exception as e:
            logger.log_error(f"Dashboard server failed to start: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.running = False
            logger.log_info("Dashboard web server stopped.")

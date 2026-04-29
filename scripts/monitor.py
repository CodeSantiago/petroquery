#!/usr/bin/env python3
"""
PetroQuery Agent Monitor
Muestra el estado actual de construcción del proyecto.
Uso:
    python scripts/monitor.py              # Muestra estado en terminal
    python scripts/monitor.py --serve      # Lanza servidor HTTP en :8765
"""
import argparse
import json
import http.server
import socketserver
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / ".petroquery" / "build_state.json"


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"error": "No build state found"}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def print_state(state: dict):
    print("=" * 70)
    print(f"  PETROQUERY BUILD MONITOR  |  {state.get('project', 'Unknown')}")
    print("=" * 70)
    print()
    for agent in state.get("agents", []):
        status_icon = "✅" if agent.get("status") == "completed" else "🔄" if agent.get("status") == "in_progress" else "⏳"
        print(f"{status_icon} {agent['name']} [{agent['status'].upper()}]")
        for task in agent.get("tasks", []):
            t_icon = "  ✓" if task.get("status") == "completed" else "  ·"
            print(f"{t_icon} {task['task']}")
        print()
    pending = state.get("pending_files", [])
    if pending:
        print("📁 Archivos pendientes:")
        for f in pending:
            print(f"   - {f}")
    print("=" * 70)


class MonitorHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            state = load_state()
            html = self._render_html(state)
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/api/state":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(load_state()).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _render_html(self, state: dict) -> str:
        agents_html = ""
        for agent in state.get("agents", []):
            status_class = agent.get("status", "pending")
            status_icon = {"completed": "✅", "in_progress": "🔄", "pending": "⏳"}.get(status_class, "⏳")
            tasks_html = ""
            for task in agent.get("tasks", []):
                t_icon = "✓" if task.get("status") == "completed" else "·"
                tasks_html += f'<li class="task {task.get("status","")}">{t_icon} {task["task"]}</li>'
            agents_html += f"""
            <div class="agent {status_class}">
                <h3>{status_icon} {agent['name']}</h3>
                <ul>{tasks_html}</ul>
            </div>
            """
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PetroQuery Monitor</title>
<style>
body {{ font-family: monospace; background: #0a0a14; color: #e0e0e0; padding: 2rem; }}
h1 {{ color: #1A237E; border-bottom: 2px solid #FF6F00; padding-bottom: 0.5rem; }}
.agent {{ border: 1px solid #333; margin: 1rem 0; padding: 1rem; background: #141428; }}
.agent.completed {{ border-left: 4px solid #C0CA33; }}
.agent.in_progress {{ border-left: 4px solid #FF6F00; }}
.agent.pending {{ border-left: 4px solid #555; }}
h3 {{ margin-top: 0; color: #FF6F00; }}
.task {{ list-style: none; margin: 0.3rem 0; }}
.task.completed {{ color: #C0CA33; }}
</style>
</head>
<body>
<h1>🛢️ PetroQuery Build Monitor</h1>
{agents_html}
<p style="color:#666;font-size:0.8rem;margin-top:2rem;">Actualizado: {datetime.now().isoformat()}</p>
</body>
</html>"""

    def log_message(self, format, *args):
        pass  # Silenciar logs


def serve(port: int = 8765):
    with socketserver.TCPServer(("", port), MonitorHandler) as httpd:
        print(f"🖥️  Monitor de PetroQuery corriendo en http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Monitor detenido")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PetroQuery Agent Monitor")
    parser.add_argument("--serve", action="store_true", help="Lanzar servidor HTTP")
    parser.add_argument("--port", type=int, default=8765, help="Puerto (default: 8765)")
    args = parser.parse_args()

    if args.serve:
        serve(args.port)
    else:
        print_state(load_state())

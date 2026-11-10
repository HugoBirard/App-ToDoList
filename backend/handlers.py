"""
Gestionnaire HTTP et répartiteur d'API REST.
Lie les requêtes HTTP entrantes aux méthodes du TodoService.
"""

import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler
from .config import STATIC_DIR
from .services import TodoService


class TodoRequestHandler(SimpleHTTPRequestHandler):
    db_path = None

    def __init__(self, *args, **kwargs):
        self.service = TodoService(db_path=self.db_path)
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        # Silence les logs HTTP répétitifs en console
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, data, status=200):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response_bytes)

    def parse_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/data":
            data = self.service.get_all_data()
            self.send_json(data)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        parts = path.strip("/").split("/")
        payload = self.parse_body()

        # POST /api/folders/<id>/reset
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "folders" and parts[3] == "reset":
            folder_id = int(parts[2])
            self.service.reset_folder_tasks(folder_id)
            self.send_json({"success": True})
            return

        # POST /api/folders
        if path == "/api/folders":
            folder = self.service.create_folder(payload)
            self.send_json(folder, status=201)
            return

        # POST /api/tasks
        if path == "/api/tasks":
            title = (payload.get("title") or "").strip()
            if not title:
                self.send_json({"error": "Le titre est requis"}, status=400)
                return
            task = self.service.create_task(payload)
            self.send_json(task, status=201)
            return

        # POST /api/tasks/clear-completed
        if path == "/api/tasks/clear-completed":
            folder_id = payload.get("folder_id")
            self.service.clear_completed(folder_id)
            self.send_json({"success": True})
            return

        self.send_json({"error": "Route introuvable"}, status=404)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        parts = path.strip("/").split("/")
        payload = self.parse_body()

        # PUT /api/settings
        if path == "/api/settings":
            settings = self.service.update_settings(payload)
            self.send_json(settings)
            return

        # PUT /api/folders/<id>
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "folders":
            folder_id = int(parts[2])
            updated = self.service.update_folder(folder_id, payload)
            if updated:
                self.send_json(updated)
            else:
                self.send_json({"error": "Dossier introuvable"}, status=404)
            return

        # PUT /api/tasks/<id>
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "tasks":
            task_id = int(parts[2])
            updated = self.service.update_task(task_id, payload)
            if updated:
                self.send_json(updated)
            else:
                self.send_json({"error": "Tâche introuvable"}, status=404)
            return

        self.send_json({"error": "Route introuvable"}, status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        parts = path.strip("/").split("/")

        # DELETE /api/folders/<id>
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "folders":
            folder_id = int(parts[2])
            self.service.delete_folder(folder_id)
            self.send_json({"success": True})
            return

        # DELETE /api/tasks/<id>
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "tasks":
            task_id = int(parts[2])
            self.service.delete_task(task_id)
            self.send_json({"success": True})
            return

        self.send_json({"error": "Route introuvable"}, status=404)

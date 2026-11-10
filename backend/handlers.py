"""
Gestionnaire HTTP et répartiteur d'API REST.
Lie les requêtes HTTP entrantes aux méthodes du TodoService de façon robuste et sécurisée.
"""

import json
import os
import subprocess
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
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
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

    def parse_id(self, val):
        """Parse de manière sécurisée un entier d'identifiant d'URL compatible SQLite 64-bit."""
        try:
            n = int(val)
            if 0 < n <= 9223372036854775807:
                return n
            return None
        except (ValueError, TypeError, OverflowError):
            return None

    def parse_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0

        if content_length <= 0:
            return {}

        # Limite de taille de payload : 5 Mo
        if content_length > 5 * 1024 * 1024:
            return {}

        try:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path == "/api/data":
                data = self.service.get_all_data()
                self.send_json(data)
                return

            # GET /api/sync/status
            if path == "/api/sync/status":
                self.send_json(self.service.get_storage_info())
                return

            # GET /api/sync/check-updates
            if path == "/api/sync/check-updates":
                self.send_json(self.service.check_updates())
                return

            # GET /api/storage/export
            if path == "/api/storage/export":
                self.send_json(self.service.export_backup())
                return

            super().do_GET()
        except Exception as e:
            self.send_json({"error": "Erreur interne", "details": str(e)}, status=500)

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            parts = path.strip("/").split("/")
            payload = self.parse_body()

            # POST /api/folders/<id>/reset
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "folders" and parts[3] == "reset":
                folder_id = self.parse_id(parts[2])
                if not folder_id:
                    self.send_json({"error": "Identifiant de dossier invalide"}, status=400)
                    return
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
                if folder_id is not None:
                    folder_id = self.parse_id(folder_id)
                self.service.clear_completed(folder_id)
                self.send_json({"success": True})
                return

            # POST /api/storage/change-path
            if path == "/api/storage/change-path":
                target_path = payload.get("target_path")
                action = payload.get("action", "connect")
                res = self.service.change_storage_path(target_path, action=action)
                self.send_json(res)
                return

            # POST /api/storage/browse
            if path == "/api/storage/browse":
                chosen = ""
                try:
                    proc = subprocess.run(
                        [
                            "zenity",
                            "--file-selection",
                            "--save",
                            "--confirm-overwrite",
                            "--filename=todolist.db",
                            "--file-filter=Base de données SQLite (*.db)|*.db",
                            "--file-filter=Tous les fichiers|*",
                            "--title=Choisir l'emplacement partagé de la base ToDoList"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if proc.returncode == 0:
                        chosen = proc.stdout.strip()
                except Exception:
                    chosen = ""
                self.send_json({"path": chosen})
                return

            # POST /api/storage/import
            if path == "/api/storage/import":
                mode = payload.get("mode", "merge")
                data = payload.get("data") or payload
                res = self.service.import_backup(data, mode=mode)
                self.send_json({"success": True, "data": res})
                return

            self.send_json({"error": "Route introuvable"}, status=404)
        except Exception as e:
            self.send_json({"error": "Erreur interne", "details": str(e)}, status=500)

    def do_PUT(self):
        try:
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
                folder_id = self.parse_id(parts[2])
                if not folder_id:
                    self.send_json({"error": "Identifiant de dossier invalide"}, status=400)
                    return
                updated = self.service.update_folder(folder_id, payload)
                if updated:
                    self.send_json(updated)
                else:
                    self.send_json({"error": "Dossier introuvable"}, status=404)
                return

            # PUT /api/tasks/<id>
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "tasks":
                task_id = self.parse_id(parts[2])
                if not task_id:
                    self.send_json({"error": "Identifiant de tâche invalide"}, status=400)
                    return
                updated = self.service.update_task(task_id, payload)
                if updated:
                    self.send_json(updated)
                else:
                    self.send_json({"error": "Tâche introuvable"}, status=404)
                return

            self.send_json({"error": "Route introuvable"}, status=404)
        except Exception as e:
            self.send_json({"error": "Erreur interne", "details": str(e)}, status=500)

    def do_DELETE(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            parts = path.strip("/").split("/")

            # DELETE /api/folders/<id>
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "folders":
                folder_id = self.parse_id(parts[2])
                if not folder_id:
                    self.send_json({"error": "Identifiant de dossier invalide"}, status=400)
                    return
                self.service.delete_folder(folder_id)
                self.send_json({"success": True})
                return

            # DELETE /api/tasks/<id>
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "tasks":
                task_id = self.parse_id(parts[2])
                if not task_id:
                    self.send_json({"error": "Identifiant de tâche invalide"}, status=400)
                    return
                self.service.delete_task(task_id)
                self.send_json({"success": True})
                return

            self.send_json({"error": "Route introuvable"}, status=404)
        except Exception as e:
            self.send_json({"error": "Erreur interne", "details": str(e)}, status=500)

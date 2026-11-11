"""
Gestionnaire HTTP et répartiteur d'API REST.
Lie les requêtes HTTP entrantes aux méthodes du TodoService de façon robuste et sécurisée.
"""

import base64
import hmac
import json
import logging
import os
import subprocess
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler
from .config import STATIC_DIR, DEFAULT_PORT, get_lan_ips
from .services import TodoService
from .discord import send_test_message

logger = logging.getLogger("todolist.http")


class PayloadTooLargeError(Exception):
    """Exception levée lorsque le corps de la requête dépasse la taille maximale autorisée."""
    pass


class TodoRequestHandler(SimpleHTTPRequestHandler):
    db_path = None
    api_token = None

    LOCAL_ONLY_ROUTES = {
        "/api/storage/change-path",
        "/api/storage/browse",
        "/api/storage/pick",
        "/api/storage/import",
        "/api/storage/export",
        "/api/sync/status",
    }

    def __init__(self, *args, **kwargs):
        self.service = TodoService(db_path=self.db_path)
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        # Silence les logs HTTP répétitifs en console
        pass

    @property
    def server_port(self):
        """Récupère le port réel d'écoute du serveur de façon fiable."""
        if hasattr(self.server, "server_port"):
            return self.server.server_port
        if hasattr(self.server, "server_address") and isinstance(self.server.server_address, tuple):
            return self.server.server_address[1]
        return DEFAULT_PORT

    def _is_local_client(self):
        """Vérifie si la requête provient de la machine hôte elle-même."""
        if not self.client_address:
            return False
        client_ip = self.client_address[0]
        return client_ip in ("127.0.0.1", "::1", "localhost")

    def _check_auth(self):
        """Vérifie le jeton d'authentification partagé si configuré."""
        if not self.api_token:
            return True
        auth_header = self.headers.get("Authorization", "")
        sent = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else auth_header.strip()
        if sent and hmac.compare_digest(sent, self.api_token):
            return True
        self.send_json({"error": "Non autorisé"}, status=401)
        return False

    def _get_allowed_origins(self):
        """Définit la liste stricte des origines CORS autorisées."""
        port = self.server_port
        allowed = {
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
            f"http://127.0.0.1:{DEFAULT_PORT}",
            f"http://localhost:{DEFAULT_PORT}",
        }
        try:
            for ip in get_lan_ips():
                allowed.add(f"http://{ip}:{port}")
                allowed.add(f"http://{ip}:{DEFAULT_PORT}")
        except Exception:
            pass
        return allowed

    def _is_origin_allowed(self, origin):
        """Valide si l'en-tête Origin est autorisé."""
        if not origin:
            return True
        return origin.rstrip("/") in self._get_allowed_origins()

    def _check_origin(self):
        """Rejette les requêtes d'écriture dont l'en-tête Origin est spécifié mais non autorisé."""
        origin = self.headers.get("Origin")
        if origin and not self._is_origin_allowed(origin):
            self.send_json({"error": "Origine non autorisée"}, status=403)
            return False
        return True

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

        # CORS restreint aux origines légitimes (pas de wildcard '*')
        origin = self.headers.get("Origin")
        if origin and self._is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

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
        """Parse le corps JSON de la requête avec limitation stricte de taille."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0

        if content_length <= 0:
            return {}

        # Limite de taille de payload : 5 Mo
        if content_length > 5 * 1024 * 1024:
            raise PayloadTooLargeError("Corps de requête trop volumineux (max 5 Mo)")

        try:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_OPTIONS(self):
        origin = self.headers.get("Origin")
        if origin and not self._is_origin_allowed(origin):
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(204)
        if origin and self._is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path.startswith("/api/"):
                if not self._check_auth():
                    return
                if path in self.LOCAL_ONLY_ROUTES and not self._is_local_client():
                    self.send_json({"error": "Action réservée à la machine hôte"}, status=403)
                    return

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

            # GET /api/network/info
            if path == "/api/network/info":
                ips = get_lan_ips()
                port = self.server_port
                self.send_json({
                    "port": port,
                    "local_url": f"http://127.0.0.1:{port}",
                    "network_ips": ips,
                    "network_urls": [f"http://{ip}:{port}" for ip in ips]
                })
                return

            super().do_GET()
        except Exception:
            logger.exception("Erreur sur %s %s", self.command, self.path)
            self.send_json({"error": "Erreur interne"}, status=500)

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if not self._check_origin():
                return

            if path.startswith("/api/"):
                if not self._check_auth():
                    return
                if path in self.LOCAL_ONLY_ROUTES and not self._is_local_client():
                    self.send_json({"error": "Action réservée à la machine hôte"}, status=403)
                    return

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

            # POST /api/folders/reorder
            if path == "/api/folders/reorder":
                folder_ids = payload.get("folder_ids") or payload.get("order") or []
                self.service.reorder_folders(folder_ids)
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

            # POST /api/discord/test
            if path == "/api/discord/test":
                webhook_url = (payload.get("webhook_url") or "").strip().strip("'\"")
                author_name = (payload.get("author_name") or "Utilisateur ToDoList").strip()
                
                # Si l'URL n'est pas transmise ou masquée (••••), aller chercher l'URL réelle en base
                if not webhook_url or webhook_url.startswith("••••"):
                    try:
                        conn = self.service._conn()
                        cur = conn.cursor()
                        cur.execute("SELECT value FROM settings WHERE key = 'discord_webhook_url'")
                        row = cur.fetchone()
                        conn.close()
                        if row and row["value"]:
                            webhook_url = str(row["value"]).strip()
                    except Exception:
                        pass

                if not webhook_url:
                    self.send_json({"success": False, "message": "Aucune URL de webhook Discord n'a été trouvée."}, status=400)
                    return

                ok, msg = send_test_message(webhook_url, author_name=author_name)
                if ok and not webhook_url.startswith("••••"):
                    # Enregistrer immédiatement en base si le test est concluant
                    try:
                        self.service.update_settings({
                            "discord_webhook_url": webhook_url,
                            "discord_enabled": "1",
                            "discord_author_name": author_name
                        })
                    except Exception:
                        pass
                self.send_json({"success": ok, "message": msg}, status=200 if ok else 400)
                return

            # POST /api/upload/background (Upload d'image personnalisée de fond)
            if path == "/api/upload/background":
                raw_image = payload.get("image") or ""
                if not raw_image:
                    self.send_json({"error": "Aucune image fournie"}, status=400)
                    return

                # Découper le préfixe data URL
                # Ex: data:image/jpeg;base64,...
                ext = "jpg"
                if "," in raw_image:
                    header, base64_data = raw_image.split(",", 1)
                    if "image/png" in header:
                        ext = "png"
                    elif "image/webp" in header:
                        ext = "webp"
                else:
                    base64_data = raw_image

                try:
                    img_bytes = base64.b64decode(base64_data)
                except Exception:
                    self.send_json({"error": "Format d'encodage base64 invalide"}, status=400)
                    return

                if len(img_bytes) > 5 * 1024 * 1024:
                    self.send_json({"error": "L'image dépasse la limite de 5 Mo"}, status=413)
                    return

                # Sauvegarder dans static/assets/
                is_folder_scope = payload.get("scope") == "folder"
                folder_id = payload.get("folder_id")
                timestamp = int(time.time() * 1000)

                if is_folder_scope and folder_id:
                    target_filename = f"folder-bg-{folder_id}.{ext}"
                elif is_folder_scope:
                    target_filename = f"folder-bg-{timestamp}.{ext}"
                else:
                    target_filename = f"custom-background.{ext}"

                target_path = os.path.join(STATIC_DIR, "assets", target_filename)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "wb") as f:
                    f.write(img_bytes)

                relative_url = f"/assets/{target_filename}?t={timestamp}"
                bg_value = f"url('{relative_url}') center / cover no-repeat fixed #08090c"

                if not is_folder_scope:
                    # Mettre à jour les settings en base uniquement si c'est pour le thème global
                    self.service.update_settings({"main_background": bg_value})

                self.send_json({
                    "success": True,
                    "url": relative_url,
                    "bg_value": bg_value
                })
                return

            self.send_json({"error": "Route introuvable"}, status=404)
        except PayloadTooLargeError:
            self.send_json({"error": "Payload trop volumineux (max 5 Mo)"}, status=413)
        except Exception:
            logger.exception("Erreur sur %s %s", self.command, self.path)
            self.send_json({"error": "Erreur interne"}, status=500)

    def do_PUT(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if not self._check_origin():
                return

            if path.startswith("/api/"):
                if not self._check_auth():
                    return
                if path in self.LOCAL_ONLY_ROUTES and not self._is_local_client():
                    self.send_json({"error": "Action réservée à la machine hôte"}, status=403)
                    return

            parts = path.strip("/").split("/")
            payload = self.parse_body()

            # PUT /api/settings
            if path == "/api/settings":
                settings = self.service.update_settings(payload)
                self.send_json(settings)
                return

            # PUT /api/folders/reorder
            if path == "/api/folders/reorder":
                folder_ids = payload.get("folder_ids") or payload.get("order") or []
                self.service.reorder_folders(folder_ids)
                self.send_json({"success": True})
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
        except PayloadTooLargeError:
            self.send_json({"error": "Payload trop volumineux (max 5 Mo)"}, status=413)
        except Exception:
            logger.exception("Erreur sur %s %s", self.command, self.path)
            self.send_json({"error": "Erreur interne"}, status=500)

    def do_DELETE(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if not self._check_origin():
                return

            if path.startswith("/api/"):
                if not self._check_auth():
                    return
                if path in self.LOCAL_ONLY_ROUTES and not self._is_local_client():
                    self.send_json({"error": "Action réservée à la machine hôte"}, status=403)
                    return

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
        except Exception:
            logger.exception("Erreur sur %s %s", self.command, self.path)
            self.send_json({"error": "Erreur interne"}, status=500)

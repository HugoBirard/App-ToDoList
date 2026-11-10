"""
Tests unitaires et d'intégration pour les routes API REST du TodoRequestHandler.
"""

import json
import os
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

from backend.database import init_db
from backend.handlers import TodoRequestHandler


class HandlersTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "test_api.db")
        init_db(cls.db_path)

        class CustomHandler(TodoRequestHandler):
            db_path = cls.db_path

        # Lancer le serveur de test sur un port éphémère (0)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), CustomHandler)
        cls.port = cls.httpd.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.temp_dir.cleanup()

    def _request(self, method, path, data=None):
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                content = json.loads(resp.read().decode("utf-8"))
                return status, content
        except urllib.error.HTTPError as e:
            try:
                content = json.loads(e.read().decode("utf-8"))
            except Exception:
                content = None
            finally:
                e.close()
            return e.code, content

    def test_get_initial_data(self):
        status, data = self._request("GET", "/api/data")
        self.assertEqual(status, 200)
        self.assertIn("folders", data)
        self.assertIn("tasks", data)
        self.assertIn("settings", data)

    def test_create_and_update_folder(self):
        status, folder = self._request("POST", "/api/folders", {
            "name": "Dossier API",
            "icon": "briefcase",
            "color": "#10b981"
        })
        self.assertEqual(status, 201)
        self.assertEqual(folder["name"], "Dossier API")
        folder_id = folder["id"]

        # Mise à jour
        status, updated = self._request("PUT", f"/api/folders/{folder_id}", {
            "name": "Dossier Renommé"
        })
        self.assertEqual(status, 200)
        self.assertEqual(updated["name"], "Dossier Renommé")

    def test_task_crud_and_validation(self):
        # Validation : titre vide -> 400
        status, err = self._request("POST", "/api/tasks", {"title": "   "})
        self.assertEqual(status, 400)
        self.assertIn("error", err)

        # Création réussie
        status, task = self._request("POST", "/api/tasks", {
            "title": "Tâche via API",
            "has_progress": 1,
            "progress": 25
        })
        self.assertEqual(status, 201)
        task_id = task["id"]
        self.assertEqual(task["title"], "Tâche via API")

        # Mise à jour progression -> 100% coche la tâche
        status, updated = self._request("PUT", f"/api/tasks/{task_id}", {
            "progress": 100
        })
        self.assertEqual(status, 200)
        self.assertEqual(updated["completed"], 1)

        # Suppression
        status, resp = self._request("DELETE", f"/api/tasks/{task_id}")
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("success"))

    def test_not_found_route(self):
        status, err = self._request("GET", "/api/unknown_endpoint")
        self.assertEqual(status, 404)

    def test_invalid_url_identifiers(self):
        # Non-integer IDs doivent renvoyer un statut 400 propre
        status, err = self._request("PUT", "/api/tasks/abc", {"title": "Test"})
        self.assertEqual(status, 400)
        self.assertIn("error", err)

        status, err = self._request("DELETE", "/api/tasks/notanumber")
        self.assertEqual(status, 400)

        status, err = self._request("DELETE", "/api/tasks/-5")
        self.assertEqual(status, 400)

        status, err = self._request("PUT", "/api/tasks/99999999999999999999999999999999", {"title": "Overflow"})
        self.assertEqual(status, 400)

    def test_security_headers(self):
        url = f"{self.base_url}/api/data"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            headers = resp.headers
            self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
            self.assertEqual(headers.get("X-Frame-Options"), "DENY")
            self.assertEqual(headers.get("Referrer-Policy"), "no-referrer")

    def test_sqli_resilience(self):
        payload = "' OR '1'='1"
        status, task = self._request("POST", "/api/tasks", {"title": payload})
        self.assertEqual(status, 201)
        self.assertEqual(task["title"], payload)

    def test_storage_and_sync_endpoints(self):
        # GET /api/sync/status
        status, info = self._request("GET", "/api/sync/status")
        self.assertEqual(status, 200)
        self.assertIn("current_db_path", info)
        self.assertTrue(info["file_exists"])

        # GET /api/sync/check-updates
        status, upd = self._request("GET", "/api/sync/check-updates")
        self.assertEqual(status, 200)
        self.assertIn("last_modified", upd)

        # GET /api/storage/export
        status, export = self._request("GET", "/api/storage/export")
        self.assertEqual(status, 200)
        self.assertEqual(export["app"], "ToDoList")
        self.assertIn("data", export)

        # POST /api/storage/import
        status, imported = self._request("POST", "/api/storage/import", {
            "mode": "merge",
            "data": export["data"]
        })
        self.assertEqual(status, 200)
        self.assertTrue(imported.get("success"))


if __name__ == "__main__":
    unittest.main()

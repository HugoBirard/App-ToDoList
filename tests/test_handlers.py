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
        from backend.config import STATIC_DIR
        for ext in ("png", "jpg", "jpeg", "webp"):
            for prefix in ("custom-background", "folder-bg-42"):
                p = os.path.join(STATIC_DIR, "assets", f"{prefix}.{ext}")
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

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

        # GET /api/network/info
        status, net_info = self._request("GET", "/api/network/info")
        self.assertEqual(status, 200)
        self.assertIn("local_url", net_info)
        self.assertIn("network_ips", net_info)
        self.assertIn("network_urls", net_info)

    def test_reorder_folders_endpoint(self):
        s1, f1 = self._request("POST", "/api/folders", {"name": "Alpha"})
        s2, f2 = self._request("POST", "/api/folders", {"name": "Beta"})
        self.assertEqual(s1, 201)
        self.assertEqual(s2, 201)

        status, res = self._request("POST", "/api/folders/reorder", {
            "folder_ids": [f2["id"], f1["id"]]
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))

        status, data = self._request("GET", "/api/data")
        self.assertEqual(status, 200)
        matching = [f["id"] for f in data["folders"] if f["id"] in (f1["id"], f2["id"])]
        self.assertEqual(matching, [f2["id"], f1["id"]])

    def test_system_update_endpoints(self):
        # GET /api/system/update-status
        status, res = self._request("GET", "/api/system/update-status")
        self.assertEqual(status, 200)
        self.assertIn("is_git", res)
        self.assertIn("update_available", res)

        # POST /api/system/apply-update (mocked ou testé)
        from unittest.mock import patch
        with patch("backend.handlers.apply_update") as mock_apply:
            mock_apply.return_value = {"success": True, "message": "OK", "new_commit": "1234567"}
            status, res_post = self._request("POST", "/api/system/apply-update")
            self.assertEqual(status, 200)
            self.assertTrue(res_post.get("success"))

    def test_upload_background_endpoint(self):
        # 1x1 transparent PNG en base64
        tiny_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        status, res = self._request("POST", "/api/upload/background", {"image": tiny_png_b64})
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertIn("/assets/custom-background.png", res.get("url"))
        self.assertIn("custom-background.png", res.get("bg_value"))

        # Vérifier que le réglage a été mis à jour en base
        status, data = self._request("GET", "/api/data")
        self.assertEqual(status, 200)
        self.assertIn("custom-background.png", data["settings"]["main_background"])

    def test_upload_folder_background_endpoint(self):
        tiny_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        # Upload d'image avec scope 'folder'
        status, res = self._request("POST", "/api/upload/background", {
            "image": tiny_png_b64,
            "scope": "folder",
            "folder_id": 42
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertIn("folder-bg-42", res.get("url"))
        self.assertIn("folder-bg-42", res.get("bg_value"))

        # Vérifier que le réglage global main_background n'a PAS été écrasé
        status, data = self._request("GET", "/api/data")
        self.assertEqual(status, 200)
        main_bg = data["settings"].get("main_background", "")
        self.assertNotIn("folder-bg-42", main_bg)

    def test_discord_test_endpoint(self):
        from unittest.mock import patch

        # 1. Sans URL et sans rien en base -> 400
        status, res = self._request("POST", "/api/discord/test", {"webhook_url": ""})
        self.assertEqual(status, 400)
        self.assertFalse(res.get("success"))

        # 2. URL non-discord invalide -> 400
        status, res = self._request("POST", "/api/discord/test", {"webhook_url": "https://evil.com/webhook"})
        self.assertEqual(status, 400)
        self.assertFalse(res.get("success"))

        # 3. Test avec URL valide mockée
        valid_webhook = "https://discord.com/api/webhooks/1234567890/tokenABC"
        with patch("backend.handlers.send_test_message") as mock_send:
            mock_send.return_value = (True, "Message envoyé")
            status, res = self._request("POST", "/api/discord/test", {
                "webhook_url": valid_webhook,
                "author_name": "Hugo"
            })
            self.assertEqual(status, 200)
            self.assertTrue(res.get("success"))

        # 4. Test avec webhook sauvegardé en base quand la requête envoie '••••'
        status, _ = self._request("PUT", "/api/settings", {"discord_webhook_url": valid_webhook})
        self.assertEqual(status, 200)

        with patch("backend.handlers.send_test_message") as mock_send:
            mock_send.return_value = (True, "Message envoyé")
            status, res = self._request("POST", "/api/discord/test", {
                "webhook_url": "••••ABC",
                "use_saved": True
            })
            self.assertEqual(status, 200)
            self.assertTrue(res.get("success"))
            mock_send.assert_called_with(valid_webhook, author_name="Hugo")

    def test_salon_endpoints(self):
        # 1. GET /api/salons
        status, salons = self._request("GET", "/api/salons")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(salons), 1)

        # 2. POST /api/salons
        status, new_salon = self._request("POST", "/api/salons", {
            "name": "Equipe Dev",
            "icon": "terminal",
            "color": "#3b82f6"
        })
        self.assertEqual(status, 201)
        salon_id = new_salon["id"]

        # 3. PUT /api/salons/<id>
        status, updated = self._request("PUT", f"/api/salons/{salon_id}", {
            "name": "Equipe Dev Core"
        })
        self.assertEqual(status, 200)
        self.assertEqual(updated["name"], "Equipe Dev Core")

        # 4. GET /api/salons/<id>/export
        status, exp = self._request("GET", f"/api/salons/{salon_id}/export")
        self.assertEqual(status, 200)
        self.assertEqual(exp["scope"], "salon")

        # 5. POST /api/salons/import
        status, imp = self._request("POST", "/api/salons/import", exp)
        self.assertEqual(status, 201)
        self.assertEqual(imp["name"], "Equipe Dev Core")

        # 6. DELETE /api/salons/<id>
        status, del_res = self._request("DELETE", f"/api/salons/{salon_id}")
        self.assertEqual(status, 200)
        self.assertTrue(del_res["success"])

        status, del_imp = self._request("DELETE", f"/api/salons/{imp['id']}")
        self.assertEqual(status, 200)

if __name__ == "__main__":
    unittest.main()

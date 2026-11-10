"""
Tests de sécurité complets pour valider la résolution de toutes les vulnérabilités identifiées.
Couvre : Authentification, CORS / Anti-CSRF, Restrictions réseau sur routes d'admin,
Masquage de secrets Discord, Protection contre les injections XSS/CSS et limitation des payloads.
"""

import hmac
import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

from backend.database import init_db
from backend.handlers import TodoRequestHandler
from backend.services import TodoService, _safe_color, _safe_bg_type


class SecurityTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "test_security.db")
        init_db(cls.db_path)

        cls.secret_token = "MonJetonUltraSecret123"

        # Serveur de test avec token activé pour valider l'authentification
        class AuthHandler(TodoRequestHandler):
            db_path = cls.db_path
            api_token = cls.secret_token

        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), AuthHandler)
        cls.port = cls.httpd.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.temp_dir.cleanup()

    def _request(self, method, path, data=None, headers=None):
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                resp_headers = resp.headers
                raw = resp.read().decode("utf-8")
                try:
                    content = json.loads(raw)
                except Exception:
                    content = raw
                return status, content, resp_headers
        except urllib.error.HTTPError as e:
            resp_headers = e.headers
            try:
                content = json.loads(e.read().decode("utf-8"))
            except Exception:
                content = None
            finally:
                e.close()
            return e.code, content, resp_headers

    # ------------------------------------------------------------------------
    # 🔴 FAILLE 1 : Authentification par jeton
    # ------------------------------------------------------------------------

    def test_auth_missing_token_returns_401(self):
        """Une requête API sans jeton sur un serveur protégé doit renvoyer 401."""
        status, content, _ = self._request("GET", "/api/data")
        self.assertEqual(status, 401)
        self.assertIn("error", content)

    def test_auth_invalid_token_returns_401(self):
        """Une requête avec un mauvais jeton doit renvoyer 401."""
        headers = {"Authorization": "Bearer MauvaisToken"}
        status, content, _ = self._request("GET", "/api/data", headers=headers)
        self.assertEqual(status, 401)

    def test_auth_valid_token_returns_200(self):
        """Une requête avec le bon jeton Bearer doit être acceptée (200)."""
        headers = {"Authorization": f"Bearer {self.secret_token}"}
        status, content, _ = self._request("GET", "/api/data", headers=headers)
        self.assertEqual(status, 200)
        self.assertIn("folders", content)

    # ------------------------------------------------------------------------
    # 🔴 FAILLE 2 : CORS et Protection Anti-CSRF / Origin Validation
    # ------------------------------------------------------------------------

    def test_cors_no_wildcard_for_unknown_origin(self):
        """Un site tiers malveillant ne doit jamais recevoir Access-Control-Allow-Origin: *"""
        headers = {
            "Authorization": f"Bearer {self.secret_token}",
            "Origin": "http://evil-site.com"
        }
        status, content, resp_headers = self._request("GET", "/api/data", headers=headers)
        self.assertNotEqual(resp_headers.get("Access-Control-Allow-Origin"), "*")
        self.assertNotEqual(resp_headers.get("Access-Control-Allow-Origin"), "http://evil-site.com")

    def test_cors_mutation_rejected_from_unauthorized_origin(self):
        """Toute mutation (POST/PUT/DELETE) émise avec un Origin non autorisé doit être bloquée en 403."""
        headers = {
            "Authorization": f"Bearer {self.secret_token}",
            "Origin": "http://malicious-website.org"
        }
        status, content, _ = self._request("POST", "/api/tasks", {"title": "XSRF Task"}, headers=headers)
        self.assertEqual(status, 403)
        self.assertIn("Origine non autorisée", content.get("error", ""))

    def test_cors_preflight_rejected_for_unauthorized_origin(self):
        """Une requête pre-flight OPTIONS d'une origine non autorisée doit renvoyer 403."""
        headers = {"Origin": "http://attacker.com"}
        status, _, resp_headers = self._request("OPTIONS", "/api/tasks", headers=headers)
        self.assertEqual(status, 403)

    def test_cors_allowed_for_legitimate_origin(self):
        """Une requête émise depuis la même application locale doit renvoyer l'en-tête CORS spécifique."""
        legit_origin = f"http://127.0.0.1:{self.port}"
        headers = {
            "Authorization": f"Bearer {self.secret_token}",
            "Origin": legit_origin
        }
        status, content, resp_headers = self._request("GET", "/api/data", headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(resp_headers.get("Access-Control-Allow-Origin"), legit_origin)

    # ------------------------------------------------------------------------
    # 🔴 FAILLE 3 : Routes d'administration restreintes à l'hôte local
    # ------------------------------------------------------------------------

    def test_admin_routes_blocked_for_remote_client_ip(self):
        """Les routes sensibles (/api/storage/*, /api/sync/status) doivent refuser les IP distantes (403)."""
        handler = TodoRequestHandler.__new__(TodoRequestHandler)
        handler.client_address = ("192.168.1.55", 54321)
        self.assertFalse(handler._is_local_client())

        handler.client_address = ("127.0.0.1", 12345)
        self.assertTrue(handler._is_local_client())

        handler.client_address = ("::1", 12345)
        self.assertTrue(handler._is_local_client())

    # ------------------------------------------------------------------------
    # 🟠 FAILLE 4 : Masquage et protection des Webhooks Discord
    # ------------------------------------------------------------------------

    def test_discord_webhook_url_masked_in_get_data(self):
        """L'URL complète du webhook Discord ne doit jamais fuiter dans /api/data ni dans l'export."""
        service = TodoService(self.db_path)
        real_webhook = "https://discord.com/api/webhooks/9876543210/abcdefsecretkeyxyz"
        service.update_settings({"discord_webhook_url": real_webhook})

        data = service.get_all_data()
        returned_url = data["settings"].get("discord_webhook_url")
        self.assertNotEqual(returned_url, real_webhook)
        self.assertTrue(returned_url.startswith("••••"))
        self.assertTrue(returned_url.endswith("yxyz"))
        self.assertTrue(data["settings"].get("discord_webhook_configured"))

        # Vérifier que le backup exporte aussi la valeur masquée
        backup = service.export_backup()
        self.assertNotEqual(backup["data"]["settings"].get("discord_webhook_url"), real_webhook)

    def test_discord_webhook_not_overwritten_by_masked_value(self):
        """Renvoyer une valeur masquée commençant par •••• ne doit pas écraser l'URL secrète en base."""
        service = TodoService(self.db_path)
        real_webhook = "https://discord.com/api/webhooks/9876543210/mysecrettoken"
        service.update_settings({"discord_webhook_url": real_webhook})

        # Simuler une mise à jour des réglages où le frontend renvoie la valeur masquée
        service.update_settings({
            "discord_webhook_url": "••••oken",
            "discord_author_name": "AntigravityBot"
        })

        # Vérifier en base directement que la vraie URL est restée intacte
        conn = service._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'discord_webhook_url'")
        val_in_db = cursor.fetchone()["value"]
        conn.close()

        self.assertEqual(val_in_db, real_webhook)

    # ------------------------------------------------------------------------
    # 🟠 FAILLE 5 : Validation stricte des couleurs et XSS / CSS Injection
    # ------------------------------------------------------------------------

    def test_safe_color_rejects_xss_and_css_injections(self):
        """Les tentatives d'injection HTML/CSS dans le champ couleur doivent être neutralisées."""
        # Tentatives XSS
        self.assertEqual(_safe_color('"><script>alert(1)</script>'), "#6366f1")
        self.assertEqual(_safe_color('"><svg onload=alert(1)>'), "#6366f1")
        self.assertEqual(_safe_color("red; background: url('evil.com')"), "#6366f1")
        self.assertEqual(_safe_color("javascript:alert(1)"), "#6366f1")

        # Couleurs valides acceptées
        self.assertEqual(_safe_color("#4f46e5"), "#4f46e5")
        self.assertEqual(_safe_color("#fff"), "#fff")
        self.assertEqual(_safe_color("#10B981"), "#10B981")
        self.assertEqual(_safe_color("#12345678"), "#12345678")

        # Longueurs non-CSS rejetées (5 chars, 7 chars ne sont pas des couleurs CSS)
        self.assertEqual(_safe_color("#12345"), "#6366f1")     # 5 hex chars → invalide
        self.assertEqual(_safe_color("#1234567"), "#6366f1")   # 7 hex chars → invalide

    def test_safe_bg_type_whitelist(self):
        """bg_type doit être restreint aux valeurs autorisées."""
        self.assertEqual(_safe_bg_type("solid"), "solid")
        self.assertEqual(_safe_bg_type("gradient"), "gradient")
        self.assertEqual(_safe_bg_type("default"), "default")
        self.assertEqual(_safe_bg_type("<script>evil()</script>"), "default")
        self.assertEqual(_safe_bg_type("unknown_type"), "default")

    def test_folder_creation_sanitizes_color_and_bg(self):
        """La création de dossier via TodoService applique l'assainissement de couleur."""
        service = TodoService(self.db_path)
        folder = service.create_folder({
            "name": "Dossier Test Sécurité",
            "color": '"><svg onload=alert(1)>',
            "bg_type": "invalid_type",
            "bg_color1": '"><img src=x onerror=alert(1)>'
        })
        self.assertEqual(folder["color"], "#4f46e5")
        self.assertEqual(folder["bg_type"], "default")
        self.assertEqual(folder["bg_color1"], "")

    # ------------------------------------------------------------------------
    # 🟡 FAILLE 6 : Non-divulgation des erreurs internes (pas de "details")
    # ------------------------------------------------------------------------

    def test_internal_server_error_does_not_leak_details(self):
        """En cas d'exception non gérée, la réponse 500 ne doit jamais divulguer de stack trace ou détails."""
        # On simule un crash en envoyant un id de suppression qui ferait planter le service
        original_delete = TodoService.delete_task

        def crashing_delete(service_self, task_id):
            raise RuntimeError("Database connection string: /home/secret/passwords.db")

        TodoService.delete_task = crashing_delete
        try:
            headers = {"Authorization": f"Bearer {self.secret_token}"}
            status, content, _ = self._request("DELETE", "/api/tasks/1", headers=headers)
            self.assertEqual(status, 500)
            self.assertEqual(content, {"error": "Erreur interne"})
            self.assertNotIn("details", content)
            self.assertNotIn("passwords", json.dumps(content))
        finally:
            TodoService.delete_task = original_delete

    # ------------------------------------------------------------------------
    # 🟡 FAILLE 9 : Protection contre les requêtes trop volumineuses (DoS 413)
    # ------------------------------------------------------------------------

    def test_payload_too_large_returns_413(self):
        """Une requête dépassant 5 Mo doit être rejetée avec le code HTTP 413."""
        # Test direct du handler sur un Content-Length excessif
        class MockServer:
            server_port = 4848

        class MockHandler(TodoRequestHandler):
            def __init__(self):
                self.server = MockServer()
                self.headers = {"Content-Length": str(6 * 1024 * 1024)}

        handler = MockHandler()
        with self.assertRaises(Exception) as ctx:
            handler.parse_body()
        self.assertIn("volumineux", str(ctx.exception).lower())

    # ------------------------------------------------------------------------
    # 🟠 FAILLE 10 : import_backup ne doit pas écraser les secrets masqués
    # ------------------------------------------------------------------------

    def test_import_backup_does_not_overwrite_secret_with_masked_value(self):
        """Importer un backup contenant une valeur masquée (••••) ne doit pas écraser le vrai secret en base."""
        service = TodoService(self.db_path)
        real_webhook = "https://discord.com/api/webhooks/111222333/realSecretToken"
        service.update_settings({"discord_webhook_url": real_webhook})

        # Simuler un backup JSON issu d'une autre machine (valeur masquée dans le backup)
        fake_backup = {
            "folders": [],
            "tasks": [],
            "settings": {
                "discord_webhook_url": "••••oken",   # valeur masquée issue de get_all_data()
                "discord_author_name": "BackupBot"
            }
        }
        service.import_backup(fake_backup, mode="merge")

        # La vraie URL en base doit être INCHANGÉE
        conn = service._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'discord_webhook_url'")
        val_in_db = cursor.fetchone()["value"]
        conn.close()

        self.assertEqual(val_in_db, real_webhook,
                         "import_backup a écrasé le vrai webhook par la valeur masquée !")

        # Les réglages non-sensibles doivent bien être importés
        data = service.get_all_data()
        self.assertEqual(data["settings"].get("discord_author_name"), "BackupBot")


if __name__ == "__main__":
    unittest.main()

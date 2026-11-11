import unittest
from unittest.mock import patch, MagicMock
from backend.discord import (
    is_valid_discord_webhook,
    send_discord_payload,
    send_test_message,
    notify_task_created,
    notify_task_status_changed,
    notify_task_deleted,
    notify_folder_created
)


class TestDiscordIntegration(unittest.TestCase):
    def test_webhook_url_validation(self):
        # Valid URLs
        valid_url = "https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz"
        self.assertTrue(is_valid_discord_webhook(valid_url))
        self.assertTrue(is_valid_discord_webhook("https://discordapp.com/api/webhooks/123/token"))
        self.assertTrue(is_valid_discord_webhook("https://canary.discord.com/api/webhooks/123/token"))

        # Invalid URLs (SSRF protection)
        self.assertFalse(is_valid_discord_webhook(""))
        self.assertFalse(is_valid_discord_webhook(None))
        self.assertFalse(is_valid_discord_webhook("http://discord.com/api/webhooks/123/abc"))  # Non-HTTPS
        self.assertFalse(is_valid_discord_webhook("https://evil.com/api/webhooks/123/abc"))
        self.assertFalse(is_valid_discord_webhook("https://discord.com/other/path"))
        self.assertFalse(is_valid_discord_webhook("file:///etc/passwd"))

    @patch("backend.discord.urllib.request.urlopen")
    def test_send_test_message_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        ok, msg = send_test_message(
            "https://discord.com/api/webhooks/12345/abcdef",
            author_name="Hugo"
        )
        self.assertTrue(ok)
        self.assertIn("Succès", msg)

    def test_send_test_message_invalid_url(self):
        ok, msg = send_test_message("https://evil.com/hook")
        self.assertFalse(ok)
        self.assertIn("non valide", msg)

    @patch("backend.discord.send_discord_payload")
    def test_notify_helpers(self, mock_send):
        webhook_url = "https://discord.com/api/webhooks/123/token"

        # Task created
        notify_task_created(webhook_url, {"title": "Test task", "priority": "urgent"}, "Dev", "Hugo")
        self.assertTrue(mock_send.called)
        payload = mock_send.call_args[0][1]
        self.assertEqual(payload["username"], "ToDoList")
        self.assertEqual(payload["embeds"][0]["title"], "📝 Nouvelle tâche créée")

        # Task completed
        notify_task_status_changed(webhook_url, {"title": "Test task", "completed": 1}, "Dev", "Hugo")
        payload = mock_send.call_args[0][1]
        self.assertEqual(payload["embeds"][0]["title"], "✅ Tâche terminée !")

        # Task reopened
        notify_task_status_changed(webhook_url, {"title": "Test task", "completed": 0}, "Dev", "Hugo")
        payload = mock_send.call_args[0][1]
        self.assertEqual(payload["embeds"][0]["title"], "🔄 Tâche réouverte")

        # Task deleted
        notify_task_deleted(webhook_url, "Tâche à supprimer", "Dev", "Hugo")
        payload = mock_send.call_args[0][1]
        self.assertEqual(payload["embeds"][0]["title"], "🗑️ Tâche supprimée")

        # Folder created
        notify_folder_created(webhook_url, "Nouveau Projet", "Hugo")
        payload = mock_send.call_args[0][1]
        self.assertEqual(payload["embeds"][0]["title"], "📁 Nouveau dossier de projet")

    def test_salon_specific_discord_notification_routing(self):
        from backend.database import init_db
        from backend.services import TodoService
        import tempfile, shutil

        tmpdir = tempfile.mkdtemp()
        try:
            db_path = f"{tmpdir}/test_salon_discord.db"
            init_db(db_path=db_path)
            service = TodoService(db_path=db_path)

            # Créer un salon spécifique avec son propre webhook
            salon_hook = "https://discord.com/api/webhooks/9999/salonSpecificToken"
            s = service.create_salon({
                "name": "Equipe Alpha",
                "discord_webhook_url": salon_hook,
                "discord_enabled": 1,
                "discord_author_name": "Alice"
            })

            # Créer un dossier rattaché à ce salon
            f = service.create_folder({
                "name": "Dossier Alpha",
                "salon_id": s["id"]
            })

            with patch("backend.services.notify_task_created") as mock_notify:
                service.create_task({
                    "title": "Tâche pour Alpha",
                    "folder_id": f["id"],
                    "author": "Alice"
                })
                self.assertTrue(mock_notify.called)
                called_webhook = mock_notify.call_args[0][0]
                self.assertEqual(called_webhook, salon_hook)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)



if __name__ == "__main__":
    unittest.main()

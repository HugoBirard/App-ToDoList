"""
Tests unitaires pour le module de mise à jour automatique (backend/updater.py).
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from backend.updater import check_for_updates, apply_update


class UpdaterTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_check_for_updates_non_git_directory(self):
        with patch("backend.updater.BASE_DIR", self.temp_dir.name):
            res = check_for_updates()
            self.assertFalse(res["is_git"])
            self.assertFalse(res["update_available"])
            self.assertIn("hors Git", res["message"])

    def test_check_for_updates_up_to_date(self):
        res = check_for_updates()
        self.assertTrue(res["is_git"])
        self.assertIn("current_commit", res)
        self.assertIn("branch", res)

    @patch("subprocess.run")
    def test_check_for_updates_update_available(self, mock_run):
        # Simuler un retour Git indiquant 2 commits de retard
        def side_effect(cmd, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "rev-parse" in cmd and "--short" in cmd:
                m.stdout = "abc1234\n"
            elif "rev-parse" in cmd and "--abbrev-ref" in cmd:
                m.stdout = "main\n"
            elif "fetch" in cmd:
                m.stdout = ""
            elif "rev-list" in cmd:
                m.stdout = "2\n"
            elif "log" in cmd:
                m.stdout = "def5678|Nouveau thème cyberpunk\n9876abc|Correctif affichage\n"
            return m

        mock_run.side_effect = side_effect

        res = check_for_updates()
        self.assertTrue(res["is_git"])
        self.assertTrue(res["update_available"])
        self.assertEqual(res["behind_count"], 2)
        self.assertEqual(len(res["commits"]), 2)
        self.assertEqual(res["commits"][0]["hash"], "def5678")

    def test_apply_update_creates_sqlite_backup(self):
        db_path = os.path.join(self.temp_dir.name, "todolist.db")
        with open(db_path, "w", encoding="utf-8") as f:
            f.write("SQLITE_TEST_CONTENT")

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Mise à jour effectuée\n"
            mock_run.return_value = mock_proc

            res = apply_update(db_path=db_path)
            self.assertTrue(res["success"])
            self.assertTrue(res["backup_created"])

            # Vérifier que le fichier .pre-update.bak existe
            backup_path = f"{db_path}.pre-update.bak"
            self.assertTrue(os.path.exists(backup_path))
            with open(backup_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "SQLITE_TEST_CONTENT")

    def test_apply_update_non_git_directory(self):
        with patch("backend.updater.BASE_DIR", self.temp_dir.name):
            res = apply_update()
            self.assertFalse(res["success"])
            self.assertIn("pas depuis un dépôt Git", res["error"])


if __name__ == "__main__":
    unittest.main()

"""
Tests unitaires pour la base de données et les migrations SQLite.
"""

import os
import unittest
import tempfile
from backend.database import init_db, get_connection


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_todo.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_db_creates_tables(self):
        init_db(self.db_path)
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row["name"] for row in cursor.fetchall()}
        self.assertIn("folders", tables)
        self.assertIn("tasks", tables)
        self.assertIn("settings", tables)

        # Vérifier colonnes dossiers
        cursor.execute("PRAGMA table_info(folders)")
        f_cols = {row["name"] for row in cursor.fetchall()}
        self.assertIn("auto_reset_weekly", f_cols)
        self.assertIn("bg_type", f_cols)
        self.assertIn("bg_color1", f_cols)

        # Vérifier colonnes tâches
        cursor.execute("PRAGMA table_info(tasks)")
        t_cols = {row["name"] for row in cursor.fetchall()}
        self.assertIn("has_progress", t_cols)
        self.assertIn("progress", t_cols)

        conn.close()

    def test_seed_default_data_illustrates_checkbox_and_progress_modes(self):
        """Vérifie que les données d'exemple initiales intègrent bien le mode case à cocher et la barre d'avancement."""
        init_db(self.db_path)
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        # Dossier d'exemples présent
        cursor.execute("SELECT * FROM folders WHERE name LIKE '%Exemple%'")
        demo_folder = cursor.fetchone()
        self.assertIsNotNone(demo_folder, "Le dossier d'exemples doit être initialisé.")

        # Tâches associées
        cursor.execute("SELECT * FROM tasks WHERE folder_id = ?", (demo_folder["id"],))
        tasks = [dict(row) for row in cursor.fetchall()]
        self.assertGreaterEqual(len(tasks), 3, "Le dossier d'exemples doit comporter plusieurs tâches de démonstration.")

        # Vérifier la présence d'au moins une tâche simple avec case à cocher (has_progress = 0)
        checkbox_tasks = [t for t in tasks if not t["has_progress"]]
        self.assertTrue(len(checkbox_tasks) > 0, "Doit comporter au moins une tâche avec case à cocher standard.")

        # Vérifier la présence d'au moins une tâche avec barre d'avancement interactive (has_progress = 1)
        progress_tasks = [t for t in tasks if t["has_progress"]]
        self.assertTrue(len(progress_tasks) > 0, "Doit comporter au moins une tâche avec barre d'avancement.")

        conn.close()


if __name__ == "__main__":
    unittest.main()

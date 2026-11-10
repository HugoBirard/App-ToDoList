"""
Tests unitaires pour TodoService (logique métier, progression 100%, resets hebdo).
"""

import os
import unittest
import tempfile
from datetime import datetime, timedelta
from backend.database import init_db
from backend.services import TodoService


class ServicesTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_services.db")
        init_db(self.db_path)
        self.service = TodoService(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_progress_reaches_100_percent_completes_task(self):
        task = self.service.create_task({
            "title": "Tâche test progression",
            "has_progress": 1,
            "progress": 50
        })
        self.assertEqual(task["completed"], 0)
        self.assertEqual(task["progress"], 50)

        # Passe à 100% -> complétée
        updated = self.service.update_task(task["id"], {"progress": 100})
        self.assertEqual(updated["completed"], 1)
        self.assertEqual(updated["progress"], 100)

        # Redescend à 70% -> à faire
        updated_down = self.service.update_task(task["id"], {"progress": 70})
        self.assertEqual(updated_down["completed"], 0)
        self.assertEqual(updated_down["progress"], 70)

    def test_weekly_reset_resets_tasks_after_7_days(self):
        folder = self.service.create_folder({
            "name": "Hebdo Routine",
            "auto_reset_weekly": 1
        })
        task = self.service.create_task({
            "title": "Routine terminée",
            "folder_id": folder["id"],
            "completed": 1,
            "has_progress": 1,
            "progress": 100
        })

        # Simuler 8 jours d'ancienneté
        old_time = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
        conn = self.service._conn()
        conn.execute("UPDATE folders SET last_reset_at = ? WHERE id = ?", (old_time, folder["id"]))
        conn.commit()
        conn.close()

        # check_weekly_resets doit réinitialiser la tâche
        self.service.check_weekly_resets()

        data = self.service.get_all_data()
        reset_task = next(t for t in data["tasks"] if t["id"] == task["id"])
        self.assertEqual(reset_task["completed"], 0)
        self.assertEqual(reset_task["progress"], 0)

    def test_create_folder_defaults_to_vector_icon_identifier(self):
        folder = self.service.create_folder({"name": "Test Icon"})
        self.assertEqual(folder["icon"], "folder")

    def test_storage_info_and_change_path(self):
        info = self.service.get_storage_info()
        self.assertTrue(info["file_exists"])
        self.assertIn("current_db_path", info)
        self.assertGreaterEqual(info["task_count"], 0)

        # Migration vers un autre fichier
        new_db = os.path.join(self.temp_dir.name, "shared_cloud", "todolist.db")
        res = self.service.change_storage_path(new_db, action="migrate")
        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(new_db))

        # Vérifier que les données sont bien dans la nouvelle base
        new_info = self.service.get_storage_info()
        self.assertEqual(os.path.abspath(new_info["current_db_path"]), os.path.abspath(new_db))

        # Reset vers emplacement par défaut
        res_reset = self.service.change_storage_path(None, action="reset")
        self.assertTrue(res_reset["success"])

    def test_export_and_import_backup(self):
        # Création de données
        folder = self.service.create_folder({"name": "Dossier Export"})
        self.service.create_task({"title": "Tâche Exportable", "folder_id": folder["id"]})

        backup = self.service.export_backup()
        self.assertEqual(backup["app"], "ToDoList")
        self.assertIn("folders", backup["data"])
        self.assertIn("tasks", backup["data"])

        # Test import en mode fusion
        imported_data = self.service.import_backup(backup, mode="merge")
        self.assertIn("folders", imported_data)
        self.assertIn("tasks", imported_data)

        # Test check_updates
        updates = self.service.check_updates()
        self.assertGreater(updates["last_modified"], 0)


if __name__ == "__main__":
    unittest.main()

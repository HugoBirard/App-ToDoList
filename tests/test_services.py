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

    def test_reorder_folders(self):
        f1 = self.service.create_folder({"name": "Dossier 1"})
        f2 = self.service.create_folder({"name": "Dossier 2"})
        f3 = self.service.create_folder({"name": "Dossier 3"})

        # Inverser l'ordre
        self.service.reorder_folders([f3["id"], f1["id"], f2["id"]])
        data = self.service.get_all_data()
        folders = [f for f in data["folders"] if f["id"] in (f1["id"], f2["id"], f3["id"])]
        self.assertEqual([f["id"] for f in folders], [f3["id"], f1["id"], f2["id"]])

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

    def test_folder_background_options(self):
        # Preset background
        f_preset = self.service.create_folder({
            "name": "Dossier Cyberpunk",
            "bg_type": "preset",
            "bg_color1": "cyberpunk"
        })
        self.assertEqual(f_preset["bg_type"], "preset")
        self.assertEqual(f_preset["bg_color1"], "cyberpunk")

        # Mise à jour avec un autre preset
        f_preset_up = self.service.update_folder(f_preset["id"], {
            "bg_type": "preset",
            "bg_color1": "street"
        })
        self.assertEqual(f_preset_up["bg_type"], "preset")
        self.assertEqual(f_preset_up["bg_color1"], "street")

        # Custom image background
        f_img = self.service.create_folder({
            "name": "Dossier Photo",
            "bg_type": "image",
            "bg_color1": "/assets/folder-bg-123.jpg"
        })
        self.assertEqual(f_img["bg_type"], "image")
        self.assertEqual(f_img["bg_color1"], "/assets/folder-bg-123.jpg")

    def test_salon_crud_and_export_import(self):
        # 1. Obtenir les salons initiaux (doit avoir au moins 'Personnel')
        salons = self.service.get_salons()
        self.assertGreaterEqual(len(salons), 1)
        self.assertEqual(salons[0]["name"], "Personnel")

        # 2. Créer un nouveau salon "Groupe Projet"
        created = self.service.create_salon({
            "name": "Groupe Projet",
            "icon": "users",
            "color": "#10b981",
            "description": "Salon pour le travail en équipe",
            "discord_webhook_url": "https://discord.com/api/webhooks/123/abc",
            "discord_enabled": 1,
            "discord_author_name": "Hugo"
        })
        self.assertIsNotNone(created)
        self.assertEqual(created["name"], "Groupe Projet")
        self.assertTrue(created["discord_webhook_configured"])
        self.assertTrue(created["discord_webhook_url"].startswith("••••"))

        # 3. Créer un dossier lié à ce salon
        f = self.service.create_folder({
            "name": "Dossier Equipe",
            "salon_id": created["id"]
        })
        self.assertEqual(f["salon_id"], created["id"])

        # 4. Créer une tâche dans ce dossier
        t = self.service.create_task({
            "title": "Tâche de groupe",
            "folder_id": f["id"]
        })
        self.assertIsNotNone(t)

        # 5. Exporter uniquement ce salon
        exp = self.service.export_salon(created["id"])
        self.assertEqual(exp["scope"], "salon")
        self.assertEqual(exp["salon"]["name"], "Groupe Projet")
        self.assertEqual(len(exp["folders"]), 1)
        self.assertEqual(len(exp["tasks"]), 1)
        # Vérifier que le secret webhook n'a pas fuité dans l'export
        self.assertNotIn("discord_webhook_url", exp["salon"])

        # 6. Importer ce salon comme nouveau salon
        imported = self.service.import_salon(exp)
        self.assertIsNotNone(imported)
        self.assertNotEqual(imported["id"], created["id"])
        self.assertEqual(imported["name"], "Groupe Projet")

        # 7. Mettre à jour le salon
        up = self.service.update_salon(created["id"], {"name": "Groupe Projet V2"})
        self.assertEqual(up["name"], "Groupe Projet V2")

        # 8. Supprimer le salon
        ok, _ = self.service.delete_salon(created["id"])
        self.assertTrue(ok)
        self.assertIsNone(self.service.get_salon(created["id"]))

        # Solid background
        f_solid = self.service.create_folder({
            "name": "Dossier Uni",
            "bg_type": "solid",
            "bg_color1": "#090A0D"
        })
        self.assertEqual(f_solid["bg_type"], "solid")
        self.assertEqual(f_solid["bg_color1"], "#090A0D")

        # Gradient background
        f_grad = self.service.create_folder({
            "name": "Dossier Dégradé",
            "bg_type": "gradient",
            "bg_color1": "#112233",
            "bg_color2": "#445566",
            "bg_angle": 90
        })
        self.assertEqual(f_grad["bg_type"], "gradient")
        self.assertEqual(f_grad["bg_color1"], "#112233")
        self.assertEqual(f_grad["bg_color2"], "#445566")
        self.assertEqual(f_grad["bg_angle"], 90)

    def test_salon_presence_and_live_sync_versioning(self):
        """Vérifie le comptage de présence des membres en ligne et l'incrémentation de version pour la synchro en direct."""
        salon = self.service.create_salon({"name": "Salon Partagé Live"})
        salon_id = salon["id"]

        # Initialement aucun membre actif
        self.assertEqual(self.service.get_active_member_count(salon_id), 0)

        # Enregistrement de 2 clients
        self.service.record_presence(salon_id, "user_pc_1", "Alice")
        self.service.record_presence(salon_id, "user_pc_2", "Bob")
        self.assertEqual(self.service.get_active_member_count(salon_id), 2)

        # Un client qui change de salon bascule sa présence
        salon2 = self.service.create_salon({"name": "Deuxième Salon"})
        self.service.record_presence(salon2["id"], "user_pc_1", "Alice")
        self.assertEqual(self.service.get_active_member_count(salon_id), 1)
        self.assertEqual(self.service.get_active_member_count(salon2["id"]), 1)

        # Expiration après timeout
        self.assertEqual(self.service.get_active_member_count(salon_id, timeout=-1.0), 0)

        # Vérification des versions de salon lors des modifications
        v_initial = self.service.get_salon_version(salon_id)
        folder = self.service.create_folder({"name": "Dossier Test", "salon_id": salon_id})
        self.assertGreater(self.service.get_salon_version(salon_id), v_initial)

        v_after_folder = self.service.get_salon_version(salon_id)
        task = self.service.create_task({"title": "Tâche Live", "folder_id": folder["id"]})
        self.assertGreater(self.service.get_salon_version(salon_id), v_after_folder)

        v_after_task = self.service.get_salon_version(salon_id)
        self.service.update_task(task["id"], {"completed": True})
        self.assertGreater(self.service.get_salon_version(salon_id), v_after_task)

        v_after_update = self.service.get_salon_version(salon_id)
        self.service.delete_task(task["id"])
        self.assertGreater(self.service.get_salon_version(salon_id), v_after_update)


if __name__ == "__main__":
    unittest.main()

"""
Service métier de gestion des dossiers, tâches et réglages.
Contient toute la logique métier (réinitialisation hebdomadaire, calcul de complétion, etc.).
"""

import os
import shutil
from datetime import datetime, timedelta
from .config import DEFAULT_DB_PATH, get_current_db_path, load_local_config, save_local_config
from .database import get_connection, init_db
from .discord import notify_task_created, notify_task_status_changed, notify_task_deleted, notify_folder_created


def _safe_int(val, default=0, min_val=None, max_val=None):
    """Convertit de manière sécurisée en entier sans lever d'exception."""
    try:
        res = int(val)
    except (ValueError, TypeError, OverflowError):
        res = default
    if min_val is not None and res < min_val:
        res = min_val
    if max_val is not None and res > max_val:
        res = max_val
    return res


class TodoService:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _conn(self):
        if self.db_path:
            return get_connection(self.db_path)
        return get_connection()

    def get_all_data(self):
        """Récupère l'ensemble des données après avoir vérifié les réinitialisations hebdomadaires."""
        conn = self._conn()
        self.check_weekly_resets(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM folders ORDER BY id ASC")
        folders = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM tasks ORDER BY completed ASC, id DESC")
        tasks = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT key, value FROM settings")
        settings = {row["key"]: row["value"] for row in cursor.fetchall()}

        conn.close()
        return {"folders": folders, "tasks": tasks, "settings": settings}

    def check_weekly_resets(self, conn=None):
        """Vérifie si 7 jours se sont écoulés pour les dossiers hebdomadaires et remet leurs tâches à zéro."""
        own_conn = False
        if conn is None:
            conn = self._conn()
            own_conn = True

        cursor = conn.cursor()
        cursor.execute("SELECT id, name, last_reset_at FROM folders WHERE auto_reset_weekly = 1")
        folders = cursor.fetchall()
        now = datetime.now()

        for f in folders:
            folder_id = f["id"]
            last_reset = f["last_reset_at"]
            should_reset = False

            if not last_reset:
                should_reset = True
            else:
                try:
                    date_str = str(last_reset)[:19].replace("T", " ")
                    last_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    if (now - last_dt) >= timedelta(days=7):
                        should_reset = True
                except Exception:
                    should_reset = True

            if should_reset:
                cursor.execute("""
                    UPDATE tasks 
                    SET completed = 0, progress = 0, completed_at = NULL 
                    WHERE folder_id = ?
                """, (folder_id,))
                cursor.execute("""
                    UPDATE folders 
                    SET last_reset_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (folder_id,))

        conn.commit()
        if own_conn:
            conn.close()

    def _trigger_discord(self, action_type, **kwargs):
        """Déclenche les notifications Discord de façon asynchrone si le service est activé."""
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings WHERE key LIKE 'discord_%'")
            settings = {row["key"]: row["value"] for row in cursor.fetchall()}
            conn.close()

            if str(settings.get("discord_enabled", "0")) != "1":
                return

            webhook_url = settings.get("discord_webhook_url", "").strip()
            if not webhook_url:
                return

            author = kwargs.get("author") or settings.get("discord_author_name") or "Équipe"

            if action_type == "task_created" and str(settings.get("discord_notify_created", "1")) == "1":
                notify_task_created(webhook_url, kwargs.get("task", {}), kwargs.get("folder_name", "Général"), author=author)
            elif action_type == "task_status" and str(settings.get("discord_notify_completed", "1")) == "1":
                notify_task_status_changed(webhook_url, kwargs.get("task", {}), kwargs.get("folder_name", "Général"), author=author)
            elif action_type == "task_deleted" and str(settings.get("discord_notify_deleted", "1")) == "1":
                notify_task_deleted(webhook_url, kwargs.get("task_title", "Tâche"), kwargs.get("folder_name", "Général"), author=author)
            elif action_type == "folder_created" and str(settings.get("discord_notify_folder", "1")) == "1":
                notify_folder_created(webhook_url, kwargs.get("folder_name", "Dossier"), author=author)
        except Exception:
            pass

    # --- Dossiers ---

    def create_folder(self, data):
        conn = self._conn()
        cursor = conn.cursor()
        name = str(data.get("name") or "Nouveau dossier").strip()[:100]
        icon = str(data.get("icon") or "folder")[:50]
        color = str(data.get("color") or "#4f46e5")[:20]
        auto_reset_weekly = 1 if data.get("auto_reset_weekly") else 0
        bg_type = str(data.get("bg_type", "default"))[:30]
        bg_color1 = str(data.get("bg_color1", ""))[:50]
        bg_color2 = str(data.get("bg_color2", ""))[:50]
        bg_angle = _safe_int(data.get("bg_angle", 135), default=135, min_val=0, max_val=360)

        cursor.execute(
            """INSERT INTO folders (name, icon, color, auto_reset_weekly, bg_type, bg_color1, bg_color2, bg_angle) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, icon, color, auto_reset_weekly, bg_type, bg_color1, bg_color2, bg_angle)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM folders WHERE id = ?", (new_id,))
        created = dict(cursor.fetchone())
        conn.close()
        self._trigger_discord("folder_created", folder_name=created.get("name", "Nouveau dossier"), author=data.get("author"))
        return created

    def update_folder(self, folder_id, data):
        conn = self._conn()
        cursor = conn.cursor()
        fields = []
        values = []

        if "name" in data:
            fields.append("name = ?")
            values.append(str(data["name"]).strip()[:100])
        if "icon" in data:
            fields.append("icon = ?")
            values.append(str(data["icon"])[:50])
        if "color" in data:
            fields.append("color = ?")
            values.append(str(data["color"])[:20])
        if "auto_reset_weekly" in data:
            fields.append("auto_reset_weekly = ?")
            values.append(1 if data["auto_reset_weekly"] else 0)
        if "bg_type" in data:
            fields.append("bg_type = ?")
            values.append(str(data["bg_type"])[:30])
        if "bg_color1" in data:
            fields.append("bg_color1 = ?")
            values.append(str(data["bg_color1"])[:50])
        if "bg_color2" in data:
            fields.append("bg_color2 = ?")
            values.append(str(data["bg_color2"])[:50])
        if "bg_angle" in data:
            fields.append("bg_angle = ?")
            values.append(_safe_int(data["bg_angle"], default=135, min_val=0, max_val=360))

        if fields:
            values.append(folder_id)
            cursor.execute(f"UPDATE folders SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

        cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_folder(self, folder_id):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE folder_id = ?", (folder_id,))
        cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        conn.commit()
        conn.close()
        return True

    def reset_folder_tasks(self, folder_id):
        """Réinitialise immédiatement les tâches d'un dossier (non faites, 0%)."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks 
            SET completed = 0, progress = 0, completed_at = NULL 
            WHERE folder_id = ?
        """, (folder_id,))
        cursor.execute("""
            UPDATE folders 
            SET last_reset_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (folder_id,))
        conn.commit()
        conn.close()
        return True

    # --- Tâches ---

    def create_task(self, data):
        conn = self._conn()
        cursor = conn.cursor()
        title = str(data.get("title") or "").strip()[:500]
        folder_id = data.get("folder_id")

        # Validation sécurisée de folder_id : si le dossier n'existe pas, on sélectionne le premier dossier valide
        if folder_id is not None:
            cursor.execute("SELECT id FROM folders WHERE id = ?", (folder_id,))
            if not cursor.fetchone():
                cursor.execute("SELECT id FROM folders ORDER BY id ASC LIMIT 1")
                first_f = cursor.fetchone()
                folder_id = first_f["id"] if first_f else None
        else:
            cursor.execute("SELECT id FROM folders ORDER BY id ASC LIMIT 1")
            first_f = cursor.fetchone()
            folder_id = first_f["id"] if first_f else None
        priority = str(data.get("priority", "normal"))[:20]
        due_date = data.get("due_date", None)
        if due_date:
            due_date = str(due_date)[:30]
        has_progress = 1 if data.get("has_progress") else 0
        progress = _safe_int(data.get("progress", 0), default=0, min_val=0, max_val=100)

        # Règle des 100%
        completed = 1 if (has_progress and progress >= 100) else (1 if data.get("completed") else 0)

        cursor.execute(
            """INSERT INTO tasks (folder_id, title, completed, has_progress, progress, priority, due_date) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (folder_id, title, completed, has_progress, progress, priority, due_date)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (new_id,))
        created = dict(cursor.fetchone())
        
        folder_name = "Général"
        if folder_id:
            cursor.execute("SELECT name FROM folders WHERE id = ?", (folder_id,))
            f_row = cursor.fetchone()
            if f_row:
                folder_name = f_row["name"]
        conn.close()
        self._trigger_discord("task_created", task=created, folder_name=folder_name, author=data.get("author"))
        return created

    def update_task(self, task_id, data):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            return None

        fields = []
        values = []

        if "title" in data:
            fields.append("title = ?")
            values.append(str(data["title"]).strip()[:500])

        has_progress = data.get("has_progress", existing["has_progress"])
        if "has_progress" in data:
            fields.append("has_progress = ?")
            values.append(1 if has_progress else 0)

        # Règle de cohérence progression <-> complétion
        if "progress" in data:
            prog = _safe_int(data["progress"], default=0, min_val=0, max_val=100)
            fields.append("progress = ?")
            values.append(prog)
            if prog >= 100:
                fields.append("completed = 1")
                fields.append("completed_at = CURRENT_TIMESTAMP")
            else:
                fields.append("completed = 0")
                fields.append("completed_at = NULL")

        elif "completed" in data:
            completed_val = 1 if data["completed"] else 0
            fields.append("completed = ?")
            values.append(completed_val)
            if completed_val == 1:
                fields.append("completed_at = CURRENT_TIMESTAMP")
                if has_progress:
                    fields.append("progress = 100")
            else:
                fields.append("completed_at = NULL")
                if has_progress:
                    fields.append("progress = 0")

        if "folder_id" in data:
            fid = data["folder_id"]
            if fid is not None:
                cursor.execute("SELECT id FROM folders WHERE id = ?", (fid,))
                if not cursor.fetchone():
                    cursor.execute("SELECT id FROM folders ORDER BY id ASC LIMIT 1")
                    first_f = cursor.fetchone()
                    fid = first_f["id"] if first_f else None
            fields.append("folder_id = ?")
            values.append(fid)
        if "priority" in data:
            fields.append("priority = ?")
            values.append(str(data["priority"])[:20])
        if "due_date" in data:
            fields.append("due_date = ?")
            values.append(str(data["due_date"])[:30] if data["due_date"] else None)

        if fields:
            values.append(task_id)
            cursor.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        
        status_changed = False
        if row and existing and ("completed" in data or "progress" in data):
            if existing["completed"] != row["completed"]:
                status_changed = True

        folder_name = "Général"
        if row and row["folder_id"]:
            cursor.execute("SELECT name FROM folders WHERE id = ?", (row["folder_id"],))
            f_row = cursor.fetchone()
            if f_row:
                folder_name = f_row["name"]

        conn.close()

        if status_changed and row:
            self._trigger_discord("task_status", task=dict(row), folder_name=folder_name, author=data.get("author"))

        return dict(row) if row else None

    def delete_task(self, task_id, author=None):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT title, folder_id FROM tasks WHERE id = ?", (task_id,))
        existing = cursor.fetchone()
        task_title = existing["title"] if existing else "Tâche"
        folder_name = "Général"
        if existing and existing["folder_id"]:
            cursor.execute("SELECT name FROM folders WHERE id = ?", (existing["folder_id"],))
            f_row = cursor.fetchone()
            if f_row:
                folder_name = f_row["name"]

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

        if existing:
            self._trigger_discord("task_deleted", task_title=task_title, folder_name=folder_name, author=author)

        return True

    def clear_completed(self, folder_id=None):
        conn = self._conn()
        cursor = conn.cursor()
        if folder_id is not None:
            cursor.execute("DELETE FROM tasks WHERE completed = 1 AND folder_id = ?", (folder_id,))
        else:
            cursor.execute("DELETE FROM tasks WHERE completed = 1")
        conn.commit()
        conn.close()
        return True

    # --- Réglages ---

    def update_settings(self, payload):
        conn = self._conn()
        cursor = conn.cursor()
        for k, v in payload.items():
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (str(k), str(v)))
        conn.commit()
        cursor.execute("SELECT key, value FROM settings")
        settings = {row["key"]: row["value"] for row in cursor.fetchall()}
        conn.close()
        return settings

    # --- Synchronisation & Multi-PC ---

    def get_active_db_path(self):
        """Retourne le chemin absolu de la base de données active."""
        return self.db_path or get_current_db_path()

    def get_storage_info(self):
        """Retourne les informations sur l'emplacement actuel de stockage."""
        active_path = self.get_active_db_path()
        file_exists = os.path.exists(active_path)
        file_size = os.path.getsize(active_path) if file_exists else 0
        last_modified = os.path.getmtime(active_path) if file_exists else 0

        task_count = 0
        folder_count = 0
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM folders")
            folder_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

        return {
            "current_db_path": active_path,
            "default_db_path": DEFAULT_DB_PATH,
            "is_custom": os.path.abspath(active_path) != os.path.abspath(DEFAULT_DB_PATH),
            "file_exists": file_exists,
            "file_size": file_size,
            "last_modified": last_modified,
            "task_count": task_count,
            "folder_count": folder_count
        }

    def change_storage_path(self, target_path, action="connect"):
        """Change l'emplacement de stockage de la base SQLite pour synchronisation multi-PC."""
        if action == "reset":
            cfg = load_local_config()
            cfg.pop("custom_db_path", None)
            save_local_config(cfg)
            self.db_path = None
            init_db(DEFAULT_DB_PATH)
            return {"success": True, "info": self.get_storage_info()}

        if not target_path or not isinstance(target_path, str) or not target_path.strip():
            raise ValueError("Le chemin cible est invalide ou vide.")

        target_path = os.path.abspath(os.path.expanduser(target_path.strip()))
        if os.path.isdir(target_path) or not target_path.endswith(".db"):
            target_path = os.path.join(target_path, "todolist.db")

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        current_path = self.get_active_db_path()

        if action == "migrate":
            if os.path.exists(current_path) and os.path.abspath(current_path) != os.path.abspath(target_path):
                # Checkpoint du WAL pour s'assurer que toutes les données sont bien dans le fichier principal
                try:
                    conn = self._conn()
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    conn.close()
                except Exception:
                    pass
                shutil.copy2(current_path, target_path)

        # Initialiser ou valider le schéma sur le nouvel emplacement
        init_db(target_path)

        # Sauvegarder la nouvelle configuration sur cette machine
        cfg = load_local_config()
        cfg["custom_db_path"] = target_path
        save_local_config(cfg)
        self.db_path = target_path

        return {"success": True, "info": self.get_storage_info()}

    def check_updates(self):
        """Vérifie rapidement si la base de données a été modifiée par un autre PC."""
        active_path = self.get_active_db_path()
        last_modified = os.path.getmtime(active_path) if os.path.exists(active_path) else 0
        task_count = 0
        folder_count = 0
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM folders")
            folder_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

        return {
            "last_modified": last_modified,
            "task_count": task_count,
            "folder_count": folder_count
        }

    def export_backup(self):
        """Exporte l'intégralité des données en dictionnaire JSON structuré."""
        data = self.get_all_data()
        return {
            "app": "ToDoList",
            "version": "1.0.0",
            "exported_at": datetime.now().isoformat(),
            "data": data
        }

    def import_backup(self, payload, mode="merge"):
        """Importe des données depuis un JSON avec option de fusion ou remplacement."""
        backup_data = payload.get("data", payload)
        folders = backup_data.get("folders", [])
        tasks = backup_data.get("tasks", [])
        settings = backup_data.get("settings", {})

        conn = self._conn()
        cursor = conn.cursor()

        if mode == "replace":
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM folders")

        # Map d'anciens folder_id vers nouveaux IDs si fusion
        folder_id_map = {}
        for f in folders:
            name = (f.get("name") or "Dossier importé").strip()[:100]
            icon = str(f.get("icon") or "folder")[:50]
            color = str(f.get("color") or "#4f46e5")[:20]
            auto_reset_weekly = 1 if f.get("auto_reset_weekly") else 0
            bg_type = str(f.get("bg_type", "default"))[:30]
            bg_color1 = str(f.get("bg_color1", ""))[:50]
            bg_color2 = str(f.get("bg_color2", ""))[:50]
            bg_angle = _safe_int(f.get("bg_angle", 135), default=135, min_val=0, max_val=360)

            # En mode fusion, si un dossier de même nom existe, le réutiliser
            existing_id = None
            if mode == "merge":
                cursor.execute("SELECT id FROM folders WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    existing_id = row["id"]

            if existing_id is not None:
                folder_id_map[f.get("id")] = existing_id
            else:
                cursor.execute(
                    """INSERT INTO folders (name, icon, color, auto_reset_weekly, bg_type, bg_color1, bg_color2, bg_angle) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, icon, color, auto_reset_weekly, bg_type, bg_color1, bg_color2, bg_angle)
                )
                new_fid = cursor.lastrowid
                folder_id_map[f.get("id")] = new_fid

        # Obtenir un premier dossier valide par défaut pour les tâches orphelines
        cursor.execute("SELECT id FROM folders ORDER BY id ASC LIMIT 1")
        first_row = cursor.fetchone()
        default_folder_id = first_row["id"] if first_row else None

        for t in tasks:
            title = str(t.get("title") or "").strip()[:500]
            if not title:
                continue

            old_fid = t.get("folder_id")
            new_fid = folder_id_map.get(old_fid, default_folder_id)
            completed = 1 if t.get("completed") else 0
            has_progress = 1 if t.get("has_progress") else 0
            progress = _safe_int(t.get("progress", 0), default=0, min_val=0, max_val=100)
            priority = str(t.get("priority", "normal"))[:20]
            due_date = str(t.get("due_date"))[:30] if t.get("due_date") else None

            # Si merge, vérifier si tâche identique existe déjà
            if mode == "merge":
                cursor.execute(
                    "SELECT id FROM tasks WHERE title = ? AND folder_id = ?",
                    (title, new_fid)
                )
                if cursor.fetchone():
                    continue

            cursor.execute(
                """INSERT INTO tasks (folder_id, title, completed, has_progress, progress, priority, due_date) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (new_fid, title, completed, has_progress, progress, priority, due_date)
            )

        # Réglages
        if isinstance(settings, dict):
            for k, v in settings.items():
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (str(k), str(v)))

        conn.commit()
        conn.close()
        return self.get_all_data()

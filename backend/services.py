"""
Service métier de gestion des dossiers, tâches et réglages.
Contient toute la logique métier (réinitialisation hebdomadaire, calcul de complétion, etc.).
"""

from datetime import datetime, timedelta
from .database import get_connection


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

    # --- Dossiers ---

    def create_folder(self, data):
        conn = self._conn()
        cursor = conn.cursor()
        name = (data.get("name") or "Nouveau dossier").strip()
        icon = data.get("icon") or "folder"
        color = data.get("color") or "#4f46e5"
        auto_reset_weekly = 1 if data.get("auto_reset_weekly") else 0
        bg_type = data.get("bg_type", "default")
        bg_color1 = data.get("bg_color1", "")
        bg_color2 = data.get("bg_color2", "")
        bg_angle = int(data.get("bg_angle", 135))

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
        return created

    def update_folder(self, folder_id, data):
        conn = self._conn()
        cursor = conn.cursor()
        fields = []
        values = []

        if "name" in data:
            fields.append("name = ?")
            values.append(data["name"].strip())
        if "icon" in data:
            fields.append("icon = ?")
            values.append(data["icon"])
        if "color" in data:
            fields.append("color = ?")
            values.append(data["color"])
        if "auto_reset_weekly" in data:
            fields.append("auto_reset_weekly = ?")
            values.append(1 if data["auto_reset_weekly"] else 0)
        if "bg_type" in data:
            fields.append("bg_type = ?")
            values.append(data["bg_type"])
        if "bg_color1" in data:
            fields.append("bg_color1 = ?")
            values.append(data["bg_color1"])
        if "bg_color2" in data:
            fields.append("bg_color2 = ?")
            values.append(data["bg_color2"])
        if "bg_angle" in data:
            fields.append("bg_angle = ?")
            values.append(int(data["bg_angle"]))

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
        title = (data.get("title") or "").strip()
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
        priority = data.get("priority", "normal")
        due_date = data.get("due_date", None)
        has_progress = 1 if data.get("has_progress") else 0
        progress = int(data.get("progress", 0))
        if progress < 0: progress = 0
        if progress > 100: progress = 100

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
        conn.close()
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
            values.append(data["title"].strip())

        has_progress = data.get("has_progress", existing["has_progress"])
        if "has_progress" in data:
            fields.append("has_progress = ?")
            values.append(1 if has_progress else 0)

        # Règle de cohérence progression <-> complétion
        if "progress" in data:
            prog = int(data["progress"])
            if prog < 0: prog = 0
            if prog > 100: prog = 100
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
            fields.append("folder_id = ?")
            values.append(data["folder_id"])
        if "priority" in data:
            fields.append("priority = ?")
            values.append(data["priority"])
        if "due_date" in data:
            fields.append("due_date = ?")
            values.append(data["due_date"])

        if fields:
            values.append(task_id)
            cursor.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_task(self, task_id):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
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

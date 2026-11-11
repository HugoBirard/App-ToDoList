"""
Service métier de gestion des dossiers, tâches et réglages.
Contient toute la logique métier (réinitialisation hebdomadaire, calcul de complétion, etc.).
"""

import logging
import os
import re
import shutil
import threading
import time
from datetime import datetime, timedelta
from .config import DEFAULT_DB_PATH, get_current_db_path, load_local_config, save_local_config
from .database import get_connection, init_db
from .discord import notify_task_created, notify_task_status_changed, notify_task_deleted, notify_folder_created

logger = logging.getLogger("todolist.services")

_HEX_COLOR = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_VALID_BG_TYPES = {"default", "solid", "gradient", "preset", "image", "custom"}
_VALID_PRESET_KEYS = {
    "pro-dark", "carbon", "midnight", "slate", "emerald", "violet",
    "street", "techno", "cyberpunk", "y2k", "arcade", "luxury", "zen", "lava"
}
SENSITIVE_SETTINGS_KEYS = {"discord_webhook_url"}


def _safe_color(value, default="#6366f1"):
    """Valide et retourne une couleur hexadécimale sûre (évite injections CSS/HTML)."""
    v = str(value or "").strip()
    return v if _HEX_COLOR.match(v) else default


def _safe_bg_type(value, default="default"):
    """Valide le type de fond selon une liste blanche stricte."""
    v = str(value or "").strip().lower()
    return v if v in _VALID_BG_TYPES else default


def _safe_bg_value(val, bg_type):
    """Valide la valeur de fond du dossier selon le type sélectionné."""
    v = str(val or "").strip()
    if not v:
        return ""
    if bg_type == "preset":
        return v if v in _VALID_PRESET_KEYS else "pro-dark"
    elif bg_type in ("image", "custom"):
        if len(v) <= 500 and (v.startswith("/assets/") or v.startswith("url(") or v.startswith("data:image/")):
            return v.replace("<", "").replace(">", "").replace(";", "")
        return ""
    else:
        return _safe_color(v, default="") if v else ""


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
    _presence_lock = threading.Lock()
    _version_lock = threading.Lock()
    _shared_presence = {}          # (db_path, salon_id) -> {client_id: {"last_seen": ts, "name": str}}
    _shared_versions = {}          # (db_path, salon_id) -> int
    _shared_timestamps = {}        # (db_path, salon_id) -> ts
    _shared_global_version = {}    # db_path -> int

    def __init__(self, db_path=None):
        self.db_path = db_path

    @property
    def _global_version(self):
        with self._version_lock:
            return self._shared_global_version.get(self.db_path, 1)

    def _conn(self):
        if self.db_path:
            return get_connection(self.db_path)
        return get_connection()

    def _get_salon_id_for_folder(self, folder_id):
        if not folder_id:
            return None
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute("SELECT salon_id FROM folders WHERE id = ?", (folder_id,))
            row = cursor.fetchone()
            conn.close()
            return row["salon_id"] if row else None
        except Exception:
            return None

    def bump_salon_version(self, salon_id=None):
        """Incrémente la version d'un salon ou de tous les salons pour la synchro en direct."""
        now = time.time()
        db_k = self.db_path
        with self._version_lock:
            self._shared_global_version[db_k] = self._shared_global_version.get(db_k, 0) + 1
            if salon_id is not None:
                k = (db_k, salon_id)
                self._shared_versions[k] = self._shared_versions.get(k, 0) + 1
                self._shared_timestamps[k] = now
            else:
                for (d, s_id) in list(self._shared_versions.keys()):
                    if d == db_k:
                        self._shared_versions[(d, s_id)] = self._shared_versions.get((d, s_id), 0) + 1
                        self._shared_timestamps[(d, s_id)] = now

    def get_salon_version(self, salon_id):
        with self._version_lock:
            return self._shared_versions.get((self.db_path, salon_id), 1)

    def record_presence(self, salon_id, client_id, client_name="Membre"):
        """Enregistre l'activité d'un membre sur un salon pour le comptage en ligne."""
        if not salon_id or not client_id:
            return
        now = time.time()
        db_k = self.db_path
        with self._presence_lock:
            # Un client ne peut être en ligne que sur un seul salon à la fois pour cette base
            for (d, s_id), clients in list(self._shared_presence.items()):
                if d == db_k and s_id != salon_id and client_id in clients:
                    del clients[client_id]

            k = (db_k, salon_id)
            if k not in self._shared_presence:
                self._shared_presence[k] = {}
            self._shared_presence[k][client_id] = {
                "last_seen": now,
                "name": str(client_name)[:50]
            }

    def get_active_member_count(self, salon_id, timeout=12.0):
        """Retourne le nombre de membres actifs sur un salon."""
        now = time.time()
        k = (self.db_path, salon_id)
        with self._presence_lock:
            clients = self._shared_presence.get(k, {})
            expired = [cid for cid, info in clients.items() if now - info["last_seen"] > timeout]
            for cid in expired:
                del clients[cid]
            return len(clients)

    def get_all_salons_active_counts(self, timeout=12.0):
        """Retourne un dictionnaire {salon_id: count} pour tous les salons."""
        now = time.time()
        db_k = self.db_path
        res = {}
        with self._presence_lock:
            for (d, s_id), clients in list(self._shared_presence.items()):
                if d == db_k:
                    expired = [cid for cid, info in clients.items() if now - info["last_seen"] > timeout]
                    for cid in expired:
                        del clients[cid]
                    res[s_id] = len(clients)
        return res

    def get_all_data(self):
        """Récupère l'ensemble des données après avoir vérifié les réinitialisations hebdomadaires."""
        conn = self._conn()
        self.check_weekly_resets(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM salons ORDER BY position ASC, id ASC")
        raw_salons = [dict(row) for row in cursor.fetchall()]
        counts = self.get_all_salons_active_counts()
        salons = []
        for s in raw_salons:
            s_dict = dict(s)
            url = s_dict.get("discord_webhook_url") or ""
            s_dict["discord_webhook_configured"] = bool(url)
            if url:
                s_dict["discord_webhook_url"] = "••••" + str(url)[-4:] if len(str(url)) > 4 else "••••"
            s_dict["active_members_count"] = counts.get(s_dict["id"], 0)
            s_dict["version"] = self.get_salon_version(s_dict["id"])
            salons.append(s_dict)

        cursor.execute("SELECT * FROM folders ORDER BY position ASC, id ASC")
        folders = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM tasks ORDER BY completed ASC, id DESC")
        tasks = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT key, value FROM settings")
        raw_settings = {row["key"]: row["value"] for row in cursor.fetchall()}

        conn.close()

        # Masquer les données sensibles (ex: webhook Discord)
        safe_settings = {}
        for k, v in raw_settings.items():
            if k in SENSITIVE_SETTINGS_KEYS and v:
                safe_settings[k] = "••••" + str(v)[-4:] if len(str(v)) > 4 else "••••"
            else:
                safe_settings[k] = v
        safe_settings["discord_webhook_configured"] = bool(raw_settings.get("discord_webhook_url"))

        return {"salons": salons, "folders": folders, "tasks": tasks, "settings": safe_settings}

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
                    logger.debug("Date last_reset_at invalide pour dossier %s", folder_id, exc_info=True)
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

            # Déterminer le salon_id concerné
            salon_id = kwargs.get("salon_id")
            folder_id = kwargs.get("folder_id") or kwargs.get("task", {}).get("folder_id")
            if not salon_id and folder_id:
                cursor.execute("SELECT salon_id FROM folders WHERE id = ?", (folder_id,))
                row = cursor.fetchone()
                if row and row["salon_id"]:
                    salon_id = row["salon_id"]

            webhook_url = ""
            author = kwargs.get("author") or ""
            is_enabled = False

            # 1. Vérifier si le salon spécifique a un webhook Discord configuré
            if salon_id:
                cursor.execute("SELECT * FROM salons WHERE id = ?", (salon_id,))
                salon_row = cursor.fetchone()
                if salon_row:
                    s_data = dict(salon_row)
                    if s_data.get("discord_enabled") and s_data.get("discord_webhook_url"):
                        webhook_url = str(s_data["discord_webhook_url"]).strip()
                        is_enabled = True
                        if not author and s_data.get("discord_author_name"):
                            author = s_data["discord_author_name"]

            # 2. Fallback sur les réglages globaux si le salon n'a pas de webhook propre
            cursor.execute("SELECT key, value FROM settings WHERE key LIKE 'discord_%'")
            settings = {row["key"]: row["value"] for row in cursor.fetchall()}
            conn.close()

            if not is_enabled:
                if str(settings.get("discord_enabled", "0")) == "1" and settings.get("discord_webhook_url"):
                    webhook_url = str(settings.get("discord_webhook_url", "")).strip()
                    is_enabled = True

            if not is_enabled or not webhook_url:
                return

            if not author:
                author = settings.get("discord_author_name") or "Équipe"

            if action_type == "task_created" and str(settings.get("discord_notify_created", "1")) == "1":
                notify_task_created(webhook_url, kwargs.get("task", {}), kwargs.get("folder_name", "Général"), author=author)
            elif action_type == "task_status" and str(settings.get("discord_notify_completed", "1")) == "1":
                notify_task_status_changed(webhook_url, kwargs.get("task", {}), kwargs.get("folder_name", "Général"), author=author)
            elif action_type == "task_deleted" and str(settings.get("discord_notify_deleted", "1")) == "1":
                notify_task_deleted(webhook_url, kwargs.get("task_title", "Tâche"), kwargs.get("folder_name", "Général"), author=author)
            elif action_type == "folder_created" and str(settings.get("discord_notify_folder", "1")) == "1":
                notify_folder_created(webhook_url, kwargs.get("folder_name", "Dossier"), author=author)
        except Exception:
            logger.warning("Erreur lors de la notification Discord", exc_info=True)

    # --- Salons (Espaces de travail partagés) ---

    def get_salons(self):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM salons ORDER BY position ASC, id ASC")
        raw = [dict(r) for r in cursor.fetchall()]
        conn.close()
        counts = self.get_all_salons_active_counts()
        res = []
        for s in raw:
            item = dict(s)
            url = item.get("discord_webhook_url") or ""
            item["discord_webhook_configured"] = bool(url)
            if url:
                item["discord_webhook_url"] = "••••" + str(url)[-4:] if len(str(url)) > 4 else "••••"
            item["active_members_count"] = counts.get(item["id"], 0)
            item["version"] = self.get_salon_version(item["id"])
            res.append(item)
        return res

    def get_raw_salon_setting(self, salon_id, key):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {key} FROM salons WHERE id = ?", (salon_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_salon(self, salon_id):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM salons WHERE id = ?", (salon_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        item = dict(row)
        url = item.get("discord_webhook_url") or ""
        item["discord_webhook_configured"] = bool(url)
        if url:
            item["discord_webhook_url"] = "••••" + str(url)[-4:] if len(str(url)) > 4 else "••••"
        item["active_members_count"] = self.get_active_member_count(salon_id)
        item["version"] = self.get_salon_version(salon_id)
        return item

    def create_salon(self, data):
        conn = self._conn()
        cursor = conn.cursor()
        name = str(data.get("name") or "Nouveau salon").strip()[:100]
        icon = str(data.get("icon") or "folder")[:50]
        color = _safe_color(data.get("color"), default="#4f46e5")
        description = str(data.get("description") or "").strip()[:300]
        discord_webhook_url = str(data.get("discord_webhook_url") or "").strip()
        discord_enabled = 1 if data.get("discord_enabled") in (1, "1", True) else 0
        discord_author_name = str(data.get("discord_author_name") or "").strip()[:100]

        cursor.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM salons")
        next_pos = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO salons (name, icon, color, description, discord_webhook_url, discord_enabled, discord_author_name, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, icon, color, description, discord_webhook_url, discord_enabled, discord_author_name, next_pos))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        self.bump_salon_version(new_id)
        return self.get_salon(new_id)

    def update_salon(self, salon_id, data):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM salons WHERE id = ?", (salon_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            return None

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
            values.append(_safe_color(data["color"], default="#4f46e5"))
        if "description" in data:
            fields.append("description = ?")
            values.append(str(data["description"]).strip()[:300])
        if "discord_webhook_url" in data:
            new_url = str(data["discord_webhook_url"]).strip()
            # Si masqué (••••), ne pas écraser l'URL secrète existante
            if not new_url.startswith("••••"):
                fields.append("discord_webhook_url = ?")
                values.append(new_url)
        if "discord_enabled" in data:
            fields.append("discord_enabled = ?")
            values.append(1 if data["discord_enabled"] in (1, "1", True) else 0)
        if "discord_author_name" in data:
            fields.append("discord_author_name = ?")
            values.append(str(data["discord_author_name"]).strip()[:100])
        if "position" in data:
            fields.append("position = ?")
            values.append(_safe_int(data["position"], default=0))

        if fields:
            values.append(salon_id)
            cursor.execute(f"UPDATE salons SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

        conn.close()
        self.bump_salon_version(salon_id)
        return self.get_salon(salon_id)

    def delete_salon(self, salon_id):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM salons")
        count = cursor.fetchone()[0]
        if count <= 1:
            conn.close()
            return False, "Impossible de supprimer le dernier salon."

        cursor.execute("""
            DELETE FROM tasks WHERE folder_id IN (
                SELECT id FROM folders WHERE salon_id = ?
            )
        """, (salon_id,))
        cursor.execute("DELETE FROM folders WHERE salon_id = ?", (salon_id,))
        cursor.execute("DELETE FROM salons WHERE id = ?", (salon_id,))
        conn.commit()
        conn.close()
        self.bump_salon_version()
        return True, "Salon supprimé avec succès."

    def export_salon(self, salon_id):
        """Exporte uniquement les dossiers et tâches d'un salon donné pour partage."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM salons WHERE id = ?", (salon_id,))
        salon_row = cursor.fetchone()
        if not salon_row:
            conn.close()
            return None

        salon = dict(salon_row)
        # Ne JAMAIS exporter le webhook Discord secret du propriétaire
        salon.pop("discord_webhook_url", None)

        cursor.execute("SELECT * FROM folders WHERE salon_id = ? ORDER BY position ASC, id ASC", (salon_id,))
        folders = [dict(r) for r in cursor.fetchall()]
        folder_ids = [f["id"] for f in folders]

        tasks = []
        if folder_ids:
            placeholders = ",".join("?" * len(folder_ids))
            cursor.execute(f"SELECT * FROM tasks WHERE folder_id IN ({placeholders}) ORDER BY id ASC", folder_ids)
            tasks = [dict(r) for r in cursor.fetchall()]

        conn.close()
        salon_name = salon.get("name") or "Salon"
        return {
            "version": 2,
            "scope": "salon",
            "salon_name": salon_name,
            "name": salon_name,
            "exported_at": datetime.now().isoformat(),
            "salon": salon,
            "folders": folders,
            "tasks": tasks
        }

    def export_salon_to_file(self, salon_id):
        """Exporte un salon sous forme de fichier .tdl sauvegardé dans le dossier Téléchargements/Downloads."""
        import base64
        import zlib
        import json

        data = self.export_salon(salon_id)
        if not data:
            return None

        salon_name = data.get("salon", {}).get("name", "salon")
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", salon_name).strip("-") or "salon"
        filename = f"todolist-salon-{clean_name.lower()}.tdl"

        # Chercher le répertoire de téléchargements de l'utilisateur
        target_dir = os.path.expanduser("~/Téléchargements")
        if not os.path.isdir(target_dir):
            target_dir = os.path.expanduser("~/Downloads")
        if not os.path.isdir(target_dir):
            target_dir = os.path.expanduser("~/Bureau")
        if not os.path.isdir(target_dir):
            target_dir = os.path.expanduser("~")

        filepath = os.path.join(target_dir, filename)
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(filepath):
            filepath = f"{base}_{counter}{ext}"
            filename = os.path.basename(filepath)
            counter += 1

        file_saved = False
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            file_saved = True
        except Exception as e:
            logger.warning("Erreur écriture fichier export: %s", e)
            filepath = ""

        # Générer un code d'invitation compressé en base64 pour partage instantané sur Discord
        json_bytes = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        compressed = zlib.compress(json_bytes, level=9)
        invite_code = "TDL1_" + base64.urlsafe_b64encode(compressed).decode("ascii")

        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "file_saved": file_saved,
            "salon_name": salon_name,
            "folder_count": len(data.get("folders", [])),
            "task_count": len(data.get("tasks", [])),
            "invite_code": invite_code,
            "data": data
        }

    def import_salon(self, data, target_salon_id=None):
        """Importe un salon partagé (dict, code TDL1_ ou JSON). Si target_salon_id est None, crée un nouveau salon."""
        if isinstance(data, str):
            clean_str = data.strip()
            if clean_str.startswith("TDL1_"):
                try:
                    import base64
                    import zlib
                    import json
                    b64_part = clean_str[5:]
                    decompressed = zlib.decompress(base64.urlsafe_b64decode(b64_part.encode("ascii")))
                    data = json.loads(decompressed.decode("utf-8"))
                except Exception as e:
                    logger.warning("Échec décodage code d'invitation salon: %s", e)
                    return None
            else:
                try:
                    import json
                    data = json.loads(clean_str)
                except Exception:
                    return None

        if not isinstance(data, dict):
            return None

        # Si le dictionnaire est encapsulé dans "data"
        if "data" in data and isinstance(data["data"], dict):
            data = data["data"]

        incoming_salon = data.get("salon")
        if not isinstance(incoming_salon, dict):
            incoming_salon = {}

        incoming_folders = data.get("folders", [])
        if not isinstance(incoming_folders, list):
            incoming_folders = []

        incoming_tasks = data.get("tasks", [])
        if not isinstance(incoming_tasks, list):
            incoming_tasks = []

        conn = self._conn()
        cursor = conn.cursor()

        salon_id = target_salon_id
        if salon_id:
            cursor.execute("SELECT id FROM salons WHERE id = ?", (salon_id,))
            if not cursor.fetchone():
                salon_id = None

        if not salon_id:
            raw_name = (
                incoming_salon.get("name")
                or data.get("salon_name")
                or data.get("name")
                or (data.get("salon") if isinstance(data.get("salon"), str) else None)
                or incoming_salon.get("title")
                or data.get("title")
                or "Salon Partagé"
            )
            name = str(raw_name).strip()[:100]
            if not name:
                name = "Salon Partagé"

            icon = str(
                incoming_salon.get("icon")
                or data.get("icon")
                or "folder"
            )[:50]

            raw_color = (
                incoming_salon.get("color")
                or data.get("color")
                or "#4f46e5"
            )
            color = _safe_color(raw_color, default="#4f46e5")

            raw_desc = (
                incoming_salon.get("description")
                or data.get("description")
                or ""
            )
            desc = str(raw_desc).strip()[:300]

            cursor.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM salons")
            next_pos = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO salons (name, icon, color, description, position)
                VALUES (?, ?, ?, ?, ?)
            """, (name, icon, color, desc, next_pos))
            conn.commit()
            salon_id = cursor.lastrowid

        folder_id_map = {}
        for f in incoming_folders:
            old_id = f.get("id")
            fname = str(f.get("name") or "Dossier").strip()[:100]
            ficon = str(f.get("icon") or "folder")[:50]
            fcol = _safe_color(f.get("color"), default="#4f46e5")
            f_reset = 1 if f.get("auto_reset_weekly") else 0
            f_bg_type = _safe_bg_type(f.get("bg_type"), default="default")
            f_bg1 = _safe_bg_value(f.get("bg_color1"), f_bg_type)
            f_bg2 = _safe_color(f.get("bg_color2"), default="") if f.get("bg_color2") else ""
            f_angle = _safe_int(f.get("bg_angle", 135), default=135, min_val=0, max_val=360)

            cursor.execute("""
                INSERT INTO folders (salon_id, name, icon, color, auto_reset_weekly, bg_type, bg_color1, bg_color2, bg_angle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (salon_id, fname, ficon, fcol, f_reset, f_bg_type, f_bg1, f_bg2, f_angle))
            conn.commit()
            new_fid = cursor.lastrowid
            if old_id is not None:
                folder_id_map[old_id] = new_fid

        for t in incoming_tasks:
            old_fid = t.get("folder_id")
            new_fid = folder_id_map.get(old_fid)
            if not new_fid and folder_id_map:
                new_fid = next(iter(folder_id_map.values()))

            title = str(t.get("title") or "Tâche sans titre").strip()[:500]
            completed = 1 if t.get("completed") else 0
            has_prog = 1 if t.get("has_progress") else 0
            prog = _safe_int(t.get("progress", 0), default=0, min_val=0, max_val=100)
            prio = str(t.get("priority") or "normal")[:20]
            due = str(t.get("due_date"))[:30] if t.get("due_date") else None

            cursor.execute("""
                INSERT INTO tasks (folder_id, title, completed, has_progress, progress, priority, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_fid, title, completed, has_prog, prog, prio, due))

        conn.commit()
        conn.close()
        self.bump_salon_version(salon_id)
        return self.get_salon(salon_id)

    # --- Dossiers ---

    def create_folder(self, data):
        conn = self._conn()
        cursor = conn.cursor()
        name = str(data.get("name") or "Nouveau dossier").strip()[:100]
        icon = str(data.get("icon") or "folder")[:50]
        color = _safe_color(data.get("color"), default="#4f46e5")
        auto_reset_weekly = 1 if data.get("auto_reset_weekly") else 0
        bg_type = _safe_bg_type(data.get("bg_type"), default="default")
        bg_color1 = _safe_bg_value(data.get("bg_color1"), bg_type)
        bg_color2 = _safe_color(data.get("bg_color2"), default="") if data.get("bg_color2") else ""
        bg_angle = _safe_int(data.get("bg_angle", 135), default=135, min_val=0, max_val=360)

        # Assigner à un salon valide
        salon_id = _safe_int(data.get("salon_id"), default=None)
        if salon_id is not None:
            cursor.execute("SELECT id FROM salons WHERE id = ?", (salon_id,))
            if not cursor.fetchone():
                cursor.execute("SELECT id FROM salons ORDER BY position ASC, id ASC LIMIT 1")
                first_s = cursor.fetchone()
                salon_id = first_s["id"] if first_s else 1
        else:
            cursor.execute("SELECT id FROM salons ORDER BY position ASC, id ASC LIMIT 1")
            first_s = cursor.fetchone()
            salon_id = first_s["id"] if first_s else 1

        cursor.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM folders WHERE salon_id = ?", (salon_id,))
        next_pos = cursor.fetchone()[0]

        cursor.execute(
            """INSERT INTO folders (salon_id, name, icon, color, auto_reset_weekly, bg_type, bg_color1, bg_color2, bg_angle, position) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (salon_id, name, icon, color, auto_reset_weekly, bg_type, bg_color1, bg_color2, bg_angle, next_pos)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM folders WHERE id = ?", (new_id,))
        created = dict(cursor.fetchone())
        conn.close()
        self.bump_salon_version(salon_id)
        self._trigger_discord("folder_created", folder_name=created.get("name", "Nouveau dossier"), author=data.get("author"), salon_id=salon_id)
        return created

    def reorder_folders(self, folder_ids):
        """Met à jour l'ordre des dossiers suite à un glisser-déposer."""
        if not isinstance(folder_ids, (list, tuple)):
            return False
        conn = self._conn()
        cursor = conn.cursor()
        for idx, fid in enumerate(folder_ids):
            safe_id = _safe_int(fid, None)
            if safe_id is not None:
                cursor.execute("UPDATE folders SET position = ? WHERE id = ?", (idx, safe_id))
        conn.commit()
        conn.close()
        self.bump_salon_version()
        return True

    def update_folder(self, folder_id, data):
        conn = self._conn()
        cursor = conn.cursor()
        fields = []
        values = []

        if "name" in data:
            fields.append("name = ?")
            values.append(str(data["name"]).strip()[:100])
        if "salon_id" in data:
            s_id = _safe_int(data["salon_id"], None)
            if s_id:
                cursor.execute("SELECT id FROM salons WHERE id = ?", (s_id,))
                if cursor.fetchone():
                    fields.append("salon_id = ?")
                    values.append(s_id)
        if "icon" in data:
            fields.append("icon = ?")
            values.append(str(data["icon"])[:50])
        if "color" in data:
            fields.append("color = ?")
            values.append(_safe_color(data["color"], default="#4f46e5"))
        if "auto_reset_weekly" in data:
            fields.append("auto_reset_weekly = ?")
            values.append(1 if data["auto_reset_weekly"] else 0)
        target_bg_type = _safe_bg_type(data["bg_type"], default="default") if "bg_type" in data else None
        if "bg_type" in data:
            fields.append("bg_type = ?")
            values.append(target_bg_type)
        if "bg_color1" in data:
            fields.append("bg_color1 = ?")
            values.append(_safe_bg_value(data["bg_color1"], target_bg_type or "default"))
        if "bg_color2" in data:
            fields.append("bg_color2 = ?")
            values.append(_safe_color(data["bg_color2"], default="") if data["bg_color2"] else "")
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
        res = dict(row) if row else None
        if res:
            self.bump_salon_version(res.get("salon_id"))
        return res

    def delete_folder(self, folder_id):
        salon_id = self._get_salon_id_for_folder(folder_id)
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE folder_id = ?", (folder_id,))
        cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        conn.commit()
        conn.close()
        if salon_id:
            self.bump_salon_version(salon_id)
        return True

    def reset_folder_tasks(self, folder_id):
        """Réinitialise immédiatement les tâches d'un dossier (non faites, 0%)."""
        salon_id = self._get_salon_id_for_folder(folder_id)
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
        if salon_id:
            self.bump_salon_version(salon_id)
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
        salon_id = self._get_salon_id_for_folder(folder_id)
        if salon_id:
            self.bump_salon_version(salon_id)
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

        if row and row["folder_id"]:
            salon_id = self._get_salon_id_for_folder(row["folder_id"])
            if salon_id:
                self.bump_salon_version(salon_id)

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
        folder_id = existing["folder_id"] if existing else None
        if existing and existing["folder_id"]:
            cursor.execute("SELECT name FROM folders WHERE id = ?", (existing["folder_id"],))
            f_row = cursor.fetchone()
            if f_row:
                folder_name = f_row["name"]

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

        if folder_id:
            salon_id = self._get_salon_id_for_folder(folder_id)
            if salon_id:
                self.bump_salon_version(salon_id)

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
        salon_id = self._get_salon_id_for_folder(folder_id) if folder_id else None
        self.bump_salon_version(salon_id)
        return True

    # --- Réglages ---

    def update_settings(self, payload):
        conn = self._conn()
        cursor = conn.cursor()
        for k, v in payload.items():
            # Ne pas écraser une valeur sensible existante avec une valeur masquée
            if k in SENSITIVE_SETTINGS_KEYS and str(v).startswith("••••"):
                continue
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (str(k), str(v)))
        conn.commit()
        conn.close()
        return self.get_all_data()["settings"]

    def get_raw_setting(self, key):
        """Récupère la valeur brute non masquée d'un paramètre sensible en base."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (str(key),))
        row = cursor.fetchone()
        conn.close()
        return row["value"] if row else ""

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
            logger.warning("Erreur lors de la lecture des statistiques de la base", exc_info=True)

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
                    logger.warning("Erreur lors du checkpoint WAL", exc_info=True)
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
            logger.debug("Erreur lors de check_updates", exc_info=True)

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
            color = _safe_color(f.get("color"), default="#4f46e5")
            auto_reset_weekly = 1 if f.get("auto_reset_weekly") else 0
            bg_type = _safe_bg_type(f.get("bg_type"), default="default")
            bg_color1 = _safe_bg_value(f.get("bg_color1"), bg_type)
            bg_color2 = _safe_color(f.get("bg_color2"), default="") if f.get("bg_color2") else ""
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
                # Ne jamais écraser un secret en base par une valeur masquée (••••)
                if k in SENSITIVE_SETTINGS_KEYS and str(v).startswith("••••"):
                    logger.warning("import_backup: valeur masquée ignorée pour la clé sensible '%s'", k)
                    continue
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (str(k), str(v)))

        conn.commit()
        conn.close()
        return self.get_all_data()

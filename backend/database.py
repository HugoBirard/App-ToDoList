"""
Couche d'accès et d'initialisation de la base de données SQLite.
Gère les tables, clés étrangères et migrations de schéma automatiques.
"""

import os
import sqlite3
from .config import DATA_DIR, DB_PATH


def get_connection(db_path=DB_PATH):
    """Retourne une connexion SQLite configurée avec accès par nom de colonne et mode WAL concurrent."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_PATH):
    """Initialise le schéma de la base et applique les migrations si nécessaire."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Table des dossiers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT 'folder',
            color TEXT DEFAULT '#4f46e5',
            auto_reset_weekly INTEGER DEFAULT 0,
            last_reset_at TIMESTAMP DEFAULT NULL,
            bg_type TEXT DEFAULT 'default',
            bg_color1 TEXT DEFAULT '',
            bg_color2 TEXT DEFAULT '',
            bg_angle INTEGER DEFAULT 135,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table des tâches
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER,
            title TEXT NOT NULL,
            completed BOOLEAN DEFAULT 0,
            has_progress INTEGER DEFAULT 0,
            progress INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'normal',
            due_date TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP DEFAULT NULL,
            FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE CASCADE
        )
    """)

    # Table des réglages globaux (thème, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Migrations incrémentales pour les bases existantes
    cursor.execute("PRAGMA table_info(folders)")
    folder_cols = [r[1] for r in cursor.fetchall()]
    if "auto_reset_weekly" not in folder_cols:
        cursor.execute("ALTER TABLE folders ADD COLUMN auto_reset_weekly INTEGER DEFAULT 0")
    if "last_reset_at" not in folder_cols:
        cursor.execute("ALTER TABLE folders ADD COLUMN last_reset_at TIMESTAMP DEFAULT NULL")
        cursor.execute("UPDATE folders SET last_reset_at = CURRENT_TIMESTAMP WHERE last_reset_at IS NULL")
    if "bg_type" not in folder_cols:
        cursor.execute("ALTER TABLE folders ADD COLUMN bg_type TEXT DEFAULT 'default'")
    if "bg_color1" not in folder_cols:
        cursor.execute("ALTER TABLE folders ADD COLUMN bg_color1 TEXT DEFAULT ''")
    if "bg_color2" not in folder_cols:
        cursor.execute("ALTER TABLE folders ADD COLUMN bg_color2 TEXT DEFAULT ''")
    if "bg_angle" not in folder_cols:
        cursor.execute("ALTER TABLE folders ADD COLUMN bg_angle INTEGER DEFAULT 135")

    cursor.execute("PRAGMA table_info(tasks)")
    task_cols = [r[1] for r in cursor.fetchall()]
    if "has_progress" not in task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN has_progress INTEGER DEFAULT 0")
    if "progress" not in task_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN progress INTEGER DEFAULT 0")

    # Migration des anciens émojis vers les identifiants d'icônes vectorielles
    emoji_migrations = {
        "📋": "clipboard",
        "💼": "briefcase",
        "🌱": "leaf",
        "🏠": "home",
        "🛒": "shopping-cart",
        "🚀": "rocket",
        "🎓": "graduation-cap",
        "🎯": "target",
        "💡": "lightbulb",
        "⭐": "star",
        "❤️": "heart",
        "📁": "folder",
    }
    for em, ic in emoji_migrations.items():
        cursor.execute("UPDATE folders SET icon = ? WHERE icon = ?", (ic, em))
    cursor.execute("UPDATE folders SET name = 'Habitudes Hebdo' WHERE name LIKE 'Habitudes Hebdo%'")

    # Données d'exemple si premier démarrage
    cursor.execute("SELECT COUNT(*) FROM folders")
    if cursor.fetchone()[0] == 0:
        _seed_default_data(cursor)

    conn.commit()
    conn.close()


def _seed_default_data(cursor):
    """Insère quelques exemples de démarrage soignés."""
    cursor.execute(
        "INSERT INTO folders (name, icon, color, auto_reset_weekly) VALUES (?, ?, ?, 0)",
        ("Général", "clipboard", "#6366f1")
    )
    cursor.execute(
        "INSERT INTO folders (name, icon, color, auto_reset_weekly) VALUES (?, ?, ?, 0)",
        ("Travail", "briefcase", "#3b82f6")
    )
    cursor.execute(
        "INSERT INTO folders (name, icon, color, auto_reset_weekly) VALUES (?, ?, ?, 1)",
        ("Habitudes Hebdo", "leaf", "#10b981")
    )

    general_id = 1
    cursor.execute(
        "INSERT INTO tasks (folder_id, title, completed, has_progress, progress) VALUES (?, ?, ?, ?, ?)",
        (general_id, "Bienvenue dans votre ToDoList !", 0, 0, 0)
    )
    cursor.execute(
        "INSERT INTO tasks (folder_id, title, completed, has_progress, progress) VALUES (?, ?, ?, ?, ?)",
        (general_id, "Exemple de tâche avec progression (glisser jusqu'à 100%)", 0, 1, 40)
    )
    cursor.execute(
        "INSERT INTO tasks (folder_id, title, completed, has_progress, progress) VALUES (?, ?, ?, ?, ?)",
        (general_id, "Cocher cette tâche pour la marquer comme faite", 1, 0, 100)
    )

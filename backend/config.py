"""
Configuration globale et chemins de l'application ToDoList.
Supporte les emplacements personnalisés pour la synchronisation multi-PC (Nextcloud, Dropbox, Syncthing, etc.).
"""

import json
import logging
import os
import socket
import subprocess

logger = logging.getLogger("todolist.config")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Emplacement par défaut des données
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DATA_DIR, "todolist.db")

# Fichier de configuration locale de la machine (stocke l'emplacement partagé choisi)
APP_CONFIG_DIR = os.path.expanduser("~/.config/todolist")
LOCAL_CONFIG_FILE = os.path.join(APP_CONFIG_DIR, "config.json")


def load_local_config():
    """Charge le fichier de configuration de l'application sur la machine."""
    if os.path.exists(LOCAL_CONFIG_FILE):
        try:
            with open(LOCAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("Erreur lors de la lecture du fichier de config locale", exc_info=True)
            return {}
    return {}


def save_local_config(cfg):
    """Sauvegarde le fichier de configuration de l'application sur la machine."""
    try:
        os.makedirs(APP_CONFIG_DIR, exist_ok=True)
        with open(LOCAL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        logger.warning("Erreur lors de la sauvegarde du fichier de config locale", exc_info=True)
        return False


def get_current_db_path():
    """Retourne le chemin de base actif (personnalisé si configuré, sinon défaut)."""
    cfg = load_local_config()
    custom = cfg.get("custom_db_path")
    if custom and isinstance(custom, str) and custom.strip():
        expanded = os.path.abspath(os.path.expanduser(custom.strip()))
        return expanded
    return DEFAULT_DB_PATH


# DB_PATH par défaut (peut être surchargé ou résolu dynamiquement via get_current_db_path())
DB_PATH = get_current_db_path()
DATA_DIR = os.path.dirname(DB_PATH)

# Icônes de l'application
ICON_PNG = os.path.join(STATIC_DIR, "assets", "icon.png")
if not os.path.exists(ICON_PNG):
    ICON_PNG = os.path.join(STATIC_DIR, "icon.png")

# Constantes Réseau & App
DEFAULT_PORT = 4848
APP_NAME = "ToDoList"
APP_ID = "com.local.todolist"

# Thème sombre professionnel par défaut
DEFAULT_PRO_BG = "linear-gradient(135deg, #08090c 0%, #131620 50%, #1a1e2b 100%)"


def get_lan_ips():
    """Détecte les adresses IPv4 locales de la machine pour le partage réseau."""
    ips = set()
    try:
        proc = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=2)
        for part in proc.stdout.split():
            part = part.strip()
            if part and not part.startswith("127.") and not part.startswith("172.17."):
                ips.add(part)
    except Exception:
        pass

    if not ips:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip and not ip.startswith("127."):
                    ips.add(ip)
        except Exception:
            pass

    return sorted(list(ips))


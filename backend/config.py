"""
Configuration globale et chemins de l'application ToDoList.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "todolist.db")

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

"""
Package backend ToDoList.
"""

from .config import BASE_DIR, STATIC_DIR, DATA_DIR, DB_PATH, DEFAULT_PORT
from .database import init_db, get_connection
from .services import TodoService
from .handlers import TodoRequestHandler
from .window import launch_app_window, install_desktop_shortcuts

__all__ = [
    "BASE_DIR",
    "STATIC_DIR",
    "DATA_DIR",
    "DB_PATH",
    "DEFAULT_PORT",
    "init_db",
    "get_connection",
    "TodoService",
    "TodoRequestHandler",
    "launch_app_window",
    "install_desktop_shortcuts",
]

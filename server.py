#!/usr/bin/env python3
"""
Serveur HTTP autonome pour l'application ToDo List.
Peut être lancé directement : python3 server.py [--port 4848] [--no-window]
"""

import sys
from http.server import ThreadingHTTPServer

from backend.config import DEFAULT_PORT
from backend.database import init_db
from backend.handlers import TodoRequestHandler
from backend.window import launch_app_window


def run_server(port=DEFAULT_PORT, open_window=False):
    """Démarre le serveur HTTP et initialise la base de données."""
    init_db()
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, TodoRequestHandler)
    url = f"http://127.0.0.1:{port}"

    print(f"======================================================")
    print(f"  Serveur ToDoList démarré avec succès !")
    print(f"  URL : {url}")
    print(f"  Appuyez sur Ctrl+C pour arrêter le serveur.")
    print(f"======================================================")

    if open_window:
        try:
            launch_app_window(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur...")
        httpd.server_close()


if __name__ == "__main__":
    port = DEFAULT_PORT
    if "--port" in sys.argv:
        try:
            idx = sys.argv.index("--port")
            port = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            pass

    open_win = "--window" in sys.argv
    run_server(port=port, open_window=open_win)

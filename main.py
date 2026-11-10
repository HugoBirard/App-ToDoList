#!/usr/bin/env python3
"""
Point d'entrée principal de l'application ToDoList.
Orchestre :
- L'installation automatique du raccourci système
- La détection de port et le démarrage du serveur en arrière-plan
- Le lancement de la fenêtre dédiée
- La fermeture propre du serveur lors de la fermeture de la fenêtre
"""

import time
import socket
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from backend.config import DEFAULT_PORT
from backend.database import init_db
from backend.handlers import TodoRequestHandler
from backend.window import launch_app_window, install_desktop_shortcuts


def is_server_ready(url, timeout=0.6):
    """Vérifie si le serveur ToDoList répond déjà sur cette URL."""
    try:
        req = urllib.request.Request(f"{url}/api/data", headers={"User-Agent": "ToDoListChecker"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def find_free_port(start_port=DEFAULT_PORT):
    """Trouve un port disponible à partir du port de départ."""
    for p in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start_port


def start_server_thread(port):
    """Démarre le serveur HTTP dans un thread démon."""
    init_db()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), TodoRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def main():
    # 1. Enregistrer le raccourci dans l'environnement de bureau
    install_desktop_shortcuts()

    # 2. Gestion du serveur local
    app_url = f"http://127.0.0.1:{DEFAULT_PORT}"
    server_instance = None

    if is_server_ready(app_url):
        print(f"Serveur ToDoList déjà actif sur {app_url}.")
    else:
        port = find_free_port(DEFAULT_PORT)
        app_url = f"http://127.0.0.1:{port}"
        print(f"Démarrage du serveur local sur {app_url}...")
        server_instance = start_server_thread(port)

        for _ in range(30):
            if is_server_ready(app_url):
                break
            time.sleep(0.1)

    # 3. Ouvrir la fenêtre autonome et attendre sa fermeture
    try:
        launch_app_window(app_url, sys.argv[1:])
    finally:
        if server_instance:
            print("Fermeture de l'application et arrêt du serveur...")
            server_instance.shutdown()


if __name__ == "__main__":
    main()

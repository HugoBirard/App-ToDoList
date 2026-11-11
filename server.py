#!/usr/bin/env python3
"""
Serveur HTTP autonome pour l'application ToDoList.
Peut être lancé directement : python3 server.py [--port 4848] [--host 0.0.0.0] [--share] [--token <SECRET>]
"""

import argparse
import logging
import os
import secrets
import sys
from http.server import ThreadingHTTPServer

from backend.config import DEFAULT_PORT, get_lan_ips
from backend.database import init_db
from backend.handlers import TodoRequestHandler
from backend.window import launch_app_window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("todolist.server")


def run_server(port=DEFAULT_PORT, host="127.0.0.1", token=None, open_window=False):
    """Démarre le serveur HTTP et initialise la base de données."""
    init_db()

    # Configuration de l'authentification par jeton si exposé sur le réseau
    if host != "127.0.0.1":
        active_token = token or os.environ.get("TODOLIST_TOKEN") or secrets.token_urlsafe(24)
        TodoRequestHandler.api_token = active_token
    else:
        active_token = token or os.environ.get("TODOLIST_TOKEN")
        TodoRequestHandler.api_token = active_token

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, TodoRequestHandler)
    local_url = f"http://127.0.0.1:{port}"
    lan_ips = get_lan_ips()

    print(f"======================================================")
    print(f"  🚀 SERVEUR TODOLIST EN LIGNE (Port {port})")
    print(f"======================================================")
    print(f"  Accès local (sur cette machine) :")
    print(f"    👉 {local_url}")

    if host == "0.0.0.0":
        print(f"\n  Accès réseau pour votre équipe de projet :")
        if lan_ips:
            for ip in lan_ips:
                print(f"    👉 http://{ip}:{port}")
        else:
            print(f"    👉 http://<adresse-ip-de-ce-pc>:{port}")

        if TodoRequestHandler.api_token:
            print(f"\n  🔑 Jeton d'accès équipe (Token) :")
            print(f"    👉 {TodoRequestHandler.api_token}")
            print(f"  Partagez cette adresse ET ce jeton avec vos collègues !")
            print(f"  Ils doivent le saisir dans Options > Serveur.")
        print(f"\n  Ils peuvent s'y connecter depuis leur navigateur")
        print(f"  ou depuis l'application ToDoList (Options > Serveur).")
    else:
        print(f"\n  (Mode local uniquement. Pour partager sur votre réseau :")
        print(f"   python3 server.py --share ou ./lancer-serveur-equipe.sh)")

    print(f"======================================================")
    print(f"  Appuyez sur Ctrl+C pour arrêter le serveur.")
    print(f"======================================================")

    if open_window:
        try:
            launch_app_window(local_url)
        except Exception:
            logger.warning("Impossible de lancer la fenêtre native de l'application", exc_info=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur...")
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="Serveur ToDoList")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port d'écoute du serveur HTTP (défaut: 4848)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Hôte d'écoute (défaut: 127.0.0.1)")
    parser.add_argument("--share", "--server", "--public", dest="share", action="store_true", help="Partager sur le réseau local (0.0.0.0)")
    parser.add_argument("--token", type=str, default=None, help="Jeton d'authentification partagé (optionnel)")
    parser.add_argument("--window", action="store_true", help="Ouvrir la fenêtre d'application native")

    args = parser.parse_args()

    host = "0.0.0.0" if args.share else args.host
    run_server(port=args.port, host=host, token=args.token, open_window=args.window)


if __name__ == "__main__":
    main()

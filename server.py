#!/usr/bin/env python3
"""
Serveur HTTP autonome pour l'application ToDoList.
Peut être lancé directement : python3 server.py [--port 4848] [--host 0.0.0.0] [--share]
"""

import sys
from http.server import ThreadingHTTPServer

from backend.config import DEFAULT_PORT, get_lan_ips
from backend.database import init_db
from backend.handlers import TodoRequestHandler
from backend.window import launch_app_window


def run_server(port=DEFAULT_PORT, host="127.0.0.1", open_window=False):
    """Démarre le serveur HTTP et initialise la base de données."""
    init_db()
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, TodoRequestHandler)
    local_url = f"http://127.0.0.1:{port}"
    lan_ips = get_lan_ips()

    print(f"======================================================")
    print(f"  🚀 SERVEUR TODOLIST EN LIGNE (Port {port})")
    print(f"======================================================")
    print(f"  Accès local (sur cette machine) :")
    print(f"    👉 {local_url}")

    if host == "0.0.0.0" or "--share" in sys.argv:
        print(f"\n  Accès réseau pour votre équipe de projet :")
        if lan_ips:
            for ip in lan_ips:
                print(f"    👉 http://{ip}:{port}")
        else:
            print(f"    👉 http://<adresse-ip-de-ce-pc>:{port}")
        print(f"\n  Partagez cette adresse avec vos collègues !")
        print(f"  Ils peuvent s'y connecter depuis leur navigateur")
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

    host = "127.0.0.1"
    if "--host" in sys.argv:
        try:
            idx = sys.argv.index("--host")
            host = sys.argv[idx + 1]
        except (IndexError, ValueError):
            pass
    elif "--share" in sys.argv or "--server" in sys.argv or "--public" in sys.argv:
        host = "0.0.0.0"

    open_win = "--window" in sys.argv
    run_server(port=port, host=host, open_window=open_win)

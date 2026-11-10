#!/usr/bin/env bash
# Script pour lancer le serveur ToDoList partagé pour l'équipe de projet
# Écoute sur toutes les interfaces réseau (0.0.0.0) pour permettre aux camarades de se connecter

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

mkdir -p "$DIR/data"
echo "Lancement du serveur partagé pour l'équipe..."
exec python3 -u "$DIR/server.py" --share "$@"

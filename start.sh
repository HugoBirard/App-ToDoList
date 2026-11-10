#!/usr/bin/env bash
# Lance l'application ToDoList dans sa propre fenêtre native dédiée (style Spotify/VS Code)

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

mkdir -p "$DIR/data"
exec python3 -u "$DIR/main.py" "$@"

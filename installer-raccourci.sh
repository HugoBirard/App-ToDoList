#!/usr/bin/env bash
# Script pour installer le raccourci dans vos applications GNOME et sur votre Bureau

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_SRC="$DIR/ToDoList.desktop"

# Mettre à jour dynamiquement les chemins absolus dans le fichier .desktop
sed -i "s|^Exec=.*|Exec=$DIR/start.sh|" "$DESKTOP_SRC"
sed -i "s|^Icon=.*|Icon=$DIR/static/assets/icon.png|" "$DESKTOP_SRC"
sed -i "s|^Path=.*|Path=$DIR|" "$DESKTOP_SRC"
if ! grep -q "^Path=" "$DESKTOP_SRC"; then
  echo "Path=$DIR" >> "$DESKTOP_SRC"
fi

# Installer les icônes dans les thèmes d'icônes XDG (~/.local/share/icons)
for THEME in "hicolor" "NC"; do
  for RES in "256x256" "128x128" "48x48"; do
    mkdir -p "$HOME/.local/share/icons/$THEME/$RES/apps"
    cp -f "$DIR/static/assets/icon.png" "$HOME/.local/share/icons/$THEME/$RES/apps/todolist.png" 2>/dev/null || true
  done
  mkdir -p "$HOME/.local/share/icons/$THEME/scalable/apps"
  cp -f "$DIR/static/assets/icon.svg" "$HOME/.local/share/icons/$THEME/scalable/apps/todolist.svg" 2>/dev/null || true
  gtk-update-icon-cache -f "$HOME/.local/share/icons/$THEME" 2>/dev/null || true
done

# Rendre exécutables tous les lanceurs
chmod +x "$DIR/main.py" "$DIR/start.sh" "$DIR/server.py" "$DESKTOP_SRC"
gio set "$DESKTOP_SRC" metadata::trusted true 2>/dev/null

# Configurer Nautilus pour permettre l'exécution
gsettings set org.gnome.nautilus.preferences executable-text-activation 'launch' 2>/dev/null || true

# 1. Installer dans le menu système GNOME (raccourci unique, sans doublon)
mkdir -p "$HOME/.local/share/applications"
cp "$DESKTOP_SRC" "$HOME/.local/share/applications/todolist.desktop"
rm -f "$HOME/.local/share/applications/ToDoList.desktop"
chmod +x "$HOME/.local/share/applications/todolist.desktop"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null

# 2. Installer sur le Bureau si le dossier existe
for FOLDER in "Desktop" "Bureau"; do
  if [ -d "$HOME/$FOLDER" ]; then
    cp "$DESKTOP_SRC" "$HOME/$FOLDER/ToDoList.desktop"
    chmod +x "$HOME/$FOLDER/ToDoList.desktop"
    gio set "$HOME/$FOLDER/ToDoList.desktop" metadata::trusted true 2>/dev/null
    echo "Raccourci installé sur le Bureau (~/$FOLDER/ToDoList.desktop)"
  fi
done

echo "✅ Raccourci installé avec succès !"
echo "Vous pouvez lancer 'ToDo List' directement depuis vos applications système ou en double-cliquant sur ToDoList.desktop."

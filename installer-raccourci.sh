#!/usr/bin/env bash
# Script pour installer le raccourci dans vos applications GNOME et sur votre Bureau

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_SRC="$DIR/ToDoList.desktop"

# Mettre à jour dynamiquement les chemins et l'icône dans le fichier .desktop
sed -i "s|^Exec=.*|Exec=$DIR/start.sh|" "$DESKTOP_SRC"
sed -i "s|^Icon=.*|Icon=$DIR/static/assets/icon.png|" "$DESKTOP_SRC"
sed -i "s|^Path=.*|Path=$DIR|" "$DESKTOP_SRC"
if ! grep -q "^Path=" "$DESKTOP_SRC"; then
  echo "Path=$DIR" >> "$DESKTOP_SRC"
fi

# 1. S'assurer que le thème hicolor a son index pour la génération de cache
mkdir -p "$HOME/.local/share/icons/hicolor"
if [ ! -f "$HOME/.local/share/icons/hicolor/index.theme" ] && [ -f "/usr/share/icons/hicolor/index.theme" ]; then
  cp -f "/usr/share/icons/hicolor/index.theme" "$HOME/.local/share/icons/hicolor/index.theme"
fi

# 2. Installer les icônes dans les répertoires standards XDG & Pixmaps
mkdir -p "$HOME/.local/share/pixmaps" "$HOME/.icons"
cp -f "$DIR/static/assets/icon.png" "$HOME/.local/share/pixmaps/todolist.png" 2>/dev/null || true
cp -f "$DIR/static/assets/icon.svg" "$HOME/.local/share/pixmaps/todolist.svg" 2>/dev/null || true
cp -f "$DIR/static/assets/icon.png" "$HOME/.local/share/pixmaps/ToDoList.png" 2>/dev/null || true
cp -f "$DIR/static/assets/icon.svg" "$HOME/.local/share/pixmaps/ToDoList.svg" 2>/dev/null || true
cp -f "$DIR/static/assets/icon.png" "$HOME/.icons/todolist.png" 2>/dev/null || true
cp -f "$DIR/static/assets/icon.svg" "$HOME/.icons/todolist.svg" 2>/dev/null || true
cp -f "$DIR/static/assets/icon.png" "$HOME/.icons/ToDoList.png" 2>/dev/null || true

# 3. Installer dans les thèmes d'icônes actifs (hicolor, NC, Papirus)
for THEME in "hicolor" "NC" "Papirus" "Papirus-Dark"; do
  for RES in "256x256" "128x128" "64x64" "48x48" "32x32"; do
    mkdir -p "$HOME/.local/share/icons/$THEME/$RES/apps"
    cp -f "$DIR/static/assets/icon.png" "$HOME/.local/share/icons/$THEME/$RES/apps/todolist.png" 2>/dev/null || true
    cp -f "$DIR/static/assets/icon.png" "$HOME/.local/share/icons/$THEME/$RES/apps/ToDoList.png" 2>/dev/null || true
  done
  mkdir -p "$HOME/.local/share/icons/$THEME/scalable/apps"
  cp -f "$DIR/static/assets/icon.svg" "$HOME/.local/share/icons/$THEME/scalable/apps/todolist.svg" 2>/dev/null || true
  cp -f "$DIR/static/assets/icon.svg" "$HOME/.local/share/icons/$THEME/scalable/apps/ToDoList.svg" 2>/dev/null || true
  
  if [ -f "$HOME/.local/share/icons/$THEME/index.theme" ]; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/$THEME" 2>/dev/null || true
  fi
done

# 4. Rendre exécutables tous les lanceurs et associer l'icône personnalisée à Nautilus
chmod +x "$DIR/main.py" "$DIR/start.sh" "$DIR/server.py" "$DESKTOP_SRC"
gio set "$DESKTOP_SRC" metadata::trusted true 2>/dev/null || true
gio set "$DESKTOP_SRC" metadata::custom-icon "file://$DIR/static/assets/icon.png" 2>/dev/null || true

# Configurer Nautilus pour permettre l'exécution des scripts/lanceurs
gsettings set org.gnome.nautilus.preferences executable-text-activation 'launch' 2>/dev/null || true

# 5. Installer dans le menu système GNOME (raccourci unique, sans doublon)
mkdir -p "$HOME/.local/share/applications"
cp -f "$DESKTOP_SRC" "$HOME/.local/share/applications/todolist.desktop"
rm -f "$HOME/.local/share/applications/ToDoList.desktop"
chmod +x "$HOME/.local/share/applications/todolist.desktop"
gio set "$HOME/.local/share/applications/todolist.desktop" metadata::trusted true 2>/dev/null || true
gio set "$HOME/.local/share/applications/todolist.desktop" metadata::custom-icon "file://$DIR/static/assets/icon.png" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

# 6. Installer sur le Bureau si un dossier Bureau ou Desktop existe
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "")"
if [ -n "$DESKTOP_DIR" ] && [ "$DESKTOP_DIR" != "$HOME" ] && [ -d "$DESKTOP_DIR" ]; then
  cp -f "$DESKTOP_SRC" "$DESKTOP_DIR/ToDoList.desktop"
  chmod +x "$DESKTOP_DIR/ToDoList.desktop"
  gio set "$DESKTOP_DIR/ToDoList.desktop" metadata::trusted true 2>/dev/null || true
  gio set "$DESKTOP_DIR/ToDoList.desktop" metadata::custom-icon "file://$DIR/static/assets/icon.png" 2>/dev/null || true
fi

for FOLDER in "Desktop" "Bureau"; do
  if [ -d "$HOME/$FOLDER" ] && [ "$HOME/$FOLDER" != "$HOME" ]; then
    cp -f "$DESKTOP_SRC" "$HOME/$FOLDER/ToDoList.desktop"
    chmod +x "$HOME/$FOLDER/ToDoList.desktop"
    gio set "$HOME/$FOLDER/ToDoList.desktop" metadata::trusted true 2>/dev/null || true
    gio set "$HOME/$FOLDER/ToDoList.desktop" metadata::custom-icon "file://$DIR/static/assets/icon.png" 2>/dev/null || true
  fi
done

echo "✅ Raccourci et icônes installés avec succès !"
echo "Vous pouvez lancer 'ToDoList' directement depuis vos applications système avec son logo vectoriel."

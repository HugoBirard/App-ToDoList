#!/usr/bin/env bash
# ==============================================================================
# Script de mise à jour automatique en 1 clic pour ToDoList
# Préserve à 100% vos données et tâches personnelles dans data/todolist.db
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "🔄 Recherche de mises à jour pour ToDoList..."

if [ ! -d ".git" ]; then
  echo "⚠️ Ce dossier n'est pas un dépôt Git."
  echo "Téléchargez la dernière version depuis GitHub et conservez le dossier 'data/'."
  exit 1
fi

# Sauvegarde préventive de sécurité de la base de données
if [ -f "data/todolist.db" ]; then
  mkdir -p "data"
  cp -f "data/todolist.db" "data/todolist.db.pre-update.bak"
  echo "🛡️ Sauvegarde de sécurité créée : data/todolist.db.pre-update.bak"
fi

# Récupération des dernières modifications
echo "📥 Téléchargement des dernières améliorations..."
git pull

# Rafraîchissement des raccourcis et icônes
if [ -f "installer-raccourci.sh" ]; then
  echo "⚡ Rafraîchissement des raccourcis..."
  ./installer-raccourci.sh >/dev/null 2>&1 || true
fi

echo ""
echo "✅ ToDoList a été mis à jour avec succès !"
echo "Vos tâches, dossiers et préférences sont intacts."
echo "Vous pouvez relancer l'application : ./start.sh"

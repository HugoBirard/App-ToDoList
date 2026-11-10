/**
 * Composant de gestion de la synchronisation Multi-PC et de l'emplacement de stockage.
 */

import { api } from '../api.js';
import { state } from '../state.js';
import { showConfirmDialog, showNotificationDialog } from './modals.js';

let lastKnownMtime = 0;
let lastKnownTaskCount = -1;
let lastKnownFolderCount = -1;
let isSyncing = false;

export async function fetchStorageInfo() {
  const info = await api('/api/sync/status');
  if (info) {
    updateStorageDisplay(info);
  }
  return info;
}

export function updateStorageDisplay(info) {
  const pathText = document.getElementById('sync-current-path-text');
  const badge = document.getElementById('sync-status-badge');
  const statTasks = document.getElementById('sync-stat-tasks');
  const statFolders = document.getElementById('sync-stat-folders');
  const statSize = document.getElementById('sync-stat-size');
  const statMtime = document.getElementById('sync-stat-mtime');

  if (pathText) pathText.textContent = info.current_db_path || 'Inconnu';
  
  if (badge) {
    if (info.is_custom) {
      badge.textContent = 'Partagé / Cloud';
      badge.className = 'sync-badge custom';
    } else {
      badge.textContent = 'Local (Défaut)';
      badge.className = 'sync-badge local';
    }
  }

  if (statTasks) statTasks.textContent = `${info.task_count || 0} tâche(s)`;
  if (statFolders) statFolders.textContent = `${info.folder_count || 0} dossier(s)`;
  
  if (statSize) {
    const kb = Math.round((info.file_size || 0) / 1024);
    statSize.textContent = `${kb} Ko`;
  }

  if (statMtime && info.last_modified) {
    const d = new Date(info.last_modified * 1000);
    statMtime.textContent = `Mis à jour le ${d.toLocaleDateString('fr-FR')} à ${d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`;
  }
}

export function initSyncUI(loadDataCallback) {
  const tabAppearanceBtn = document.getElementById('modal-tab-btn-appearance');
  const tabSyncBtn = document.getElementById('modal-tab-btn-sync');
  const tabDiscordBtn = document.getElementById('modal-tab-btn-discord');

  const paneAppearance = document.getElementById('tab-pane-appearance');
  const paneSync = document.getElementById('tab-pane-sync');
  const paneDiscord = document.getElementById('tab-pane-discord');
  const themeActions = document.getElementById('theme-modal-actions');

  // Gestion des onglets
  const switchTab = (activeTab) => {
    [tabAppearanceBtn, tabSyncBtn, tabDiscordBtn].forEach(b => b?.classList.remove('active'));
    [paneAppearance, paneSync, paneDiscord].forEach(p => p?.classList.add('hidden'));

    if (activeTab === 'appearance') {
      tabAppearanceBtn?.classList.add('active');
      paneAppearance?.classList.remove('hidden');
      if (themeActions) themeActions.style.display = 'flex';
    } else if (activeTab === 'sync') {
      tabSyncBtn?.classList.add('active');
      paneSync?.classList.remove('hidden');
      if (themeActions) themeActions.style.display = 'none';
      fetchStorageInfo();
    } else if (activeTab === 'discord') {
      tabDiscordBtn?.classList.add('active');
      paneDiscord?.classList.remove('hidden');
      if (themeActions) themeActions.style.display = 'none';
    }
  };

  if (tabAppearanceBtn) tabAppearanceBtn.onclick = () => switchTab('appearance');
  if (tabSyncBtn) tabSyncBtn.onclick = () => switchTab('sync');
  if (tabDiscordBtn) tabDiscordBtn.onclick = () => switchTab('discord');

  // Copier le chemin actif
  const copyBtn = document.getElementById('sync-copy-path-btn');
  if (copyBtn) {
    copyBtn.onclick = async () => {
      const pathText = document.getElementById('sync-current-path-text')?.textContent;
      if (pathText) {
        try {
          await navigator.clipboard.writeText(pathText);
          await showNotificationDialog({
            title: "Chemin copié",
            message: "Le chemin de la base a été copié dans votre presse-papier.",
            icon: "check"
          });
        } catch {
          // Fallback silencieux
        }
      }
    };
  }

  // Raccourcis rapides (chips)
  document.querySelectorAll('.sync-chip').forEach(chip => {
    chip.onclick = () => {
      const pathInput = document.getElementById('sync-path-input');
      const targetPath = chip.getAttribute('data-path');
      if (pathInput && targetPath) {
        pathInput.value = targetPath;
      }
    };
  });

  // Bouton Parcourir
  const browseBtn = document.getElementById('sync-browse-btn');
  if (browseBtn) {
    browseBtn.onclick = async () => {
      const res = await api('/api/storage/browse', 'POST');
      if (res && res.path) {
        const pathInput = document.getElementById('sync-path-input');
        if (pathInput) pathInput.value = res.path;
      }
    };
  }

  // Bouton Connecter / Utiliser
  const connectBtn = document.getElementById('sync-connect-btn');
  if (connectBtn) {
    connectBtn.onclick = async () => {
      const pathInput = document.getElementById('sync-path-input');
      const targetPath = pathInput ? pathInput.value.trim() : '';
      if (!targetPath) {
        await showNotificationDialog({
          title: "Chemin requis",
          message: "Veuillez spécifier le chemin vers le fichier de base de données partagée.",
          icon: "info"
        });
        return;
      }

      const res = await api('/api/storage/change-path', 'POST', {
        target_path: targetPath,
        action: 'connect'
      });

      if (res && res.success) {
        updateStorageDisplay(res.info);
        if (loadDataCallback) await loadDataCallback();
        await showNotificationDialog({
          title: "Base connectée avec succès",
          message: "L'application utilise désormais cette base de données partagée.",
          icon: "check"
        });
      } else {
        await showNotificationDialog({
          title: "Erreur de connexion",
          message: "Impossible de connecter cet emplacement. Vérifiez les droits d'accès.",
          icon: "x"
        });
      }
    };
  }

  // Bouton Déplacer / Migrer
  const migrateBtn = document.getElementById('sync-migrate-btn');
  if (migrateBtn) {
    migrateBtn.onclick = async () => {
      const pathInput = document.getElementById('sync-path-input');
      const targetPath = pathInput ? pathInput.value.trim() : '';
      if (!targetPath) {
        await showNotificationDialog({
          title: "Chemin requis",
          message: "Veuillez spécifier le dossier de destination partagé.",
          icon: "info"
        });
        return;
      }

      const confirmed = await showConfirmDialog({
        title: "Déplacer les données",
        message: "Vos tâches et dossiers actuels vont être copiés vers cet emplacement partagé. Continuer ?",
        confirmText: "Déplacer",
        cancelText: "Annuler",
        icon: "folder"
      });

      if (!confirmed) return;

      const res = await api('/api/storage/change-path', 'POST', {
        target_path: targetPath,
        action: 'migrate'
      });

      if (res && res.success) {
        updateStorageDisplay(res.info);
        if (loadDataCallback) await loadDataCallback();
        await showNotificationDialog({
          title: "Données déplacées",
          message: "Vos données ont été copiées vers l'emplacement partagé et sont maintenant synchronisées !",
          icon: "check"
        });
      }
    };
  }

  // Bouton Réinitialiser au stockage local
  const resetBtn = document.getElementById('sync-reset-default-btn');
  if (resetBtn) {
    resetBtn.onclick = async () => {
      const confirmed = await showConfirmDialog({
        title: "Revenir au stockage local",
        message: "Voulez-vous déconnecter l'emplacement partagé et revenir à la base locale par défaut de ce PC ?",
        confirmText: "Revenir à zéro",
        cancelText: "Annuler",
        icon: "rotate-ccw"
      });

      if (!confirmed) return;

      const res = await api('/api/storage/change-path', 'POST', { action: 'reset' });
      if (res && res.success) {
        updateStorageDisplay(res.info);
        if (loadDataCallback) await loadDataCallback();
        await showNotificationDialog({
          title: "Stockage réinitialisé",
          message: "L'application utilise à nouveau le stockage local par défaut de ce PC.",
          icon: "check"
        });
      }
    };
  }

  // Télécharger export JSON
  const exportBtn = document.getElementById('sync-export-json-btn');
  if (exportBtn) {
    exportBtn.onclick = async () => {
      const backup = await api('/api/storage/export');
      if (!backup) return;

      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const dateStr = new Date().toISOString().slice(0, 10);
      a.href = url;
      a.download = `todolist-backup-${dateStr}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };
  }

  // Importer JSON
  const importBtn = document.getElementById('sync-import-json-btn');
  const filePicker = document.getElementById('sync-file-picker');
  if (importBtn && filePicker) {
    importBtn.onclick = () => filePicker.click();

    filePicker.onchange = async () => {
      const file = filePicker.files[0];
      if (!file) return;

      try {
        const text = await file.text();
        const json = JSON.parse(text);

        const shouldMerge = await showConfirmDialog({
          title: "Méthode d'importation",
          message: "Voulez-vous FUSIONNER ces tâches avec vos listes actuelles (recommandé) ou REMPLACER complètement vos listes ?",
          confirmText: "Fusionner",
          cancelText: "Remplacer tout",
          icon: "folder"
        });

        const mode = shouldMerge ? 'merge' : 'replace';
        const res = await api('/api/storage/import', 'POST', { data: json, mode });
        if (res && res.success) {
          if (loadDataCallback) await loadDataCallback();
          await showNotificationDialog({
            title: "Importation terminée",
            message: `Les listes ont été importées avec succès (Mode : ${mode === 'merge' ? 'Fusion' : 'Remplacement'}).`,
            icon: "check"
          });
        }
      } catch (e) {
        await showNotificationDialog({
          title: "Fichier invalide",
          message: "Le fichier sélectionné n'est pas un fichier de sauvegarde ToDoList valide.",
          icon: "x"
        });
      } finally {
        filePicker.value = '';
      }
    };
  }
}

/**
 * Surveillance automatique des modifications distantes en arrière-plan (Multi-PC polling).
 */
export function initAutoSyncWatcher(loadDataCallback) {
  async function checkForUpdates() {
    if (isSyncing) return;
    
    // Ne pas rafraîchir si l'utilisateur est en train d'éditer une tâche au clavier
    if (document.querySelector('.edit-task-input')) return;

    try {
      isSyncing = true;
      const status = await api('/api/sync/check-updates');
      if (!status) return;

      const mtime = status.last_modified || 0;
      const tasks = status.task_count ?? -1;
      const folders = status.folder_count ?? -1;

      if (lastKnownMtime > 0) {
        // Si la base a été modifiée par un autre PC
        if (mtime > lastKnownMtime || tasks !== lastKnownTaskCount || folders !== lastKnownFolderCount) {
          if (loadDataCallback) {
            await loadDataCallback(true); // silent reload
          }
        }
      }

      lastKnownMtime = mtime;
      lastKnownTaskCount = tasks;
      lastKnownFolderCount = folders;
    } catch {
      // Ignorer les erreurs réseau temporaires
    } finally {
      isSyncing = false;
    }
  }

  // Vérifier toutes les 4 secondes
  setInterval(checkForUpdates, 4000);

  // Vérifier immédiatement quand la fenêtre reprend le focus
  window.addEventListener('focus', checkForUpdates);
}

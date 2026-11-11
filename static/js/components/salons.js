/**
 * Composant de gestion des Salons / Espaces de travail partagés.
 * Permet d'isoler les dossiers et tâches par projet ou groupe,
 * avec webhook Discord dédié par salon, export/partage ciblé,
 * synchronisation automatique en direct et compteur de membres connectés.
 */

import { state, getActiveSalon, escapeHtml } from '../state.js';
import { renderIcon } from '../icons.js';
import { api } from '../api.js';
import { renderFolders, selectQuickView } from './folders.js';
import { renderTasks } from './tasks.js';
import { showConfirmDialog, showNotificationDialog } from './modals.js';

let selectedIconForSalon = 'folder';
let selectedColorForSalon = '#4f46e5';

// Identifiant unique du client pour le comptage de présence en ligne
const CLIENT_ID = (function() {
  let id = sessionStorage.getItem('todolist_client_id');
  if (!id) {
    id = 'user_' + Math.random().toString(36).substring(2, 10);
    sessionStorage.setItem('todolist_client_id', id);
  }
  return id;
})();

let currentSalonVersion = null;
let heartbeatIntervalId = null;
let globalLoadDataCallback = null;

export function initSalonUI(loadDataCallback = null) {
  globalLoadDataCallback = loadDataCallback;

  // Récupérer le salon sauvegardé dans localStorage si valide
  const savedSalonId = parseInt(localStorage.getItem('todolist_active_salon_id'), 10);
  if (savedSalonId && state.salons.some(s => s.id === savedSalonId)) {
    state.currentSalonId = savedSalonId;
  } else if (state.salons.length > 0) {
    state.currentSalonId = state.salons[0].id;
  }

  // Déroulant du sélecteur de salon
  const trigger = document.getElementById('salon-dropdown-trigger');
  const menu = document.getElementById('salon-dropdown-menu');

  if (trigger && menu) {
    trigger.onclick = (e) => {
      e.stopPropagation();
      menu.classList.toggle('hidden');
    };

    document.addEventListener('click', (e) => {
      if (!e.target.closest('#salon-dropdown-menu') && !e.target.closest('#salon-dropdown-trigger')) {
        menu.classList.add('hidden');
      }
    });
  }

  // Bouton création rapide "+" dans l'en-tête de la barre latérale
  const quickAddBtn = document.getElementById('quick-add-salon-btn');
  if (quickAddBtn) {
    quickAddBtn.onclick = (e) => {
      e.stopPropagation();
      if (menu) menu.classList.add('hidden');
      openAddSalonModal();
    };
  }

  // Bouton Gérer le salon
  const manageBtn = document.getElementById('manage-salon-btn');
  if (manageBtn) {
    manageBtn.onclick = () => {
      const active = getActiveSalon();
      if (active) openManageSalonModal(active.id);
    };
  }

  // Bouton Nouveau salon dans le menu déroulant
  const createBtn = document.getElementById('btn-create-salon');
  if (createBtn) {
    createBtn.onclick = (e) => {
      e.stopPropagation();
      if (menu) menu.classList.add('hidden');
      openAddSalonModal();
    };
  }

  // Bouton Importer un salon
  const importBtn = document.getElementById('btn-import-salon');
  const importInput = document.getElementById('salon-import-file-input');
  if (importBtn && importInput) {
    importBtn.onclick = () => {
      if (menu) menu.classList.add('hidden');
      importInput.click();
    };

    importInput.onchange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (data.scope !== 'salon' && !data.salon) {
          showNotificationDialog({
            title: "Fichier invalide",
            message: "Le fichier sélectionné n'est pas un fichier de salon ToDoList valide (.tdl).",
            icon: "alert"
          });
          return;
        }

        const res = await api('/api/salons/import', 'POST', data);
        if (res && res.id) {
          state.salons.push(res);
          // Recharger les données complètes
          if (globalLoadDataCallback) {
            await globalLoadDataCallback(true);
          } else {
            const freshData = await api('/api/data', 'GET');
            if (freshData) {
              state.salons = freshData.salons || [];
              state.folders = freshData.folders || [];
              state.tasks = freshData.tasks || [];
            }
          }
          state.currentSalonId = res.id;
          localStorage.setItem('todolist_active_salon_id', res.id);
          renderSalons();
          renderFolders();
          selectQuickView('all');
          sendSalonHeartbeat();
          showNotificationDialog({
            title: "Salon importé !",
            message: `Le salon « ${res.name} » a été importé avec succès avec tous ses dossiers et tâches.`,
            icon: "check"
          });
        }
      } catch (err) {
        showNotificationDialog({
          title: "Erreur d'import",
          message: "Impossible de lire le fichier de salon : " + err.message,
          icon: "alert"
        });
      } finally {
        importInput.value = '';
      }
    };
  }

  // Fermeture des modales salon via bouton fermer
  document.querySelectorAll('#add-salon-modal .close-modal-btn, #manage-salon-modal .close-modal-btn').forEach(btn => {
    btn.onclick = () => {
      document.getElementById('add-salon-modal')?.classList.add('hidden');
      document.getElementById('manage-salon-modal')?.classList.add('hidden');
    };
  });

  // Fermeture sur clic arrière-plan
  const addModal = document.getElementById('add-salon-modal');
  if (addModal) {
    addModal.addEventListener('click', (e) => {
      if (e.target === addModal) addModal.classList.add('hidden');
    });
  }
  const manageModal = document.getElementById('manage-salon-modal');
  if (manageModal) {
    manageModal.addEventListener('click', (e) => {
      if (e.target === manageModal) manageModal.classList.add('hidden');
    });
  }

  setupAddSalonForm();
  setupManageSalonModal();
  renderSalons();

  // Démarrer la boucle de synchronisation en direct et battement de cœur (heartbeat)
  if (!heartbeatIntervalId) {
    heartbeatIntervalId = setInterval(sendSalonHeartbeat, 3000);
    window.addEventListener('focus', sendSalonHeartbeat);
  }
  sendSalonHeartbeat();
}

/**
 * Envoie le battement de cœur périodique du client pour maintenir sa présence en ligne
 * et synchroniser automatiquement les modifications faites par les autres membres du salon.
 */
export async function sendSalonHeartbeat() {
  const active = getActiveSalon();
  if (!active) return;

  try {
    const res = await api(`/api/salons/${active.id}/heartbeat`, 'POST', {
      client_id: CLIENT_ID,
      version: currentSalonVersion
    });

    if (res) {
      // Mettre à jour les comptes des membres sur tous les salons
      if (res.all_salons_counts) {
        state.salons.forEach(s => {
          if (res.all_salons_counts[s.id] !== undefined) {
            s.active_members_count = res.all_salons_counts[s.id];
          }
        });
      }

      // Mettre à jour le badge d'en-tête du salon actif
      const presenceCountEl = document.getElementById('salon-presence-count');
      if (presenceCountEl) {
        const count = Math.max(res.active_members_count || 1, 1);
        presenceCountEl.textContent = count;
        presenceCountEl.parentElement?.setAttribute('title', `${count} membre(s) connecté(s) à ce salon`);
      }

      // Mettre à jour le texte dans la modale de gestion si ouverte
      const managePresenceText = document.getElementById('manage-salon-presence-text');
      if (managePresenceText) {
        const count = Math.max(res.active_members_count || 1, 1);
        managePresenceText.textContent = `${count} personne${count > 1 ? 's' : ''} en ligne`;
      }

      // Si le salon a été mis à jour par un autre membre (création/suppression/coche de tâche ou dossier)
      if (res.needs_refresh) {
        // Ne pas interrompre si l'utilisateur est en train de modifier une tâche au clavier
        const isEditing = document.querySelector('.edit-task-input') ||
                          (document.activeElement && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName));
        if (!isEditing) {
          currentSalonVersion = res.version;
          if (globalLoadDataCallback) {
            await globalLoadDataCallback(true); // silent reload
          }
        }
      } else {
        currentSalonVersion = res.version;
      }
    }
  } catch (err) {
    // Ignorer les erreurs réseau temporaires
  }
}

/**
 * Met à jour le sélecteur de salon et le menu déroulant.
 */
export function renderSalons() {
  const active = getActiveSalon();
  if (!active && state.salons.length > 0) {
    state.currentSalonId = state.salons[0].id;
  }

  const current = getActiveSalon();

  // Mettre à jour l'en-tête du sélecteur
  const nameEl = document.getElementById('salon-active-name');
  const colorEl = document.getElementById('salon-active-color');
  const discordPill = document.getElementById('salon-discord-indicator');
  const presenceCountEl = document.getElementById('salon-presence-count');

  if (current) {
    if (nameEl) nameEl.textContent = current.name;
    if (colorEl) colorEl.style.backgroundColor = current.color || '#4f46e5';
    if (presenceCountEl) {
      const pCount = Math.max(current.active_members_count || 1, 1);
      presenceCountEl.textContent = pCount;
      presenceCountEl.parentElement?.setAttribute('title', `${pCount} membre(s) connecté(s) à ce salon`);
    }
    if (discordPill) {
      if (current.discord_enabled && current.discord_webhook_configured) {
        discordPill.classList.remove('hidden');
      } else {
        discordPill.classList.add('hidden');
      }
    }
  }

  // Remplir le menu déroulant
  const list = document.getElementById('salon-dropdown-list');
  if (!list) return;

  list.innerHTML = '';

  state.salons.forEach(s => {
    const isCurrent = current && s.id === current.id;
    const folderCount = state.folders.filter(f => f.salon_id === s.id).length;
    const membersCount = s.active_members_count ?? (isCurrent ? 1 : 0);

    const item = document.createElement('div');
    item.className = `salon-menu-item ${isCurrent ? 'active' : ''}`;
    
    const discordBadge = (s.discord_enabled && s.discord_webhook_configured)
      ? `<span class="salon-mini-discord-badge" title="Discord lié">${renderIcon('message-square')}</span>`
      : '';

    const presenceBadge = `<span class="salon-item-presence ${membersCount > 0 ? 'online' : ''}" title="${membersCount} membre(s) connecté(s)"><span class="presence-mini-dot"></span> ${membersCount} en ligne</span>`;

    item.innerHTML = `
      <div class="salon-item-left">
        <span class="salon-item-color-dot" style="background-color: ${s.color || '#4f46e5'};"></span>
        <span class="salon-item-icon">${renderIcon(s.icon || 'folder')}</span>
        <span class="salon-item-name">${escapeHtml(s.name)}</span>
        ${discordBadge}
      </div>
      <div class="salon-item-right">
        ${presenceBadge}
        <span class="salon-item-count">${folderCount} doss.</span>
        ${isCurrent ? `<span class="salon-check">${renderIcon('check')}</span>` : ''}
      </div>
    `;

    item.onclick = (e) => {
      e.stopPropagation();
      state.currentSalonId = s.id;
      localStorage.setItem('todolist_active_salon_id', s.id);
      document.getElementById('salon-dropdown-menu')?.classList.add('hidden');
      renderSalons();
      renderFolders();
      selectQuickView('all');
      sendSalonHeartbeat();
    };

    list.appendChild(item);
  });
}

/**
 * Configuration du formulaire de création de salon.
 */
function setupAddSalonForm() {
  const form = document.getElementById('add-salon-form');
  if (!form) return;

  // Choix des icônes dans la modale d'ajout
  const iconPicker = document.getElementById('add-salon-icon-picker');
  if (iconPicker) {
    iconPicker.querySelectorAll('.icon-opt').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        iconPicker.querySelectorAll('.icon-opt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedIconForSalon = btn.dataset.icon || 'folder';
      };
    });
  }

  // Choix des couleurs
  const colorPicker = document.getElementById('add-salon-color-picker');
  if (colorPicker) {
    colorPicker.querySelectorAll('.color-opt').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        colorPicker.querySelectorAll('.color-opt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedColorForSalon = btn.dataset.color || '#4f46e5';
      };
    });
  }

  form.onsubmit = async (e) => {
    e.preventDefault();
    const nameInput = document.getElementById('add-salon-name-input');
    const descInput = document.getElementById('add-salon-desc-input');
    const webhookInput = document.getElementById('add-salon-webhook-input');
    const submitBtn = form.querySelector('button[type="submit"]');

    const name = nameInput?.value.trim();
    if (!name) return;

    let webhookUrl = (webhookInput?.value || '').trim();
    if (webhookUrl && !webhookUrl.startsWith('http://') && !webhookUrl.startsWith('https://')) {
      webhookUrl = 'https://' + webhookUrl;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Création en cours...';
    }

    try {
      const payload = {
        name: name,
        description: descInput?.value.trim() || '',
        icon: selectedIconForSalon,
        color: selectedColorForSalon,
        discord_webhook_url: webhookUrl,
        discord_enabled: webhookUrl ? 1 : 0
      };

      const res = await api('/api/salons', 'POST', payload);
      if (res && res.id) {
        state.salons.push(res);
        state.currentSalonId = res.id;
        localStorage.setItem('todolist_active_salon_id', res.id);
        document.getElementById('add-salon-modal')?.classList.add('hidden');
        form.reset();

        if (globalLoadDataCallback) {
          await globalLoadDataCallback(true);
        } else {
          renderSalons();
          renderFolders();
          selectQuickView('all');
        }

        sendSalonHeartbeat();

        showNotificationDialog({
          title: "Salon créé !",
          message: `Le salon « ${res.name} » a été créé avec succès et sélectionné.`,
          icon: "check"
        });
      } else {
        showNotificationDialog({
          title: "Erreur",
          message: "Impossible de créer le salon. Veuillez vérifier le nom saisi.",
          icon: "alert"
        });
      }
    } catch (err) {
      showNotificationDialog({
        title: "Erreur",
        message: "Une erreur est survenue lors de la création du salon : " + err.message,
        icon: "alert"
      });
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Créer le salon';
      }
    }
  };
}

export function openAddSalonModal() {
  const modal = document.getElementById('add-salon-modal');
  if (!modal) return;
  const form = document.getElementById('add-salon-form');
  if (form) form.reset();

  selectedIconForSalon = 'folder';
  selectedColorForSalon = '#4f46e5';

  const iconPicker = document.getElementById('add-salon-icon-picker');
  if (iconPicker) {
    iconPicker.querySelectorAll('.icon-opt').forEach(btn => {
      btn.classList.toggle('active', (btn.dataset.icon || 'folder') === 'folder');
    });
  }
  const colorPicker = document.getElementById('add-salon-color-picker');
  if (colorPicker) {
    colorPicker.querySelectorAll('.color-opt').forEach(btn => {
      btn.classList.toggle('active', (btn.dataset.color || '#4f46e5') === '#4f46e5');
    });
  }

  modal.classList.remove('hidden');
  setTimeout(() => {
    document.getElementById('add-salon-name-input')?.focus();
  }, 50);
}

/**
 * Configuration de la modale de gestion du salon actif.
 */
function setupManageSalonModal() {
  const modal = document.getElementById('manage-salon-modal');
  if (!modal) return;

  // Gestion des onglets de la modale salon
  modal.querySelectorAll('.salon-modal-tab').forEach(tab => {
    tab.onclick = () => {
      modal.querySelectorAll('.salon-modal-tab').forEach(t => t.classList.remove('active'));
      modal.querySelectorAll('.salon-tab-pane').forEach(p => p.classList.add('hidden'));

      tab.classList.add('active');
      const paneId = tab.dataset.pane;
      document.getElementById(paneId)?.classList.remove('hidden');
    };
  });

  // Enregistrer les infos du salon (Nom, Description, Couleur, Icône)
  const saveInfoBtn = document.getElementById('salon-save-info-btn');
  if (saveInfoBtn) {
    saveInfoBtn.onclick = async () => {
      const active = getActiveSalon();
      if (!active) return;

      const name = document.getElementById('manage-salon-name')?.value.trim();
      const desc = document.getElementById('manage-salon-desc')?.value.trim();

      if (!name) return;

      const res = await api(`/api/salons/${active.id}`, 'PUT', {
        name: name,
        description: desc
      });

      if (res) {
        const idx = state.salons.findIndex(s => s.id === active.id);
        if (idx !== -1) state.salons[idx] = res;
        renderSalons();
        showNotificationDialog({
          title: "Salon mis à jour",
          message: "Les modifications du salon ont été enregistrées avec succès.",
          icon: "check"
        });
      }
    };
  }

  // Tester le webhook Discord spécifique à ce salon
  const testDiscordBtn = document.getElementById('salon-discord-test-btn');
  const discordFeedback = document.getElementById('salon-discord-feedback');
  if (testDiscordBtn) {
    testDiscordBtn.onclick = async () => {
      const active = getActiveSalon();
      if (!active) return;

      const urlInput = document.getElementById('manage-salon-discord-url');
      const authorInput = document.getElementById('manage-salon-discord-author');

      let webhookUrl = (urlInput?.value || '').trim();
      if (webhookUrl && !webhookUrl.startsWith('••••') && !webhookUrl.startsWith('http://') && !webhookUrl.startsWith('https://')) {
        webhookUrl = 'https://' + webhookUrl;
        if (urlInput) urlInput.value = webhookUrl;
      }

      testDiscordBtn.disabled = true;
      testDiscordBtn.textContent = "Test en cours...";

      try {
        const res = await api(`/api/salons/${active.id}/discord/test`, 'POST', {
          webhook_url: webhookUrl,
          author_name: authorInput?.value.trim() || 'Équipe'
        });

        if (discordFeedback) {
          discordFeedback.classList.remove('hidden');
          if (res && res.success) {
            discordFeedback.className = 'discord-feedback success';
            discordFeedback.textContent = "✅ Test réussi ! Le salon Discord a bien reçu le message.";
            // Activer le toggle si pas déjà fait
            const toggle = document.getElementById('manage-salon-discord-enabled');
            if (toggle) toggle.checked = true;
          } else {
            discordFeedback.className = 'discord-feedback error';
            discordFeedback.textContent = `❌ Échec : ${res?.message || 'Vérifiez votre URL'}`;
          }
        }
      } catch (err) {
        if (discordFeedback) {
          discordFeedback.classList.remove('hidden');
          discordFeedback.className = 'discord-feedback error';
          discordFeedback.textContent = `❌ Erreur : ${err.message}`;
        }
      } finally {
        testDiscordBtn.disabled = false;
        testDiscordBtn.textContent = "Envoyer un message test";
      }
    };
  }

  // Enregistrer les réglages Discord du salon
  const saveDiscordBtn = document.getElementById('salon-discord-save-btn');
  if (saveDiscordBtn) {
    saveDiscordBtn.onclick = async () => {
      const active = getActiveSalon();
      if (!active) return;

      const toggle = document.getElementById('manage-salon-discord-enabled');
      const urlInput = document.getElementById('manage-salon-discord-url');
      const authorInput = document.getElementById('manage-salon-discord-author');

      let webhookUrl = (urlInput?.value || '').trim();
      if (webhookUrl && !webhookUrl.startsWith('••••') && !webhookUrl.startsWith('http://') && !webhookUrl.startsWith('https://')) {
        webhookUrl = 'https://' + webhookUrl;
        if (urlInput) urlInput.value = webhookUrl;
      }

      const payload = {
        discord_enabled: toggle?.checked ? 1 : 0,
        discord_author_name: authorInput?.value.trim() || 'Équipe'
      };

      if (webhookUrl && !webhookUrl.startsWith('••••')) {
        payload.discord_webhook_url = webhookUrl;
      }

      const res = await api(`/api/salons/${active.id}`, 'PUT', payload);
      if (res) {
        const idx = state.salons.findIndex(s => s.id === active.id);
        if (idx !== -1) state.salons[idx] = res;
        renderSalons();
        showNotificationDialog({
          title: "Discord lié au salon !",
          message: `Les notifications pour le salon « ${res.name} » ont été enregistrées avec succès.`,
          icon: "check"
        });
      }
    };
  }

  // Exporter uniquement ce salon
  const exportBtn = document.getElementById('salon-export-btn');
  if (exportBtn) {
    exportBtn.onclick = async () => {
      const active = getActiveSalon();
      if (!active) return;

      try {
        const data = await api(`/api/salons/${active.id}/export`, 'GET');
        if (data) {
          const jsonStr = JSON.stringify(data, null, 2);
          const blob = new Blob([jsonStr], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          const cleanName = (active.name || 'salon').toLowerCase().replace(/[^a-z0-9_-]/g, '-');
          a.href = url;
          a.download = `todolist-salon-${cleanName}.tdl`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
      } catch (err) {
        showNotificationDialog({
          title: "Erreur d'export",
          message: "Impossible d'exporter le salon : " + err.message,
          icon: "alert"
        });
      }
    };
  }

  // Supprimer ce salon
  const deleteBtn = document.getElementById('salon-delete-btn');
  if (deleteBtn) {
    deleteBtn.onclick = async () => {
      const active = getActiveSalon();
      if (!active) return;

      if (state.salons.length <= 1) {
        showNotificationDialog({
          title: "Action impossible",
          message: "Vous ne pouvez pas supprimer le seul salon restant.",
          icon: "alert"
        });
        return;
      }

      const confirmed = await showConfirmDialog({
        title: "Supprimer le salon",
        message: `Supprimer définitivement le salon « ${active.name} » ainsi que TOUS ses dossiers et tâches ? Cette action est irréversible.`,
        confirmText: "Supprimer définitivement",
        cancelText: "Annuler",
        isDanger: true,
        icon: "trash"
      });

      if (!confirmed) return;

      const res = await api(`/api/salons/${active.id}`, 'DELETE');
      if (res && res.success) {
        state.salons = state.salons.filter(s => s.id !== active.id);
        // Basculer sur le premier salon
        state.currentSalonId = state.salons[0].id;
        localStorage.setItem('todolist_active_salon_id', state.currentSalonId);
        
        // Recharger les données
        const fresh = await api('/api/data', 'GET');
        if (fresh) {
          state.folders = fresh.folders || [];
          state.tasks = fresh.tasks || [];
        }

        modal.classList.add('hidden');
        renderSalons();
        renderFolders();
        selectQuickView('all');

        showNotificationDialog({
          title: "Salon supprimé",
          message: `Le salon « ${active.name} » a été supprimé.`,
          icon: "check"
        });
      }
    };
  }
}

export function openManageSalonModal(salonId) {
  const modal = document.getElementById('manage-salon-modal');
  if (!modal) return;

  const salon = state.salons.find(s => s.id === salonId) || getActiveSalon();
  if (!salon) return;

  // Remplir les champs
  const title = document.getElementById('manage-salon-modal-title');
  if (title) title.textContent = `Gérer l'espace : ${salon.name}`;

  const managePresenceText = document.getElementById('manage-salon-presence-text');
  if (managePresenceText) {
    const count = Math.max(salon.active_members_count || 1, 1);
    managePresenceText.textContent = `${count} personne${count > 1 ? 's' : ''} en ligne`;
  }

  const nameInput = document.getElementById('manage-salon-name');
  if (nameInput) nameInput.value = salon.name || '';

  const descInput = document.getElementById('manage-salon-desc');
  if (descInput) descInput.value = salon.description || '';

  // Onglet Discord
  const discordToggle = document.getElementById('manage-salon-discord-enabled');
  if (discordToggle) discordToggle.checked = Boolean(salon.discord_enabled);

  const discordUrl = document.getElementById('manage-salon-discord-url');
  if (discordUrl) discordUrl.value = salon.discord_webhook_url || '';

  const discordAuthor = document.getElementById('manage-salon-discord-author');
  if (discordAuthor) discordAuthor.value = salon.discord_author_name || '';

  const discordFeedback = document.getElementById('salon-discord-feedback');
  if (discordFeedback) discordFeedback.classList.add('hidden');

  // Stats onglet Partage
  const folderCount = state.folders.filter(f => f.salon_id === salon.id).length;
  const folderIds = new Set(state.folders.filter(f => f.salon_id === salon.id).map(f => f.id));
  const taskCount = state.tasks.filter(t => folderIds.has(t.folder_id)).length;

  const statsEl = document.getElementById('salon-export-stats');
  if (statsEl) statsEl.textContent = `Ce salon regroupe actuellement ${folderCount} dossier(s) et ${taskCount} tâche(s).`;

  // Activer premier onglet par défaut
  modal.querySelectorAll('.salon-modal-tab').forEach(t => t.classList.remove('active'));
  modal.querySelectorAll('.salon-tab-pane').forEach(p => p.classList.add('hidden'));
  modal.querySelector('.salon-modal-tab[data-pane="salon-pane-info"]')?.classList.add('active');
  document.getElementById('salon-pane-info')?.classList.remove('hidden');

  modal.classList.remove('hidden');
}

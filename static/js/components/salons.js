/**
 * Composant de gestion des Salons / Espaces de travail partagés.
 * Permet d'isoler les dossiers et tâches par projet ou groupe,
 * avec webhook Discord dédié par salon et export/partage ciblé.
 */

import { state, getActiveSalon, escapeHtml } from '../state.js';
import { renderIcon } from '../icons.js';
import { api } from '../api.js';
import { renderFolders, selectQuickView } from './folders.js';
import { renderTasks } from './tasks.js';
import { showConfirmDialog, showNotificationDialog } from './modals.js';

let selectedIconForSalon = 'folder';
let selectedColorForSalon = '#4f46e5';

export function initSalonUI() {
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

  // Bouton Gérer le salon
  const manageBtn = document.getElementById('manage-salon-btn');
  if (manageBtn) {
    manageBtn.onclick = () => {
      const active = getActiveSalon();
      if (active) openManageSalonModal(active.id);
    };
  }

  // Bouton Nouveau salon
  const createBtn = document.getElementById('btn-create-salon');
  if (createBtn) {
    createBtn.onclick = () => {
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
          const freshData = await api('/api/data', 'GET');
          if (freshData) {
            state.salons = freshData.salons || [];
            state.folders = freshData.folders || [];
            state.tasks = freshData.tasks || [];
          }
          state.currentSalonId = res.id;
          localStorage.setItem('todolist_active_salon_id', res.id);
          renderSalons();
          renderFolders();
          selectQuickView('all');
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

  // Fermeture des modales salon
  document.querySelectorAll('#add-salon-modal .close-modal-btn, #manage-salon-modal .close-modal-btn').forEach(btn => {
    btn.onclick = () => {
      document.getElementById('add-salon-modal')?.classList.add('hidden');
      document.getElementById('manage-salon-modal')?.classList.add('hidden');
    };
  });

  setupAddSalonForm();
  setupManageSalonModal();
  renderSalons();
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

  if (current) {
    if (nameEl) nameEl.textContent = current.name;
    if (colorEl) colorEl.style.backgroundColor = current.color || '#4f46e5';
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

    const item = document.createElement('div');
    item.className = `salon-menu-item ${isCurrent ? 'active' : ''}`;
    
    const discordBadge = (s.discord_enabled && s.discord_webhook_configured)
      ? `<span class="salon-mini-discord-badge" title="Discord lié">${renderIcon('message-square')}</span>`
      : '';

    item.innerHTML = `
      <div class="salon-item-left">
        <span class="salon-item-color-dot" style="background-color: ${s.color || '#4f46e5'};"></span>
        <span class="salon-item-icon">${renderIcon(s.icon || 'folder')}</span>
        <span class="salon-item-name">${escapeHtml(s.name)}</span>
        ${discordBadge}
      </div>
      <div class="salon-item-right">
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
      btn.onclick = () => {
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
      btn.onclick = () => {
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

    const name = nameInput?.value.trim();
    if (!name) return;

    let webhookUrl = (webhookInput?.value || '').trim();
    if (webhookUrl && !webhookUrl.startsWith('http://') && !webhookUrl.startsWith('https://')) {
      webhookUrl = 'https://' + webhookUrl;
    }

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
      renderSalons();
      renderFolders();
      selectQuickView('all');
    }
  };
}

export function openAddSalonModal() {
  const modal = document.getElementById('add-salon-modal');
  if (!modal) return;
  const form = document.getElementById('add-salon-form');
  if (form) form.reset();
  modal.classList.remove('hidden');
  document.getElementById('add-salon-name-input')?.focus();
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

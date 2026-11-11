/**
 * Composant de gestion et rendu des dossiers et vues rapides.
 */

import { state, getCurrentViewTasks, getActiveSalon, getActiveSalonFolderIds, escapeHtml } from '../state.js';
import { applyActiveBackground } from '../theme.js';
import { renderTasks } from './tasks.js';
import { api } from '../api.js';
import { openEditFolderModal, openAddFolderModal, showConfirmDialog } from './modals.js';
import { renderIcon } from '../icons.js';
import { updateFolderDropdown } from './dropdowns.js';

let draggedFolderId = null;

export function renderFolders() {
  renderFolderSelect();
  renderFolderList();
  renderCounters();
  updateProgress();
  updateHeaderWeeklyState();
}

export function renderFolderSelect() {
  updateFolderDropdown();
}

export function renderFolderList() {
  const list = document.getElementById('folder-list');
  if (!list) return;

  list.innerHTML = '';

  const activeSalon = getActiveSalon();
  const activeId = activeSalon ? Number(activeSalon.id) : 1;
  const visibleFolders = activeSalon 
    ? state.folders.filter(f => Number(f.salon_id) === activeId || (!f.salon_id && activeId === 1))
    : state.folders;

  if (visibleFolders.length === 0) {
    list.innerHTML = `
      <div class="empty-folders-hint" style="padding: 16px 12px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
        <p>Aucun dossier dans ce salon.</p>
        <button type="button" class="btn btn-sm btn-secondary" id="btn-create-first-folder" style="margin-top: 8px; font-size: 0.8rem; padding: 4px 10px;">
          + Créer un dossier
        </button>
      </div>
    `;
    const btn = document.getElementById('btn-create-first-folder');
    if (btn) btn.onclick = () => openAddFolderModal();
    return;
  }

  visibleFolders.forEach(folder => {
    const folderTasks = state.tasks.filter(t => t.folder_id === folder.id);
    const pendingCount = folderTasks.filter(t => !t.completed).length;

    const item = document.createElement('div');
    item.className = `folder-item ${state.currentView === folder.id ? 'active' : ''}`;
    item.setAttribute('draggable', 'true');
    item.dataset.folderId = String(folder.id);

    item.onclick = (e) => {
      if (e.target.closest('.folder-actions') || item.classList.contains('dragging')) return;
      selectFolderView(folder.id);
    };

    const weeklyBadge = folder.auto_reset_weekly 
      ? `<span class="folder-mini-badge" title="Se réinitialise chaque semaine">${renderIcon('repeat')}</span>` 
      : '';

    const bgBadge = (folder.bg_type && folder.bg_type !== 'default')
      ? `<span class="folder-mini-badge" title="Fond personnalisé">${renderIcon('palette')}</span>`
      : '';

    const safeColor = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(folder.color) ? folder.color : '#6366f1';

    item.innerHTML = `
      <div class="folder-info">
        <span class="folder-drag-handle" title="Glisser pour réorganiser">${renderIcon('grip-vertical')}</span>
        <span class="folder-pill"></span>
        <span class="folder-icon">${renderIcon(folder.icon)}</span>
        <span class="folder-name">${escapeHtml(folder.name)}</span>
        ${weeklyBadge}
        ${bgBadge}
      </div>
      <div class="folder-actions">
        <span class="nav-count">${pendingCount}</span>
        <button class="icon-btn edit-folder-btn" title="Modifier le dossier" draggable="false">${renderIcon('edit')}</button>
        <button class="icon-btn delete-folder-btn" title="Supprimer le dossier" draggable="false">${renderIcon('trash')}</button>
      </div>
    `;

    const pill = item.querySelector('.folder-pill');
    if (pill) pill.style.backgroundColor = safeColor;

    // --- Gestion du Glisser-Déposer (Drag & Drop) ---
    item.addEventListener('dragstart', (e) => {
      draggedFolderId = folder.id;
      e.dataTransfer.setData('text/plain', String(folder.id));
      e.dataTransfer.effectAllowed = 'move';
      setTimeout(() => item.classList.add('dragging'), 0);
    });

    item.addEventListener('dragend', () => {
      item.classList.remove('dragging');
      list.querySelectorAll('.folder-item').forEach(el => {
        el.classList.remove('drag-over-top', 'drag-over-bottom', 'dragging');
      });
      draggedFolderId = null;
    });

    item.addEventListener('dragover', (e) => {
      e.preventDefault();
      if (!draggedFolderId || draggedFolderId === folder.id) return;
      e.dataTransfer.dropEffect = 'move';

      const rect = item.getBoundingClientRect();
      const isTop = (e.clientY - rect.top) < (rect.height / 2);
      item.classList.toggle('drag-over-top', isTop);
      item.classList.toggle('drag-over-bottom', !isTop);
    });

    item.addEventListener('dragleave', (e) => {
      if (!item.contains(e.relatedTarget)) {
        item.classList.remove('drag-over-top', 'drag-over-bottom');
      }
    });

    item.addEventListener('drop', async (e) => {
      e.preventDefault();
      item.classList.remove('drag-over-top', 'drag-over-bottom');

      const sourceId = Number(e.dataTransfer.getData('text/plain') || draggedFolderId);
      const targetId = Number(folder.id);
      if (!sourceId || sourceId === targetId) return;

      const fromIndex = state.folders.findIndex(f => f.id === sourceId);
      const toIndex = state.folders.findIndex(f => f.id === targetId);
      if (fromIndex === -1 || toIndex === -1) return;

      const rect = item.getBoundingClientRect();
      const isTop = (e.clientY - rect.top) < (rect.height / 2);
      let insertIndex = isTop ? toIndex : toIndex + 1;
      if (fromIndex < insertIndex) insertIndex--;

      const [movedFolder] = state.folders.splice(fromIndex, 1);
      state.folders.splice(insertIndex, 0, movedFolder);

      renderFolderList();
      await api('/api/folders/reorder', 'POST', {
        folder_ids: state.folders.map(f => f.id)
      });
    });

    // Event listeners
    item.querySelector('.edit-folder-btn').onclick = (e) => {
      e.stopPropagation();
      openEditFolderModal(folder.id);
    };

    item.querySelector('.delete-folder-btn').onclick = (e) => {
      e.stopPropagation();
      deleteFolder(folder.id);
    };

    list.appendChild(item);
  });
}

export function renderCounters() {
  const countAll = document.getElementById('count-all');
  const countPending = document.getElementById('count-pending');
  const countCompleted = document.getElementById('count-completed');
  const tabCountAll = document.getElementById('tab-count-all');
  const tabCountPending = document.getElementById('tab-count-pending');
  const tabCountCompleted = document.getElementById('tab-count-completed');

  const activeFolderIds = new Set(getActiveSalonFolderIds());
  const salonTasks = state.tasks.filter(t => !t.folder_id || activeFolderIds.has(t.folder_id));

  const total = salonTasks.length;
  const pending = salonTasks.filter(t => !t.completed).length;
  const completed = salonTasks.filter(t => t.completed).length;

  if (countAll) countAll.textContent = total;
  if (countPending) countPending.textContent = pending;
  if (countCompleted) countCompleted.textContent = completed;

  const viewTasks = getCurrentViewTasks();
  if (tabCountAll) tabCountAll.textContent = viewTasks.length;
  if (tabCountPending) tabCountPending.textContent = viewTasks.filter(t => !t.completed).length;
  if (tabCountCompleted) tabCountCompleted.textContent = viewTasks.filter(t => t.completed).length;
}

export function updateProgress() {
  const fill = document.getElementById('progress-fill');
  const text = document.getElementById('progress-text');
  const details = document.getElementById('progress-details');

  const viewTasks = getCurrentViewTasks();
  const total = viewTasks.length;
  const completed = viewTasks.filter(t => t.completed).length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  if (fill) fill.style.width = `${percent}%`;
  if (text) text.textContent = `Progression : ${percent}%`;
  if (details) details.textContent = `${completed} sur ${total} tâches faites`;
}

export function updateHeaderWeeklyState() {
  const badge = document.getElementById('folder-weekly-badge');
  const resetBtn = document.getElementById('folder-reset-btn');

  if (typeof state.currentView === 'number') {
    const currentFolder = state.folders.find(f => f.id === state.currentView);
    if (currentFolder && currentFolder.auto_reset_weekly) {
      if (badge) badge.classList.remove('hidden');
      if (resetBtn) resetBtn.classList.remove('hidden');
      return;
    }
  }
  if (badge) badge.classList.add('hidden');
  if (resetBtn) resetBtn.classList.add('hidden');
}

export function selectQuickView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.quick-views .nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === viewName);
  });
  renderFolderList();

  const title = document.getElementById('current-title');
  const subtitle = document.getElementById('current-subtitle');

  if (viewName === 'all') {
    if (title) title.textContent = "Toutes les tâches";
    if (subtitle) subtitle.textContent = "Vue d'ensemble de toutes vos activités";
  } else if (viewName === 'pending') {
    if (title) title.textContent = "Tâches à faire";
    if (subtitle) subtitle.textContent = "Concentrez-vous sur vos priorités actuelles";
  } else if (viewName === 'completed') {
    if (title) title.textContent = "Tâches terminées";
    if (subtitle) subtitle.textContent = "Historique de vos accomplissements";
  }

  applyActiveBackground();
  renderCounters();
  renderTasks();
  updateProgress();
  updateHeaderWeeklyState();
}

export function selectFolderView(folderId) {
  state.currentView = folderId;
  document.querySelectorAll('.quick-views .nav-item').forEach(btn => btn.classList.remove('active'));
  renderFolderList();

  const folder = state.folders.find(f => f.id === folderId);
  const title = document.getElementById('current-title');
  const subtitle = document.getElementById('current-subtitle');
  const folderSelect = document.getElementById('task-folder-select');

  if (folder) {
    if (title) {
      title.innerHTML = `${renderIcon(folder.icon)} <span>${escapeHtml(folder.name)}</span>`;
    }
    if (subtitle) {
      subtitle.textContent = folder.auto_reset_weekly 
        ? `Dossier hebdomadaire (se remet à l'état initial après 7 jours)` 
        : `Dossier de tâches`;
    }
    if (folderSelect) folderSelect.value = folder.id;
  }

  applyActiveBackground();
  renderCounters();
  renderTasks();
  updateProgress();
  updateHeaderWeeklyState();
}

export async function deleteFolder(folderId) {
  const folder = state.folders.find(f => f.id === folderId);
  if (!folder) return;

  const count = state.tasks.filter(t => t.folder_id === folderId).length;
  const msg = count > 0 
    ? `Ce dossier contient ${count} tâche(s). Supprimer définitivement le dossier et TOUTES ses tâches associées ?` 
    : `Voulez-vous vraiment supprimer définitivement le dossier "${folder.name}" ?`;

  const confirmed = await showConfirmDialog({
    title: "Supprimer le dossier",
    message: msg,
    confirmText: "Supprimer",
    cancelText: "Annuler",
    isDanger: true,
    icon: "trash"
  });

  if (!confirmed) return;

  state.folders = state.folders.filter(f => f.id !== folderId);
  state.tasks = state.tasks.filter(t => t.folder_id !== folderId);

  if (state.currentView === folderId) {
    selectQuickView('all');
  } else {
    renderFolders();
    renderTasks();
  }

  await api(`/api/folders/${folderId}`, 'DELETE');
}

export async function resetCurrentFolderWeek() {
  const currentViewNum = Number(state.currentView);
  if (isNaN(currentViewNum) || currentViewNum <= 0) return;
  const folder = state.folders.find(f => Number(f.id) === currentViewNum);
  if (!folder) return;

  const confirmed = await showConfirmDialog({
    title: "Réinitialiser la semaine",
    message: `Remettre toutes les tâches du dossier "${folder.name}" à l'état initial (non faites, 0%) pour la nouvelle semaine ?`,
    confirmText: "Réinitialiser",
    cancelText: "Annuler",
    isDanger: false,
    icon: "repeat"
  });

  if (!confirmed) return;

  const res = await api(`/api/folders/${folder.id}/reset`, 'POST');
  if (res && res.success) {
    state.tasks.forEach(t => {
      if (t.folder_id === folder.id) {
        t.completed = 0;
        t.progress = 0;
      }
    });
    renderFolders();
    renderTasks();
  }
}

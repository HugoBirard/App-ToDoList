/**
 * Composant de gestion et rendu des dossiers et vues rapides.
 */

import { state, getCurrentViewTasks, escapeHtml } from '../state.js';
import { applyActiveBackground } from '../theme.js';
import { renderTasks } from './tasks.js';
import { api } from '../api.js';
import { openEditFolderModal, showConfirmDialog } from './modals.js';
import { renderIcon } from '../icons.js';
import { updateFolderDropdown } from './dropdowns.js';

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

  state.folders.forEach(folder => {
    const folderTasks = state.tasks.filter(t => t.folder_id === folder.id);
    const pendingCount = folderTasks.filter(t => !t.completed).length;

    const item = document.createElement('div');
    item.className = `folder-item ${state.currentView === folder.id ? 'active' : ''}`;
    item.onclick = (e) => {
      if (e.target.closest('.folder-actions')) return;
      selectFolderView(folder.id);
    };

    const weeklyBadge = folder.auto_reset_weekly 
      ? `<span class="folder-mini-badge" title="Se réinitialise chaque semaine">${renderIcon('repeat')}</span>` 
      : '';

    const bgBadge = (folder.bg_type && folder.bg_type !== 'default')
      ? `<span class="folder-mini-badge" title="Fond personnalisé">${renderIcon('palette')}</span>`
      : '';

    const safeColor = /^#[0-9a-fA-F]{3,8}$/.test(folder.color) ? folder.color : '#6366f1';

    item.innerHTML = `
      <div class="folder-info">
        <span class="folder-pill"></span>
        <span class="folder-icon">${renderIcon(folder.icon)}</span>
        <span class="folder-name">${escapeHtml(folder.name)}</span>
        ${weeklyBadge}
        ${bgBadge}
      </div>
      <div class="folder-actions">
        <span class="nav-count">${pendingCount}</span>
        <button class="icon-btn edit-folder-btn" title="Modifier le dossier">${renderIcon('edit')}</button>
        <button class="icon-btn delete-folder-btn" title="Supprimer le dossier">${renderIcon('trash')}</button>
      </div>
    `;

    const pill = item.querySelector('.folder-pill');
    if (pill) pill.style.backgroundColor = safeColor;

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

  const total = state.tasks.length;
  const pending = state.tasks.filter(t => !t.completed).length;
  const completed = state.tasks.filter(t => t.completed).length;

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

/**
 * Composant de gestion et rendu des tâches.
 */

import { state, getCurrentViewTasks, escapeHtml } from '../state.js';
import { api } from '../api.js';
import { renderCounters, updateProgress } from './folders.js';
import { renderIcon } from '../icons.js';
import { showConfirmDialog, showNotificationDialog } from './modals.js';

export function renderTasks() {
  const list = document.getElementById('task-list');
  const emptyState = document.getElementById('empty-state');
  const emptyTitle = document.getElementById('empty-title');
  const emptyDesc = document.getElementById('empty-desc');

  if (!list) return;

  let tasks = getCurrentViewTasks();

  if (state.currentFilter === 'pending') {
    tasks = tasks.filter(t => !t.completed);
  } else if (state.currentFilter === 'completed') {
    tasks = tasks.filter(t => t.completed);
  }

  if (state.searchQuery.trim()) {
    const q = state.searchQuery.toLowerCase();
    tasks = tasks.filter(t => t.title.toLowerCase().includes(q));
  }

  list.innerHTML = '';

  if (tasks.length === 0) {
    if (emptyState) emptyState.classList.remove('hidden');
    if (state.searchQuery.trim()) {
      if (emptyTitle) emptyTitle.textContent = "Aucun résultat";
      if (emptyDesc) emptyDesc.textContent = `Aucune tâche ne correspond à "${state.searchQuery}".`;
    } else if (state.currentFilter === 'completed') {
      if (emptyTitle) emptyTitle.textContent = "Aucune tâche terminée";
      if (emptyDesc) emptyDesc.textContent = "Vos tâches accomplies apparaîtront ici.";
    } else {
      if (emptyTitle) emptyTitle.textContent = "Tout est propre !";
      if (emptyDesc) emptyDesc.textContent = "Vous n'avez aucune tâche en cours dans cette liste.";
    }
    return;
  }

  if (emptyState) emptyState.classList.add('hidden');

  tasks.forEach(task => {
    const folder = state.folders.find(f => f.id === task.folder_id);
    const item = document.createElement('li');
    item.className = `task-item ${task.completed ? 'completed' : ''}`;
    item.id = `task-${task.id}`;

    // Date
    let dueDateHtml = '';
    if (task.due_date) {
      const date = new Date(task.due_date);
      dueDateHtml = `<span class="task-meta-item">${renderIcon('calendar')} ${date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}</span>`;
    }

    // Badge Dossier
    let folderBadgeHtml = '';
    const safeFolderColor = folder && /^#[0-9a-fA-F]{3,8}$/.test(folder.color) ? folder.color : '#6366f1';
    if (folder && typeof state.currentView !== 'number') {
      folderBadgeHtml = `
        <span class="folder-badge">
          ${renderIcon(folder.icon)} ${escapeHtml(folder.name)}
        </span>
      `;
    }

    // Badge Priorité
    let priorityBadge = '';
    if (task.priority === 'high') {
      priorityBadge = `<span class="priority-badge priority-high">${renderIcon('zap')} Urgente</span>`;
    } else if (task.priority === 'low') {
      priorityBadge = `<span class="priority-badge priority-low">Basse</span>`;
    }

    // Barre de progression
    let progressWidgetHtml = '';
    if (task.has_progress) {
      const currentProg = task.completed ? 100 : (task.progress || 0);
      progressWidgetHtml = `
        <div class="task-progress-box">
          <input 
            type="range" 
            class="task-progress-slider" 
            min="0" 
            max="100" 
            step="5"
            value="${currentProg}"
            id="prog-slider-${task.id}"
            title="Ajustez la progression (100% = fait)"
          >
          <span class="task-progress-val" id="prog-val-${task.id}">${currentProg}%</span>
          <div class="task-progress-btns">
            <button type="button" class="progress-quick-btn btn-step" title="+25%">+25%</button>
            <button type="button" class="progress-quick-btn btn-100" title="Marquer à 100% (Fait)">100%</button>
          </div>
        </div>
      `;
    }

    const toggleTypeIcon = task.has_progress ? renderIcon('check-square') : renderIcon('bar-chart');
    const toggleTypeTitle = task.has_progress 
      ? 'Passer en case à cocher simple' 
      : 'Ajouter une barre de progression';

    item.innerHTML = `
      <div class="checkbox-container">
        <input 
          type="checkbox" 
          class="task-checkbox" 
          id="chk-${task.id}"
          ${task.completed ? 'checked' : ''} 
          title="Marquer comme ${task.completed ? 'à faire' : 'terminée'}"
        >
      </div>

      <div class="task-content">
        <span class="task-title" id="title-${task.id}">${escapeHtml(task.title)}</span>
        ${progressWidgetHtml}
        <div class="task-meta">
          ${folderBadgeHtml}
          ${priorityBadge}
          ${dueDateHtml}
        </div>
      </div>

      <div class="task-actions">
        <button class="icon-btn btn-toggle-type" title="${toggleTypeTitle}">${toggleTypeIcon}</button>
        <button class="icon-btn btn-edit-title" title="Modifier le titre">${renderIcon('edit')}</button>
        <button class="icon-btn btn-delete-task" title="Supprimer la tâche">${renderIcon('trash')}</button>
      </div>
    `;

    const fBadge = item.querySelector('.folder-badge');
    if (fBadge) fBadge.style.borderLeft = `3px solid ${safeFolderColor}`;

    // Attacher événements de manière propre
    const chk = item.querySelector('.task-checkbox');
    chk.onchange = () => toggleTaskStatus(task.id, chk.checked);

    const titleEl = item.querySelector('.task-title');
    titleEl.ondblclick = () => editTaskTitle(task.id);
    item.querySelector('.btn-edit-title').onclick = () => editTaskTitle(task.id);
    item.querySelector('.btn-delete-task').onclick = () => deleteTask(task.id);
    item.querySelector('.btn-toggle-type').onclick = () => toggleTaskProgressType(task.id);

    if (task.has_progress) {
      const slider = item.querySelector('.task-progress-slider');
      slider.oninput = () => handleSliderLiveInput(task.id, slider.value);
      slider.onchange = () => handleTaskProgressChange(task.id, slider.value);

      item.querySelector('.btn-step').onclick = () => addProgressStep(task.id, 25);
      item.querySelector('.btn-100').onclick = () => handleTaskProgressChange(task.id, 100);
    }

    list.appendChild(item);
  });
}

export async function toggleTaskStatus(taskId, isCompleted) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;

  task.completed = isCompleted ? 1 : 0;
  if (task.has_progress) {
    task.progress = isCompleted ? 100 : 0;
    const slider = document.getElementById(`prog-slider-${taskId}`);
    const valText = document.getElementById(`prog-val-${taskId}`);
    if (slider) slider.value = task.progress;
    if (valText) valText.textContent = `${task.progress}%`;
  }

  const taskEl = document.getElementById(`task-${taskId}`);
  if (taskEl) {
    taskEl.classList.toggle('completed', isCompleted);
  }
  renderCounters();
  updateProgress();

  await api(`/api/tasks/${taskId}`, 'PUT', { completed: isCompleted });
  renderTasks();
}

export function handleSliderLiveInput(taskId, value) {
  const num = parseInt(value, 10);
  const valText = document.getElementById(`prog-val-${taskId}`);
  if (valText) valText.textContent = `${num}%`;

  const taskEl = document.getElementById(`task-${taskId}`);
  const chk = document.getElementById(`chk-${taskId}`);
  const isDone = num >= 100;

  if (taskEl) taskEl.classList.toggle('completed', isDone);
  if (chk) chk.checked = isDone;
}

export async function handleTaskProgressChange(taskId, value) {
  const num = parseInt(value, 10);
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;

  const isCompleted = num >= 100;
  task.progress = num;
  task.completed = isCompleted ? 1 : 0;

  renderCounters();
  updateProgress();

  await api(`/api/tasks/${taskId}`, 'PUT', { progress: num });
  renderTasks();
}

export function addProgressStep(taskId, step = 25) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;
  const current = task.completed ? 100 : (task.progress || 0);
  const next = Math.min(100, current + step);
  handleTaskProgressChange(taskId, next);
}

export async function toggleTaskProgressType(taskId) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;

  const newHasProgress = task.has_progress ? 0 : 1;
  task.has_progress = newHasProgress;
  if (newHasProgress && task.progress === undefined) {
    task.progress = task.completed ? 100 : 0;
  }

  renderTasks();
  await api(`/api/tasks/${taskId}`, 'PUT', { has_progress: newHasProgress });
}

export async function handleAddTask(e) {
  e.preventDefault();
  const input = document.getElementById('new-task-input');
  const folderSelect = document.getElementById('task-folder-select');
  const prioritySelect = document.getElementById('task-priority-select');
  const dueDateInput = document.getElementById('task-due-date');
  const typeSelect = document.getElementById('task-type-select');

  const title = input.value.trim();
  if (!title) return;

  let folderId = parseInt(folderSelect ? folderSelect.value : '', 10);
  const exists = state.folders.some(f => f.id === folderId);
  if (!exists && state.folders.length > 0) {
    const currentNum = Number(state.currentView);
    if (!isNaN(currentNum) && state.folders.some(f => f.id === currentNum)) {
      folderId = currentNum;
    } else {
      folderId = state.folders[0].id;
    }
    if (folderSelect) folderSelect.value = folderId;
  }

  const priority = prioritySelect.value;
  const dueDate = dueDateInput.value || null;
  const hasProgress = typeSelect.value === 'progress' ? 1 : 0;

  const newTask = await api('/api/tasks', 'POST', {
    title,
    folder_id: folderId,
    priority,
    due_date: dueDate,
    has_progress: hasProgress,
    progress: 0
  });

  if (newTask) {
    state.tasks.unshift(newTask);
    input.value = '';
    dueDateInput.value = '';
    renderCounters();
    updateProgress();
    renderTasks();
    input.focus();
  }
}

export async function editTaskTitle(taskId) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;

  const titleEl = document.getElementById(`title-${taskId}`);
  if (!titleEl) return;

  const currentText = task.title;
  const input = document.createElement('input');
  input.type = 'text';
  input.value = currentText;
  input.className = 'edit-task-input';
  input.style.cssText = 'width: 100%; padding: 4px 8px; border-radius: 4px; border: 1px solid var(--accent); background: var(--bg-primary); color: var(--text-primary); font-size: 1rem;';

  const finishEdit = async () => {
    const newTitle = input.value.trim();
    if (newTitle && newTitle !== currentText) {
      task.title = newTitle;
      titleEl.textContent = newTitle;
      await api(`/api/tasks/${taskId}`, 'PUT', { title: newTitle });
    } else {
      titleEl.textContent = currentText;
    }
  };

  input.onblur = finishEdit;
  input.onkeydown = (e) => {
    if (e.key === 'Enter') input.blur();
    else if (e.key === 'Escape') titleEl.textContent = currentText;
  };

  titleEl.innerHTML = '';
  titleEl.appendChild(input);
  input.focus();
  input.select();
}

export async function deleteTask(taskId) {
  const confirmed = await showConfirmDialog({
    title: "Supprimer la tâche",
    message: "Voulez-vous vraiment supprimer définitivement cette tâche ?",
    confirmText: "Supprimer",
    cancelText: "Annuler",
    isDanger: true,
    icon: "trash"
  });
  if (!confirmed) return;

  state.tasks = state.tasks.filter(t => t.id !== taskId);
  renderCounters();
  updateProgress();
  renderTasks();
  await api(`/api/tasks/${taskId}`, 'DELETE');
}

export async function clearCompleted() {
  const completedCount = state.tasks.filter(t => t.completed).length;
  if (completedCount === 0) {
    await showNotificationDialog({
      title: "Nettoyage des tâches",
      message: "Aucune tâche terminée à nettoyer !",
      icon: "info"
    });
    return;
  }

  const currentViewNum = Number(state.currentView);
  const inFolder = !isNaN(currentViewNum) && currentViewNum > 0;
  const msg = inFolder 
    ? "Supprimer définitivement toutes les tâches terminées de ce dossier ?"
    : "Supprimer définitivement TOUTES les tâches terminées de tous les dossiers ?";

  const confirmed = await showConfirmDialog({
    title: "Nettoyer les tâches terminées",
    message: msg,
    confirmText: "Nettoyer",
    cancelText: "Annuler",
    isDanger: true,
    icon: "trash"
  });

  if (!confirmed) return;

  const folderId = inFolder ? currentViewNum : null;
  if (inFolder) {
    state.tasks = state.tasks.filter(t => !(t.completed && t.folder_id === folderId));
  } else {
    state.tasks = state.tasks.filter(t => !t.completed);
  }

  renderCounters();
  updateProgress();
  renderTasks();
  await api('/api/tasks/clear-completed', 'POST', { folder_id: folderId });
}

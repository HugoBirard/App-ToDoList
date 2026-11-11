/**
 * Composant de menus déroulants personnalisés (Custom Dropdowns).
 * Remplace totalement les <select> natifs du système pour garantir :
 * - Zéro texte blanc sur blanc sur Linux/Fedora/WebKit.
 * - Rendu 100% personnalisé, moderne et contrasté.
 * - Effet semi-transparent glassmorphism avec flou d'arrière-plan.
 */

import { state, escapeHtml } from '../state.js';
import { renderIcon } from '../icons.js';

export function initCustomDropdowns() {
  // Fermer les dropdowns ouverts lors d'un clic extérieur
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.custom-dropdown')) {
      closeAllDropdowns();
    }
  });

  // Fermer avec la touche Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAllDropdowns();
    }
  });

  setupDropdownToggle('task-folder-dropdown');
  setupDropdownToggle('task-type-dropdown');
  setupDropdownToggle('task-priority-dropdown');

  setupStaticOptionClicks('task-type-dropdown', 'task-type-select');
  setupStaticOptionClicks('task-priority-dropdown', 'task-priority-select');
}

export function closeAllDropdowns() {
  document.querySelectorAll('.custom-dropdown').forEach(dd => {
    dd.classList.remove('open');
  });
}

function setupDropdownToggle(dropdownId) {
  const dd = document.getElementById(dropdownId);
  if (!dd) return;
  const trigger = dd.querySelector('.dropdown-trigger');
  if (!trigger) return;

  trigger.onclick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const isOpen = dd.classList.contains('open');
    closeAllDropdowns();
    if (!isOpen) {
      dd.classList.add('open');
    }
  };
}

function setupStaticOptionClicks(dropdownId, hiddenInputId) {
  const dd = document.getElementById(dropdownId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!dd || !hiddenInput) return;

  dd.querySelectorAll('.dropdown-option').forEach(opt => {
    opt.onclick = (e) => {
      e.stopPropagation();
      const val = opt.dataset.value;
      hiddenInput.value = val;

      // Mettre à jour l'état visuel actif
      dd.querySelectorAll('.dropdown-option').forEach(o => o.classList.toggle('selected', o.dataset.value === val));

      // Mettre à jour le texte du trigger
      const label = dd.querySelector('.dropdown-label');
      const optText = opt.querySelector('.opt-text');
      if (label && optText) {
        label.textContent = optText.textContent;
      }
      const optIcon = opt.querySelector('.opt-icon');
      const triggerIcon = dd.querySelector('.dropdown-icon');
      if (triggerIcon && optIcon) {
        triggerIcon.innerHTML = optIcon.innerHTML;
      }

      dd.classList.remove('open');
      hiddenInput.dispatchEvent(new Event('change'));
    };
  });
}

/**
 * Met à jour dynamiquement les options du menu déroulant des dossiers.
 */
export function updateFolderDropdown() {
  const dd = document.getElementById('task-folder-dropdown');
  const hiddenInput = document.getElementById('task-folder-select');
  if (!dd || !hiddenInput) return;

  const menu = dd.querySelector('.dropdown-menu');
  if (!menu) return;

  menu.innerHTML = '';

  const visibleFolders = state.folders;

  let selectedId = parseInt(hiddenInput.value, 10);
  if (typeof state.currentView === 'number') {
    selectedId = state.currentView;
  } else if (isNaN(selectedId) || !visibleFolders.some(f => Number(f.id) === selectedId)) {
    selectedId = visibleFolders.length > 0 ? visibleFolders[0].id : null;
  }

  if (selectedId !== null) {
    hiddenInput.value = selectedId;
  } else {
    hiddenInput.value = '';
  }

  let selectedFolder = null;

  visibleFolders.forEach(folder => {
    const isSelected = folder.id === selectedId;
    if (isSelected) selectedFolder = folder;

    const item = document.createElement('div');
    item.className = `dropdown-option ${isSelected ? 'selected' : ''}`;
    item.dataset.value = folder.id;

    const weeklyBadge = folder.auto_reset_weekly 
      ? `<span class="opt-badge" title="Hebdo">${renderIcon('repeat')}</span>` 
      : '';

    item.innerHTML = `
      <span class="opt-icon">${renderIcon(folder.icon)}</span>
      <span class="opt-text">${escapeHtml(folder.name)}</span>
      ${weeklyBadge}
      <span class="opt-check">${renderIcon('check')}</span>
    `;

    item.onclick = (e) => {
      e.stopPropagation();
      hiddenInput.value = folder.id;
      updateFolderDropdown();
      dd.classList.remove('open');
      hiddenInput.dispatchEvent(new Event('change'));
    };

    menu.appendChild(item);
  });

  // Mettre à jour le libellé du trigger
  const label = dd.querySelector('.dropdown-label');
  const triggerIcon = dd.querySelector('.dropdown-icon');

  if (selectedFolder) {
    if (label) label.textContent = selectedFolder.name;
    if (triggerIcon) triggerIcon.innerHTML = renderIcon(selectedFolder.icon);
  } else if (visibleFolders.length > 0) {
    if (label) label.textContent = visibleFolders[0].name;
    if (triggerIcon) triggerIcon.innerHTML = renderIcon(visibleFolders[0].icon);
  } else {
    if (label) label.textContent = "Aucun dossier";
    if (triggerIcon) triggerIcon.innerHTML = renderIcon('folder');
  }
}

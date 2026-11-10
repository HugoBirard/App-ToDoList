/**
 * Point d'entrée de l'application Frontend.
 * Initialise les modules, charge les données et configure les écouteurs d'événements.
 */

import { state } from './state.js';
import { fetchInitialData } from './api.js';
import { initTheme, toggleTheme, applyActiveBackground } from './theme.js';
import { initCustomDropdowns } from './components/dropdowns.js';
import { 
  renderFolders, 
  selectQuickView, 
  resetCurrentFolderWeek 
} from './components/folders.js';
import { 
  renderTasks, 
  handleAddTask, 
  clearCompleted 
} from './components/tasks.js';
import { 
  openAddFolderModal, 
  closeFolderModal, 
  handleFolderSubmit, 
  openThemeModal, 
  closeThemeModal, 
  saveMainTheme, 
  resetDefaultTheme,
  applyPresetTheme,
  updateMainBgControlsUI,
  updateMainBgPreview,
  updateFolderBgControlsUI,
  updateFolderBgPreview,
  selectIcon,
  selectColor
} from './components/modals.js';

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  await loadData();
  setupEventListeners();
});

async function loadData() {
  const data = await fetchInitialData();
  if (data) {
    state.folders = data.folders || [];
    state.tasks = data.tasks || [];
    state.settings = data.settings || {};

    if (state.settings.main_background) {
      state.mainBg = state.settings.main_background;
    } else {
      const saved = localStorage.getItem('todolist_main_bg');
      if (saved) state.mainBg = saved;
    }

    applyActiveBackground();
    renderFolders();
    renderTasks();
  }
}

function setupEventListeners() {
  // Initialisation des listes déroulantes personnalisées
  initCustomDropdowns();

  // Navigation Rapide
  document.querySelectorAll('.quick-views .nav-item').forEach(btn => {
    btn.addEventListener('click', () => selectQuickView(btn.dataset.view));
  });

  // Filtres (Toutes, À faire, Terminées)
  document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.currentFilter = tab.dataset.filter;
      renderTasks();
    });
  });

  // Recherche dynamique
  const searchInput = document.getElementById('search-input');
  const clearSearchBtn = document.getElementById('clear-search-btn');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      if (clearSearchBtn) clearSearchBtn.classList.toggle('hidden', !state.searchQuery);
      renderTasks();
    });
  }

  if (clearSearchBtn) {
    clearSearchBtn.addEventListener('click', () => {
      if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
      }
      state.searchQuery = '';
      clearSearchBtn.classList.add('hidden');
      renderTasks();
    });
  }

  // Formulaire d'ajout de tâche
  const addTaskForm = document.getElementById('add-task-form');
  if (addTaskForm) {
    addTaskForm.addEventListener('submit', handleAddTask);
  }

  // Nettoyage des tâches terminées
  const clearCompletedBtn = document.getElementById('clear-completed-btn');
  if (clearCompletedBtn) {
    clearCompletedBtn.addEventListener('click', clearCompleted);
  }

  // Réinitialisation de la semaine (dossier hebdo)
  const folderResetBtn = document.getElementById('folder-reset-btn');
  if (folderResetBtn) {
    folderResetBtn.addEventListener('click', resetCurrentFolderWeek);
  }

  // Modal Personnalisation Fond & Paramètres
  const openThemeModalBtn = document.getElementById('open-theme-modal-btn');
  if (openThemeModalBtn) {
    openThemeModalBtn.addEventListener('click', openThemeModal);
  }

  const sidebarSettingsBtn = document.getElementById('sidebar-settings-btn');
  if (sidebarSettingsBtn) {
    sidebarSettingsBtn.addEventListener('click', openThemeModal);
  }

  const saveMainThemeBtn = document.getElementById('save-main-theme-btn');
  if (saveMainThemeBtn) {
    saveMainThemeBtn.addEventListener('click', saveMainTheme);
  }

  const resetDefaultThemeBtn = document.getElementById('reset-default-theme-btn');
  if (resetDefaultThemeBtn) {
    resetDefaultThemeBtn.addEventListener('click', resetDefaultTheme);
  }

  document.querySelectorAll('input[name="main-bg-type"]').forEach(r => {
    r.addEventListener('change', updateMainBgControlsUI);
  });

  ['main-bg-color1', 'main-bg-color2', 'main-bg-angle'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', updateMainBgPreview);
      el.addEventListener('change', updateMainBgPreview);
    }
  });

  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => applyPresetTheme(btn.dataset.preset));
  });

  // Modal Dossier
  const addFolderBtn = document.getElementById('add-folder-btn');
  if (addFolderBtn) {
    addFolderBtn.addEventListener('click', openAddFolderModal);
  }

  const folderForm = document.getElementById('folder-form');
  if (folderForm) {
    folderForm.addEventListener('submit', handleFolderSubmit);
  }

  document.querySelectorAll('input[name="folder-bg-type"]').forEach(r => {
    r.addEventListener('change', updateFolderBgControlsUI);
  });

  ['folder-bg-color1', 'folder-bg-color2', 'folder-bg-angle'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', updateFolderBgPreview);
      el.addEventListener('change', updateFolderBgPreview);
    }
  });

  document.querySelectorAll('.icon-opt').forEach(btn => {
    btn.addEventListener('click', () => selectIcon(btn.dataset.icon));
  });

  document.querySelectorAll('.color-opt').forEach(btn => {
    btn.addEventListener('click', () => selectColor(btn.dataset.color));
  });

  // Fermeture des modales
  document.querySelectorAll('.close-modal-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      closeFolderModal();
      closeThemeModal();
    });
  });

  const folderModal = document.getElementById('folder-modal');
  if (folderModal) {
    folderModal.addEventListener('click', (e) => {
      if (e.target === folderModal) closeFolderModal();
    });
  }

  const themeModal = document.getElementById('theme-modal');
  if (themeModal) {
    themeModal.addEventListener('click', (e) => {
      if (e.target === themeModal) closeThemeModal();
    });
  }

  // Thème Sombre / Clair (bouton sidebar)
  const themeBtn = document.getElementById('theme-btn');
  if (themeBtn) {
    themeBtn.addEventListener('click', toggleTheme);
  }

  // Mobile Menu
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
  const sidebar = document.getElementById('sidebar');

  if (mobileMenuBtn && sidebar) {
    mobileMenuBtn.addEventListener('click', () => sidebar.classList.add('open'));
  }
  if (toggleSidebarBtn && sidebar) {
    toggleSidebarBtn.addEventListener('click', () => sidebar.classList.remove('open'));
  }

  // Raccourcis clavier (Escape)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeFolderModal();
      closeThemeModal();
    }
  });
}

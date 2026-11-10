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
  selectColor,
  setFolderBgColor1,
  setFolderBgColor2,
  setFolderBgAngle,
  setMainBgColor1,
  setMainBgColor2,
  setMainBgAngle
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

  // Modal Personnalisation Fond & Paramètres (depuis la barre latérale en bas à gauche)
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

  // Swatches solides du thème principal
  document.querySelectorAll('#main-solid-swatches .solid-swatch').forEach(btn => {
    btn.addEventListener('click', () => {
      setMainBgColor1(btn.dataset.color);
      updateMainBgPreview();
    });
  });

  // Synchronisation Hex et Color Picker pour le thème principal
  const mainC1 = document.getElementById('main-bg-color1');
  const mainC1Hex = document.getElementById('main-bg-color1-hex');
  if (mainC1 && mainC1Hex) {
    mainC1.addEventListener('input', () => {
      mainC1Hex.value = mainC1.value.toUpperCase();
      updateMainBgPreview();
    });
    mainC1Hex.addEventListener('input', () => {
      let val = mainC1Hex.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        mainC1.value = val;
        setMainBgColor1(val);
        updateMainBgPreview();
      }
    });
  }

  const mainC2 = document.getElementById('main-bg-color2');
  const mainC2Hex = document.getElementById('main-bg-color2-hex');
  if (mainC2 && mainC2Hex) {
    mainC2.addEventListener('input', () => {
      mainC2Hex.value = mainC2.value.toUpperCase();
      updateMainBgPreview();
    });
    mainC2Hex.addEventListener('input', () => {
      let val = mainC2Hex.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        mainC2.value = val;
        setMainBgColor2(val);
        updateMainBgPreview();
      }
    });
  }

  // Pilules d'angle pour le thème principal
  document.querySelectorAll('#main-angle-pills .angle-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      setMainBgAngle(btn.dataset.angle);
      updateMainBgPreview();
    });
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

  // Swatches solides du dossier
  document.querySelectorAll('#folder-solid-swatches .solid-swatch').forEach(btn => {
    btn.addEventListener('click', () => {
      setFolderBgColor1(btn.dataset.color);
      updateFolderBgPreview();
    });
  });

  // Synchronisation Hex et Color Picker pour le dossier
  const folderC1 = document.getElementById('folder-bg-color1');
  const folderC1Hex = document.getElementById('folder-bg-color1-hex');
  if (folderC1 && folderC1Hex) {
    folderC1.addEventListener('input', () => {
      folderC1Hex.value = folderC1.value.toUpperCase();
      updateFolderBgPreview();
    });
    folderC1Hex.addEventListener('input', () => {
      let val = folderC1Hex.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        folderC1.value = val;
        setFolderBgColor1(val);
        updateFolderBgPreview();
      }
    });
  }

  const folderC2 = document.getElementById('folder-bg-color2');
  const folderC2Hex = document.getElementById('folder-bg-color2-hex');
  if (folderC2 && folderC2Hex) {
    folderC2.addEventListener('input', () => {
      folderC2Hex.value = folderC2.value.toUpperCase();
      updateFolderBgPreview();
    });
    folderC2Hex.addEventListener('input', () => {
      let val = folderC2Hex.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        folderC2.value = val;
        setFolderBgColor2(val);
        updateFolderBgPreview();
      }
    });
  }

  // Pilules d'angle pour le dossier
  document.querySelectorAll('#folder-angle-pills .angle-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      setFolderBgAngle(btn.dataset.angle);
      updateFolderBgPreview();
    });
  });

  document.querySelectorAll('.icon-opt').forEach(btn => {
    btn.addEventListener('click', () => selectIcon(btn.dataset.icon));
  });

  document.querySelectorAll('.color-opt').forEach(btn => {
    btn.addEventListener('click', () => selectColor(btn.dataset.color));
  });

  // Protection contre la fermeture intempestive : un clic à l'intérieur de la boîte modale ne doit JAMAIS fermer la modale
  document.querySelectorAll('.modal').forEach(m => {
    m.addEventListener('click', (e) => e.stopPropagation());
  });

  document.querySelectorAll('input[type="color"]').forEach(cp => {
    cp.addEventListener('click', (e) => e.stopPropagation());
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

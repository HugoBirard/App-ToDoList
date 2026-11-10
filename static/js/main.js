/**
 * Point d'entrée de l'application Frontend.
 * Initialise les modules, charge les données et configure les écouteurs d'événements.
 */

import { state } from './state.js';
import { fetchInitialData } from './api.js';
import { initTheme, toggleTheme, applyActiveBackground } from './theme.js';
import { initCustomDropdowns, updateFolderDropdown } from './components/dropdowns.js';
import { 
  initColorPopover, 
  openColorPopover, 
  closeColorPopover 
} from './components/colorpicker.js';
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
  initSyncUI, 
  initAutoSyncWatcher, 
  fetchStorageInfo 
} from './components/sync.js';
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
  initSyncUI(loadData);
  initAutoSyncWatcher(loadData);
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

    applyActiveBackground(true);
    renderFolders();
    updateFolderDropdown();
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

  // Initialisation du nuancier de couleur 100% In-App
  initColorPopover((targetKey, hexColor) => {
    if (targetKey === 'main1') {
      setMainBgColor1(hexColor);
      updateMainBgPreview();
    } else if (targetKey === 'main2') {
      setMainBgColor2(hexColor);
      updateMainBgPreview();
    } else if (targetKey === 'folder1') {
      setFolderBgColor1(hexColor);
      updateFolderBgPreview();
    } else if (targetKey === 'folder2') {
      setFolderBgColor2(hexColor);
      updateFolderBgPreview();
    }
  });

  // Boutons triggers ouvrant le nuancier intégré
  const mainBtn1 = document.getElementById('main-bg-color1-btn');
  if (mainBtn1) {
    mainBtn1.addEventListener('click', (e) => {
      e.stopPropagation();
      const current = document.getElementById('main-bg-color1')?.value || '#090a0d';
      openColorPopover('main1', mainBtn1, current);
    });
  }

  const mainBtn2 = document.getElementById('main-bg-color2-btn');
  if (mainBtn2) {
    mainBtn2.addEventListener('click', (e) => {
      e.stopPropagation();
      const current = document.getElementById('main-bg-color2')?.value || '#1a1d27';
      openColorPopover('main2', mainBtn2, current);
    });
  }

  const folderBtn1 = document.getElementById('folder-bg-color1-btn');
  if (folderBtn1) {
    folderBtn1.addEventListener('click', (e) => {
      e.stopPropagation();
      const current = document.getElementById('folder-bg-color1')?.value || '#161a24';
      openColorPopover('folder1', folderBtn1, current);
    });
  }

  const folderBtn2 = document.getElementById('folder-bg-color2-btn');
  if (folderBtn2) {
    folderBtn2.addEventListener('click', (e) => {
      e.stopPropagation();
      const current = document.getElementById('folder-bg-color2')?.value || '#2d3345';
      openColorPopover('folder2', folderBtn2, current);
    });
  }

  // Swatches solides du thème principal (1 clic pour appliquer)
  document.querySelectorAll('#main-solid-swatches .solid-swatch').forEach(btn => {
    btn.addEventListener('click', () => {
      setMainBgColor1(btn.dataset.color);
      updateMainBgPreview();
    });
  });

  // Synchronisation Hex pour le thème principal
  const mainC1 = document.getElementById('main-bg-color1');
  const mainC1Hex = document.getElementById('main-bg-color1-hex');
  if (mainC1 && mainC1Hex) {
    mainC1Hex.addEventListener('input', () => {
      let val = mainC1Hex.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        setMainBgColor1(val);
        updateMainBgPreview();
      }
    });
  }

  const mainC2 = document.getElementById('main-bg-color2');
  const mainC2Hex = document.getElementById('main-bg-color2-hex');
  if (mainC2 && mainC2Hex) {
    mainC2Hex.addEventListener('input', () => {
      let val = mainC2Hex.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
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

  // Swatches solides du dossier (1 clic pour appliquer)
  document.querySelectorAll('#folder-solid-swatches .solid-swatch').forEach(btn => {
    btn.addEventListener('click', () => {
      setFolderBgColor1(btn.dataset.color);
      updateFolderBgPreview();
    });
  });

  // Synchronisation Hex pour le dossier
  const folderC1 = document.getElementById('folder-bg-color1');
  const folderC1Hex = document.getElementById('folder-bg-color1-hex');
  if (folderC1 && folderC1Hex) {
    folderC1Hex.addEventListener('input', () => {
      let val = folderC1Hex.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        setFolderBgColor1(val);
        updateFolderBgPreview();
      }
    });
  }

  const folderC2 = document.getElementById('folder-bg-color2');
  const folderC2Hex = document.getElementById('folder-bg-color2-hex');
  if (folderC2 && folderC2Hex) {
    folderC2Hex.addEventListener('input', () => {
      let val = folderC2Hex.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
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
      closeColorPopover();
      closeFolderModal();
      closeThemeModal();
    });
  });

  const folderModal = document.getElementById('folder-modal');
  if (folderModal) {
    folderModal.addEventListener('click', (e) => {
      if (e.target === folderModal) {
        closeColorPopover();
        closeFolderModal();
      }
    });
  }

  const themeModal = document.getElementById('theme-modal');
  if (themeModal) {
    themeModal.addEventListener('click', (e) => {
      if (e.target === themeModal) {
        closeColorPopover();
        closeThemeModal();
      }
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

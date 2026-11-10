/**
 * Gestionnaire du moteur visuel : Thèmes Sombre/Clair et Arrière-plans dynamiques (fondu/couleur).
 */

import { state, DEFAULT_PRO_BG, DEFAULT_LIGHT_BG, PRESETS } from './state.js';
import { api } from './api.js';
import { renderIcon } from './icons.js';

let currentActiveBg = null;
let currentActiveLayer = 1;

export function applyActiveBackground(immediate = false) {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  let targetBg = null;

  // 1. Si on est dans un dossier avec un fond personnalisé dédié
  const currentViewNum = Number(state.currentView);
  if (!isNaN(currentViewNum) && currentViewNum > 0) {
    const folder = state.folders.find(f => Number(f.id) === currentViewNum);
    if (folder && folder.bg_type && folder.bg_type !== 'default') {
      if (folder.bg_type === 'solid' && folder.bg_color1) {
        targetBg = folder.bg_color1;
      } else if (folder.bg_type === 'gradient') {
        const c1 = folder.bg_color1 || '#161a24';
        const c2 = folder.bg_color2 || '#2d3345';
        const angle = folder.bg_angle || 135;
        targetBg = `linear-gradient(${angle}deg, ${c1} 0%, ${c2} 100%)`;
      }
    }
  }

  // 2. Si on est en mode clair
  if (!targetBg && isLight) {
    targetBg = DEFAULT_LIGHT_BG;
  }

  // 3. Sinon, restaurer le fond principal sombre
  if (!targetBg) {
    targetBg = state.mainBg || DEFAULT_PRO_BG;
  }

  if (targetBg === currentActiveBg) return;
  currentActiveBg = targetBg;

  // Définir la variable CSS sur la racine et sur le body
  document.documentElement.style.setProperty('--active-bg', targetBg);
  document.body.style.background = targetBg;

  const layer1 = document.getElementById('bg-layer-1');
  const layer2 = document.getElementById('bg-layer-2');

  // Si les couches n'existent pas encore (fallback)
  if (!layer1 || !layer2) {
    document.body.style.background = targetBg;
    return;
  }

  if (immediate) {
    layer1.style.background = targetBg;
    layer1.className = 'app-bg-layer active-layer';
    layer2.className = 'app-bg-layer hidden-layer';
    currentActiveLayer = 1;
    return;
  }

  // Fondu croisé ultra-fluide entre les 2 couches d'arrière-plan (zéro flash blanc)
  const nextLayer = currentActiveLayer === 1 ? layer2 : layer1;
  const prevLayer = currentActiveLayer === 1 ? layer1 : layer2;

  nextLayer.style.background = targetBg;
  nextLayer.className = 'app-bg-layer active-layer';
  prevLayer.className = 'app-bg-layer hidden-layer';

  currentActiveLayer = currentActiveLayer === 1 ? 2 : 1;
}

export function initTheme() {
  const saved = localStorage.getItem('todolist_theme') || 'dark';
  applyTheme(saved);
}

export function applyTheme(theme) {
  const themeIcon = document.getElementById('theme-icon');
  const themeLabel = document.getElementById('theme-label');

  if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    if (themeIcon) themeIcon.innerHTML = renderIcon('sun');
    if (themeLabel) themeLabel.textContent = 'Mode Clair';
  } else {
    document.documentElement.removeAttribute('data-theme');
    if (themeIcon) themeIcon.innerHTML = renderIcon('moon');
    if (themeLabel) themeLabel.textContent = 'Mode Sombre';
  }
  localStorage.setItem('todolist_theme', theme);
  applyActiveBackground();
}

export function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'light' ? 'dark' : 'light');
}

export async function setMainBackground(bgValue) {
  state.mainBg = bgValue;
  localStorage.setItem('todolist_main_bg', bgValue);
  if (document.documentElement.getAttribute('data-theme') === 'light') {
    applyTheme('dark');
  } else {
    applyActiveBackground();
  }
  await api('/api/settings', 'PUT', { main_background: bgValue });
}

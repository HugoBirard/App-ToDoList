/**
 * Gestionnaire du moteur visuel : Thèmes Sombre/Clair et Arrière-plans dynamiques (fondu/couleur).
 */

import { state, DEFAULT_PRO_BG, DEFAULT_LIGHT_BG, PRESETS } from './state.js';
import { api } from './api.js';
import { renderIcon } from './icons.js';

export function applyActiveBackground() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';

  // 1. Si on est dans un dossier avec un fond personnalisé dédié
  if (typeof state.currentView === 'number') {
    const folder = state.folders.find(f => f.id === state.currentView);
    if (folder && folder.bg_type && folder.bg_type !== 'default') {
      if (folder.bg_type === 'solid' && folder.bg_color1) {
        document.body.style.setProperty('--active-bg', folder.bg_color1);
        return;
      } else if (folder.bg_type === 'gradient' && folder.bg_color1 && folder.bg_color2) {
        const angle = folder.bg_angle || 135;
        const grad = `linear-gradient(${angle}deg, ${folder.bg_color1} 0%, ${folder.bg_color2} 100%)`;
        document.body.style.setProperty('--active-bg', grad);
        return;
      }
    }
  }

  // 2. Si on est en mode clair
  if (isLight) {
    document.body.style.setProperty('--active-bg', DEFAULT_LIGHT_BG);
    return;
  }

  // 3. Sinon, restaurer le fond principal sombre
  document.body.style.setProperty('--active-bg', state.mainBg || DEFAULT_PRO_BG);
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

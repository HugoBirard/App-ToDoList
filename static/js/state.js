/**
 * Gestion de l'état applicatif centralisé et constantes de design.
 */

export const DEFAULT_PRO_BG = 'linear-gradient(135deg, #08090c 0%, #131620 50%, #1a1e2b 100%)';
export const DEFAULT_LIGHT_BG = 'linear-gradient(135deg, #f8fafc 0%, #edf2f7 50%, #e2e8f0 100%)';

export const PRESETS = {
  // Essentiels Pro & Épurés
  'pro-dark': 'linear-gradient(135deg, #08090c 0%, #131620 50%, #1a1e2b 100%)',
  'carbon': 'linear-gradient(135deg, #050505 0%, #141414 50%, #1f1f1f 100%)',
  'midnight': 'linear-gradient(135deg, #070c18 0%, #0f1629 50%, #17213d 100%)',
  'slate': 'linear-gradient(135deg, #0f172a 0%, #172136 50%, #1e293b 100%)',
  'emerald': 'linear-gradient(135deg, #05140e 0%, #0a2017 50%, #102d21 100%)',
  'violet': 'linear-gradient(135deg, #11081c 0%, #190e29 50%, #25143a 100%)',

  // Nouveaux Univers Artistiques & Subcultures
  'street': 'linear-gradient(135deg, #0b0c10 0%, #171922 50%, #0d0e14 100%)',
  'techno': 'linear-gradient(180deg, #030304 0%, #0c0d10 50%, #060708 100%)',
  'cyberpunk': 'linear-gradient(135deg, #0c0317 0%, #1c0836 50%, #061928 100%)',
  'y2k': 'linear-gradient(135deg, #131525 0%, #20243e 50%, #1a162a 100%)',
  'arcade': 'linear-gradient(135deg, #180524 0%, #2a0b36 50%, #350f28 100%)',
  'luxury': 'linear-gradient(135deg, #0b0a0c 0%, #151318 50%, #1a1610 100%)',
  'zen': 'linear-gradient(135deg, #05130f 0%, #0b1c17 50%, #10241e 100%)'
};

export const THEME_PROFILES = {
  'pro-dark': { styleId: 'pro', accent: '#6366f1', titlebar: 'transparent' },
  'carbon': { styleId: 'carbon', accent: '#9ca3af', titlebar: 'match-bg' },
  'midnight': { styleId: 'midnight', accent: '#3b82f6', titlebar: 'transparent' },
  'slate': { styleId: 'slate', accent: '#38bdf8', titlebar: 'glass' },
  'emerald': { styleId: 'emerald', accent: '#10b981', titlebar: 'transparent' },
  'violet': { styleId: 'violet', accent: '#a855f7', titlebar: 'transparent' },
  'street': { styleId: 'street', accent: '#ccff00', titlebar: 'street' },
  'techno': { styleId: 'techno', accent: '#ffffff', titlebar: 'techno' },
  'cyberpunk': { styleId: 'cyberpunk', accent: '#ff007f', titlebar: 'cyberpunk' },
  'y2k': { styleId: 'y2k', accent: '#e879f9', titlebar: 'y2k' },
  'arcade': { styleId: 'arcade', accent: '#f43f5e', titlebar: 'arcade' },
  'luxury': { styleId: 'luxury', accent: '#f59e0b', titlebar: 'luxury' },
  'zen': { styleId: 'zen', accent: '#34d399', titlebar: 'zen' }
};

export const state = {
  folders: [],
  tasks: [],
  settings: {},
  mainBg: DEFAULT_PRO_BG,
  currentView: 'all',    // 'all', 'pending', 'completed', ou folderId (int)
  currentFilter: 'all',  // 'all', 'pending', 'completed'
  searchQuery: '',
};

export function getCurrentViewTasks() {
  if (state.currentView === 'pending') {
    return state.tasks.filter(t => !t.completed);
  } else if (state.currentView === 'completed') {
    return state.tasks.filter(t => t.completed);
  } else if (typeof state.currentView === 'number') {
    return state.tasks.filter(t => t.folder_id === state.currentView);
  }
  return state.tasks;
}

export function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Gestion de l'état applicatif centralisé et constantes de design.
 */

export const DEFAULT_PRO_BG = 'linear-gradient(135deg, #08090c 0%, #131620 50%, #1a1e2b 100%)';
export const DEFAULT_LIGHT_BG = 'linear-gradient(135deg, #f8fafc 0%, #edf2f7 50%, #e2e8f0 100%)';

export const PRESETS = {
  'pro-dark': 'linear-gradient(135deg, #08090c 0%, #131620 50%, #1a1e2b 100%)',
  'carbon': 'linear-gradient(135deg, #050505 0%, #141414 50%, #1f1f1f 100%)',
  'midnight': 'linear-gradient(135deg, #070c18 0%, #0f1629 50%, #17213d 100%)',
  'slate': 'linear-gradient(135deg, #0f172a 0%, #172136 50%, #1e293b 100%)',
  'emerald': 'linear-gradient(135deg, #05140e 0%, #0a2017 50%, #102d21 100%)',
  'violet': 'linear-gradient(135deg, #11081c 0%, #190e29 50%, #25143a 100%)'
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

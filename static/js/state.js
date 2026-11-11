/**
 * Gestion de l'état applicatif centralisé et constantes de design.
 */

export const DEFAULT_PRO_BG = 'linear-gradient(135deg, #08090c 0%, #131620 50%, #1a1e2b 100%)';
export const DEFAULT_LIGHT_BG = 'linear-gradient(135deg, #f8fafc 0%, #edf2f7 50%, #e2e8f0 100%)';

export const PRESETS = {
  // Essentiels Pro & Épurés (Classiques conservés)
  'pro-dark': 'linear-gradient(135deg, #08090c 0%, #131620 50%, #1a1e2b 100%)',
  'carbon': 'linear-gradient(135deg, #050505 0%, #141414 50%, #1f1f1f 100%)',
  'midnight': 'linear-gradient(135deg, #070c18 0%, #0f1629 50%, #17213d 100%)',
  'slate': 'linear-gradient(135deg, #0f172a 0%, #172136 50%, #1e293b 100%)',
  'emerald': 'linear-gradient(135deg, #05140e 0%, #0a2017 50%, #102d21 100%)',
  'violet': 'linear-gradient(135deg, #11081c 0%, #190e29 50%, #25143a 100%)',

  // Nouveaux Univers Artistiques & Subcultures Immersifs (Textures et décors complets)
  'street': 'url("/assets/themes/street-brick-graffiti.svg") center / cover no-repeat fixed #0b0c10',
  'techno': 'url("/assets/themes/techno-concrete-laser.svg") center / cover no-repeat fixed #030304',
  'cyberpunk': 'url("/assets/themes/cyberpunk-netrunner-hack.svg") center / cover no-repeat fixed #05010a',
  'y2k': 'url("/assets/themes/y2k-liquid-chrome.svg") center / cover no-repeat fixed #131525',
  'arcade': 'url("/assets/themes/arcade-synthwave-grid.svg") center / cover no-repeat fixed #180524',
  'luxury': 'url("/assets/themes/luxury-black-gold-marble.svg") center / cover no-repeat fixed #0b0a0c',
  'zen': 'url("/assets/themes/zen-mist-bamboo.svg") center / cover no-repeat fixed #05130f',
  'lava': 'url("/assets/themes/lava-lamp-magma.svg") center / cover no-repeat fixed #18020a'
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
  'zen': { styleId: 'zen', accent: '#34d399', titlebar: 'zen' },
  'lava': { styleId: 'lava', accent: '#ff5500', titlebar: 'lava' }
};

export const state = {
  salons: [],
  currentSalonId: 1,     // ID du salon/espace actif
  folders: [],
  tasks: [],
  settings: {},
  mainBg: DEFAULT_PRO_BG,
  currentView: 'all',    // 'all', 'pending', 'completed', ou folderId (int)
  currentFilter: 'all',  // 'all', 'pending', 'completed'
  searchQuery: '',
};

export function getActiveSalon() {
  if (!state.salons || state.salons.length === 0) return null;
  return state.salons.find(s => s.id === state.currentSalonId) || state.salons[0];
}

export function getActiveSalonFolderIds() {
  const active = getActiveSalon();
  if (!active) return state.folders.map(f => f.id);
  return state.folders.filter(f => !f.salon_id || f.salon_id === active.id).map(f => f.id);
}

export function getCurrentViewTasks() {
  const activeFolderIds = new Set(getActiveSalonFolderIds());
  const salonTasks = state.tasks.filter(t => !t.folder_id || activeFolderIds.has(t.folder_id));

  if (state.currentView === 'pending') {
    return salonTasks.filter(t => !t.completed);
  } else if (state.currentView === 'completed') {
    return salonTasks.filter(t => t.completed);
  } else if (typeof state.currentView === 'number') {
    return salonTasks.filter(t => t.folder_id === state.currentView);
  }
  return salonTasks;
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

/**
 * Composant de gestion des fenêtres modales (Dossier & Personnalisation de fond).
 */

import { state, DEFAULT_PRO_BG, PRESETS } from '../state.js';
import { api } from '../api.js';
import { applyActiveBackground, setMainBackground } from '../theme.js';
import { renderFolders, selectFolderView } from './folders.js';
import { EMOJI_MAP } from '../icons.js';

// ==========================================
// MODAL DOSSIER
// ==========================================

export function openAddFolderModal() {
  const modal = document.getElementById('folder-modal');
  const title = document.getElementById('folder-modal-title');
  const idInput = document.getElementById('folder-id');
  const nameInput = document.getElementById('folder-name-input');
  const weeklyInput = document.getElementById('folder-weekly-input');

  title.textContent = "Nouveau dossier";
  idInput.value = '';
  nameInput.value = '';
  weeklyInput.checked = false;

  document.querySelector('input[name="folder-bg-type"][value="default"]').checked = true;
  document.getElementById('folder-bg-color1').value = '#161a24';
  document.getElementById('folder-bg-color2').value = '#2d3345';
  document.getElementById('folder-bg-angle').value = '135';
  updateFolderBgControlsUI();

  selectIcon('folder');
  selectColor('#4f46e5');
  modal.classList.remove('hidden');
  nameInput.focus();
}

export function openEditFolderModal(folderId) {
  const folder = state.folders.find(f => f.id === folderId);
  if (!folder) return;

  const modal = document.getElementById('folder-modal');
  const title = document.getElementById('folder-modal-title');
  const idInput = document.getElementById('folder-id');
  const nameInput = document.getElementById('folder-name-input');
  const weeklyInput = document.getElementById('folder-weekly-input');

  title.textContent = "Modifier le dossier";
  idInput.value = folder.id;
  nameInput.value = folder.name;
  weeklyInput.checked = Boolean(folder.auto_reset_weekly);

  const bgType = folder.bg_type || 'default';
  const radio = document.querySelector(`input[name="folder-bg-type"][value="${bgType}"]`);
  if (radio) radio.checked = true;

  document.getElementById('folder-bg-color1').value = folder.bg_color1 || '#161a24';
  document.getElementById('folder-bg-color2').value = folder.bg_color2 || '#2d3345';
  document.getElementById('folder-bg-angle').value = String(folder.bg_angle || 135);
  updateFolderBgControlsUI();

  const iconKey = EMOJI_MAP[folder.icon] || folder.icon || 'folder';
  selectIcon(iconKey);
  selectColor(folder.color || '#4f46e5');
  modal.classList.remove('hidden');
  nameInput.focus();
}

export function closeFolderModal() {
  document.getElementById('folder-modal').classList.add('hidden');
}

export function selectIcon(iconName) {
  const mapped = EMOJI_MAP[iconName] || iconName || 'folder';
  const input = document.getElementById('folder-icon-input');
  if (input) input.value = mapped;
  document.querySelectorAll('.icon-opt').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.icon === mapped);
  });
}

export function selectEmoji(emoji) {
  selectIcon(emoji);
}

export function selectColor(color) {
  document.getElementById('folder-color-input').value = color;
  document.querySelectorAll('.color-opt').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.color === color);
  });
}

export function updateFolderBgControlsUI() {
  const selectedType = document.querySelector('input[name="folder-bg-type"]:checked').value;
  const controls = document.getElementById('folder-bg-controls');
  const c1Label = document.getElementById('folder-c1-label');
  const c2Wrap = document.getElementById('folder-c2-wrap');
  const angleWrap = document.getElementById('folder-angle-wrap');

  if (selectedType === 'default') {
    controls.classList.add('hidden');
  } else {
    controls.classList.remove('hidden');
    if (selectedType === 'solid') {
      c1Label.textContent = "Couleur";
      c2Wrap.classList.add('hidden');
      angleWrap.classList.add('hidden');
    } else {
      c1Label.textContent = "Couleur 1";
      c2Wrap.classList.remove('hidden');
      angleWrap.classList.remove('hidden');
    }
  }
  updateFolderBgPreview();
}

export function updateFolderBgPreview() {
  const selectedType = document.querySelector('input[name="folder-bg-type"]:checked').value;
  const c1 = document.getElementById('folder-bg-color1').value;
  const c2 = document.getElementById('folder-bg-color2').value;
  const angle = document.getElementById('folder-bg-angle').value;
  const preview = document.getElementById('folder-bg-preview');

  if (selectedType === 'default') {
    preview.style.background = state.mainBg || DEFAULT_PRO_BG;
  } else if (selectedType === 'solid') {
    preview.style.background = c1;
  } else {
    preview.style.background = `linear-gradient(${angle}deg, ${c1} 0%, ${c2} 100%)`;
  }
}

export async function handleFolderSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('folder-name-input').value.trim();
  const icon = document.getElementById('folder-icon-input').value;
  const color = document.getElementById('folder-color-input').value;
  const folderId = document.getElementById('folder-id').value;
  const autoResetWeekly = document.getElementById('folder-weekly-input').checked ? 1 : 0;

  const bgType = document.querySelector('input[name="folder-bg-type"]:checked').value;
  const bgColor1 = document.getElementById('folder-bg-color1').value;
  const bgColor2 = document.getElementById('folder-bg-color2').value;
  const bgAngle = parseInt(document.getElementById('folder-bg-angle').value, 10);

  if (!name) return;

  const folderData = { 
    name, 
    icon, 
    color, 
    auto_reset_weekly: autoResetWeekly,
    bg_type: bgType,
    bg_color1: bgColor1,
    bg_color2: bgColor2,
    bg_angle: bgAngle
  };

  if (folderId) {
    const updated = await api(`/api/folders/${folderId}`, 'PUT', folderData);
    if (updated) {
      const idx = state.folders.findIndex(f => f.id === parseInt(folderId));
      if (idx !== -1) state.folders[idx] = updated;
    }
  } else {
    const created = await api('/api/folders', 'POST', folderData);
    if (created) {
      state.folders.push(created);
      selectFolderView(created.id);
    }
  }

  closeFolderModal();
  applyActiveBackground();
  renderFolders();
}

// ==========================================
// MODAL THÈME PRINCIPAL
// ==========================================

export function openThemeModal() {
  updateMainBgControlsUI();
  updateMainBgPreview();
  document.getElementById('theme-modal').classList.remove('hidden');
}

export function closeThemeModal() {
  document.getElementById('theme-modal').classList.add('hidden');
}

export function updateMainBgControlsUI() {
  const selectedType = document.querySelector('input[name="main-bg-type"]:checked').value;
  const c1Label = document.getElementById('main-c1-label');
  const c2Wrap = document.getElementById('main-c2-wrap');
  const angleWrap = document.getElementById('main-angle-wrap');

  if (selectedType === 'solid') {
    c1Label.textContent = "Couleur";
    c2Wrap.classList.add('hidden');
    angleWrap.classList.add('hidden');
  } else {
    c1Label.textContent = "Couleur 1";
    c2Wrap.classList.remove('hidden');
    angleWrap.classList.remove('hidden');
  }
  updateMainBgPreview();
}

export function getCurrentMainBgValue() {
  const selectedType = document.querySelector('input[name="main-bg-type"]:checked').value;
  const c1 = document.getElementById('main-bg-color1').value;
  const c2 = document.getElementById('main-bg-color2').value;
  const angle = document.getElementById('main-bg-angle').value;

  if (selectedType === 'solid') return c1;
  return `linear-gradient(${angle}deg, ${c1} 0%, ${c2} 100%)`;
}

export function updateMainBgPreview() {
  const bg = getCurrentMainBgValue();
  document.getElementById('main-bg-preview').style.background = bg;
}

export async function applyPresetTheme(presetKey) {
  const bg = PRESETS[presetKey] || DEFAULT_PRO_BG;
  await setMainBackground(bg);
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === presetKey);
  });
  closeThemeModal();
}

export async function saveMainTheme() {
  const bg = getCurrentMainBgValue();
  await setMainBackground(bg);
  document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
  closeThemeModal();
}

export function resetDefaultTheme() {
  applyPresetTheme('pro-dark');
}

/**
 * Composant de gestion des fenêtres modales (Dossier, Thèmes & Dialogues de confirmation).
 */

import { state, DEFAULT_PRO_BG, PRESETS } from '../state.js';
import { api } from '../api.js';
import { applyActiveBackground, setMainBackground } from '../theme.js';
import { renderFolders, selectFolderView } from './folders.js';
import { EMOJI_MAP, renderIcon } from '../icons.js';

// ==========================================
// MODAL DE CONFIRMATION MODERNE & DIALOGUE
// ==========================================

export function showConfirmDialog({
  title = "Confirmation",
  message = "Êtes-vous sûr de vouloir continuer ?",
  confirmText = "Confirmer",
  cancelText = "Annuler",
  isDanger = false,
  icon = "help-circle"
} = {}) {
  return new Promise((resolve) => {
    const modal = document.getElementById('confirm-modal');
    const titleEl = document.getElementById('confirm-title');
    const msgEl = document.getElementById('confirm-message');
    const okBtn = document.getElementById('confirm-ok-btn');
    const cancelBtn = document.getElementById('confirm-cancel-btn');
    const iconWrap = document.getElementById('confirm-icon-wrap');
    const iconEl = document.getElementById('confirm-icon');

    if (!modal) return resolve(false);

    titleEl.textContent = title;
    msgEl.textContent = message;
    okBtn.textContent = confirmText;

    if (cancelText) {
      cancelBtn.textContent = cancelText;
      cancelBtn.classList.remove('hidden');
    } else {
      cancelBtn.classList.add('hidden');
    }

    if (isDanger) {
      okBtn.className = "btn btn-danger";
      iconWrap.className = "confirm-icon-wrap danger";
    } else {
      okBtn.className = "btn btn-primary";
      iconWrap.className = "confirm-icon-wrap primary";
    }

    iconEl.innerHTML = renderIcon(icon);
    modal.classList.remove('hidden');

    function cleanup(result) {
      modal.classList.add('hidden');
      okBtn.onclick = null;
      cancelBtn.onclick = null;
      modal.onclick = null;
      document.removeEventListener('keydown', handleKey);
      resolve(result);
    }

    function handleKey(e) {
      if (e.key === 'Escape') cleanup(false);
      else if (e.key === 'Enter') cleanup(true);
    }

    okBtn.onclick = (e) => {
      e.stopPropagation();
      cleanup(true);
    };

    cancelBtn.onclick = (e) => {
      e.stopPropagation();
      cleanup(false);
    };

    modal.onclick = (e) => {
      if (e.target === modal) cleanup(false);
    };

    document.addEventListener('keydown', handleKey);
  });
}

export function showNotificationDialog({
  title = "Information",
  message = "",
  icon = "info"
} = {}) {
  return showConfirmDialog({
    title,
    message,
    confirmText: "Compris",
    cancelText: "",
    isDanger: false,
    icon
  });
}

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

  const defaultRadio = document.querySelector('input[name="folder-bg-type"][value="default"]');
  if (defaultRadio) defaultRadio.checked = true;

  setFolderBgColor1('#161a24');
  setFolderBgColor2('#2d3345');
  setFolderBgAngle(135);
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

  setFolderBgColor1(folder.bg_color1 || '#161a24');
  setFolderBgColor2(folder.bg_color2 || '#2d3345');
  setFolderBgAngle(folder.bg_angle || 135);
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

export function selectColor(color) {
  document.getElementById('folder-color-input').value = color;
  document.querySelectorAll('.color-opt').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.color === color);
  });
}

// Helpers de synchronisation des couleurs et angles du dossier
function setFolderBgColor1(color) {
  const c = color || '#161a24';
  const input = document.getElementById('folder-bg-color1');
  const hex = document.getElementById('folder-bg-color1-hex');
  if (input) input.value = c;
  if (hex) hex.value = c.toUpperCase();
  document.querySelectorAll('#folder-solid-swatches .solid-swatch').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.color.toLowerCase() === c.toLowerCase());
  });
}

function setFolderBgColor2(color) {
  const c = color || '#2d3345';
  const input = document.getElementById('folder-bg-color2');
  const hex = document.getElementById('folder-bg-color2-hex');
  if (input) input.value = c;
  if (hex) hex.value = c.toUpperCase();
}

function setFolderBgAngle(angle) {
  const a = String(angle || 135);
  const hidden = document.getElementById('folder-bg-angle');
  if (hidden) hidden.value = a;
  document.querySelectorAll('#folder-angle-pills .angle-pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.angle === a);
  });
}

export function updateFolderBgControlsUI() {
  const checkedRadio = document.querySelector('input[name="folder-bg-type"]:checked');
  const selectedType = checkedRadio ? checkedRadio.value : 'default';
  const controls = document.getElementById('folder-bg-controls');
  const solidPalette = document.getElementById('folder-solid-palette');
  const c1Label = document.getElementById('folder-c1-label');
  const c2Wrap = document.getElementById('folder-c2-wrap');
  const angleWrap = document.getElementById('folder-angle-wrap');

  if (selectedType === 'default') {
    if (controls) controls.classList.add('hidden');
  } else {
    if (controls) controls.classList.remove('hidden');
    if (selectedType === 'solid') {
      if (solidPalette) solidPalette.classList.remove('hidden');
      if (c1Label) c1Label.textContent = "Couleur unie";
      if (c2Wrap) c2Wrap.classList.add('hidden');
      if (angleWrap) angleWrap.classList.add('hidden');
    } else {
      // Dégradé
      if (solidPalette) solidPalette.classList.add('hidden');
      if (c1Label) c1Label.textContent = "Couleur 1";
      if (c2Wrap) c2Wrap.classList.remove('hidden');
      if (angleWrap) angleWrap.classList.remove('hidden');
    }
  }
  updateFolderBgPreview();
}

export function updateFolderBgPreview() {
  const checkedRadio = document.querySelector('input[name="folder-bg-type"]:checked');
  const selectedType = checkedRadio ? checkedRadio.value : 'default';
  const c1 = document.getElementById('folder-bg-color1')?.value || '#161a24';
  const c2 = document.getElementById('folder-bg-color2')?.value || '#2d3345';
  const angle = document.getElementById('folder-bg-angle')?.value || '135';
  const preview = document.getElementById('folder-bg-preview');

  if (!preview) return;

  if (selectedType === 'default') {
    preview.style.background = state.mainBg || DEFAULT_PRO_BG;
    preview.textContent = "Thème principal par défaut";
  } else if (selectedType === 'solid') {
    preview.style.background = c1;
    preview.textContent = `Couleur unie : ${c1.toUpperCase()}`;
  } else {
    preview.style.background = `linear-gradient(${angle}deg, ${c1} 0%, ${c2} 100%)`;
    preview.textContent = `Dégradé (${angle}°)`;
  }
}

export async function handleFolderSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('folder-name-input').value.trim();
  const icon = document.getElementById('folder-icon-input').value;
  const color = document.getElementById('folder-color-input').value;
  const folderId = document.getElementById('folder-id').value;
  const autoResetWeekly = document.getElementById('folder-weekly-input').checked ? 1 : 0;

  const bgTypeRadio = document.querySelector('input[name="folder-bg-type"]:checked');
  const bgType = bgTypeRadio ? bgTypeRadio.value : 'default';
  const bgColor1 = document.getElementById('folder-bg-color1').value;
  const bgColor2 = document.getElementById('folder-bg-color2').value;
  const bgAngle = parseInt(document.getElementById('folder-bg-angle').value, 10) || 135;

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

function setMainBgColor1(color) {
  const c = color || '#090a0d';
  const input = document.getElementById('main-bg-color1');
  const hex = document.getElementById('main-bg-color1-hex');
  if (input) input.value = c;
  if (hex) hex.value = c.toUpperCase();
  document.querySelectorAll('#main-solid-swatches .solid-swatch').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.color.toLowerCase() === c.toLowerCase());
  });
}

function setMainBgColor2(color) {
  const c = color || '#1a1d27';
  const input = document.getElementById('main-bg-color2');
  const hex = document.getElementById('main-bg-color2-hex');
  if (input) input.value = c;
  if (hex) hex.value = c.toUpperCase();
}

function setMainBgAngle(angle) {
  const a = String(angle || 135);
  const hidden = document.getElementById('main-bg-angle');
  if (hidden) hidden.value = a;
  document.querySelectorAll('#main-angle-pills .angle-pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.angle === a);
  });
}

export function updateMainBgControlsUI() {
  const checkedRadio = document.querySelector('input[name="main-bg-type"]:checked');
  const selectedType = checkedRadio ? checkedRadio.value : 'gradient';
  const solidPalette = document.getElementById('main-solid-palette');
  const c1Label = document.getElementById('main-c1-label');
  const c2Wrap = document.getElementById('main-c2-wrap');
  const angleWrap = document.getElementById('main-angle-wrap');

  if (selectedType === 'solid') {
    if (solidPalette) solidPalette.classList.remove('hidden');
    if (c1Label) c1Label.textContent = "Couleur unie";
    if (c2Wrap) c2Wrap.classList.add('hidden');
    if (angleWrap) angleWrap.classList.add('hidden');
  } else {
    // Dégradé
    if (solidPalette) solidPalette.classList.add('hidden');
    if (c1Label) c1Label.textContent = "Couleur 1";
    if (c2Wrap) c2Wrap.classList.remove('hidden');
    if (angleWrap) angleWrap.classList.remove('hidden');
  }
  updateMainBgPreview();
}

export function getCurrentMainBgValue() {
  const checkedRadio = document.querySelector('input[name="main-bg-type"]:checked');
  const selectedType = checkedRadio ? checkedRadio.value : 'gradient';
  const c1 = document.getElementById('main-bg-color1')?.value || '#090a0d';
  const c2 = document.getElementById('main-bg-color2')?.value || '#1a1d27';
  const angle = document.getElementById('main-bg-angle')?.value || '135';

  if (selectedType === 'solid') return c1;
  return `linear-gradient(${angle}deg, ${c1} 0%, ${c2} 100%)`;
}

export function updateMainBgPreview() {
  const bg = getCurrentMainBgValue();
  const preview = document.getElementById('main-bg-preview');
  if (!preview) return;
  preview.style.background = bg;
  const checkedRadio = document.querySelector('input[name="main-bg-type"]:checked');
  const isSolid = checkedRadio && checkedRadio.value === 'solid';
  const c1 = document.getElementById('main-bg-color1')?.value || '';
  preview.textContent = isSolid ? `Couleur unie : ${c1.toUpperCase()}` : `Aperçu dégradé en direct`;
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

export { setFolderBgColor1, setFolderBgColor2, setFolderBgAngle, setMainBgColor1, setMainBgColor2, setMainBgAngle };

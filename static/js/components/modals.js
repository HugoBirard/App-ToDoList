/**
 * Composant de gestion des fenêtres modales (Dossier, Thèmes & Dialogues de confirmation).
 */

import { state, DEFAULT_PRO_BG, PRESETS, THEME_PROFILES } from '../state.js';
import { api } from '../api.js';
import { applyActiveBackground, setMainBackground, applyThemeStyle } from '../theme.js';
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

export function showNotificationDialog(optionsOrTitle = "Information", messageArg = "", iconArg = "info") {
  let title = "Information";
  let message = "";
  let icon = "info";

  if (typeof optionsOrTitle === "object" && optionsOrTitle !== null) {
    title = optionsOrTitle.title || "Information";
    message = optionsOrTitle.message || "";
    icon = optionsOrTitle.icon || "info";
  } else {
    title = String(optionsOrTitle || "Information");
    message = String(messageArg || "");
    icon = iconArg || "info";
  }

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

function populateFolderSalonSelect(selectedSalonId) {
  const hiddenInput = document.getElementById('folder-salon-select');
  const dd = document.getElementById('folder-salon-dropdown');
  if (!hiddenInput) return;

  const currentSalons = state.salons || [];
  const activeId = selectedSalonId || state.currentSalonId || (currentSalons[0]?.id);
  hiddenInput.value = activeId || '';

  if (dd) {
    const label = dd.querySelector('.dropdown-label');
    const menu = dd.querySelector('.dropdown-menu');
    const activeSalon = currentSalons.find(s => s.id === activeId) || currentSalons[0];
    if (label && activeSalon) {
      label.textContent = activeSalon.name;
    }

    if (menu) {
      menu.innerHTML = '';
      currentSalons.forEach(s => {
        const isSelected = s.id === activeId;
        const item = document.createElement('div');
        item.className = `dropdown-option ${isSelected ? 'selected' : ''}`;
        item.dataset.value = s.id;
        item.innerHTML = `
          <span class="salon-color-dot" style="background-color: ${s.color || '#4f46e5'};"></span>
          <span class="opt-text">${escapeHtml(s.name)}</span>
          <span class="opt-check">${renderIcon('check')}</span>
        `;
        item.onclick = (e) => {
          e.stopPropagation();
          hiddenInput.value = s.id;
          if (label) label.textContent = s.name;
          dd.querySelectorAll('.dropdown-option').forEach(o => o.classList.toggle('selected', o.dataset.value == s.id));
          dd.classList.remove('open');
        };
        menu.appendChild(item);
      });
    }
  }
}

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
  populateFolderSalonSelect(state.currentSalonId);
  const submitBtn = document.getElementById('folder-submit-btn');
  if (submitBtn) submitBtn.textContent = "Créer le dossier";

  const defaultRadio = document.querySelector('input[name="folder-bg-type"][value="default"]');
  if (defaultRadio) defaultRadio.checked = true;

  const presetHidden = document.getElementById('folder-bg-preset-val');
  if (presetHidden) presetHidden.value = 'street';
  document.querySelectorAll('.folder-preset-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === 'street');
  });

  updateFolderImageUI('');

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
  populateFolderSalonSelect(folder.salon_id || state.currentSalonId);
  const submitBtn = document.getElementById('folder-submit-btn');
  if (submitBtn) submitBtn.textContent = "Enregistrer les modifications";

  const bgType = folder.bg_type || 'default';
  const radio = document.querySelector(`input[name="folder-bg-type"][value="${bgType}"]`);
  if (radio) radio.checked = true;

  const presetVal = (bgType === 'preset' && folder.bg_color1) ? folder.bg_color1 : 'street';
  const presetHidden = document.getElementById('folder-bg-preset-val');
  if (presetHidden) presetHidden.value = presetVal;
  document.querySelectorAll('.folder-preset-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === presetVal);
  });

  const imageVal = ((bgType === 'image' || bgType === 'custom') && folder.bg_color1) ? folder.bg_color1 : '';
  updateFolderImageUI(imageVal);

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
  const btn = document.getElementById('folder-bg-color1-btn');
  if (input) input.value = c;
  if (hex) hex.value = c.toUpperCase();
  if (btn) btn.style.backgroundColor = c;
  document.querySelectorAll('#folder-solid-swatches .solid-swatch').forEach(s => {
    s.classList.toggle('active', s.dataset.color.toLowerCase() === c.toLowerCase());
  });
}

function setFolderBgColor2(color) {
  const c = color || '#2d3345';
  const input = document.getElementById('folder-bg-color2');
  const hex = document.getElementById('folder-bg-color2-hex');
  const btn = document.getElementById('folder-bg-color2-btn');
  if (input) input.value = c;
  if (hex) hex.value = c.toUpperCase();
  if (btn) btn.style.backgroundColor = c;
}

function setFolderBgAngle(angle) {
  const a = String(angle || 135);
  const hidden = document.getElementById('folder-bg-angle');
  if (hidden) hidden.value = a;
  document.querySelectorAll('#folder-angle-pills .angle-pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.angle === a);
  });
}

export function updateFolderImageUI(imageUrl) {
  const previewWrap = document.getElementById('folder-user-bg-preview-wrap');
  const removeBtn = document.getElementById('folder-user-bg-remove-btn');
  const uploadBtn = document.getElementById('folder-user-bg-btn');
  const hiddenVal = document.getElementById('folder-bg-image-val');

  if (imageUrl) {
    if (hiddenVal) hiddenVal.value = imageUrl;
    if (previewWrap) {
      previewWrap.classList.remove('hidden');
      const match = imageUrl.match(/url\((['"]?)(.*?)\1\)/);
      const url = match ? match[2] : imageUrl;
      previewWrap.style.backgroundImage = `url("${url}")`;
      previewWrap.style.backgroundSize = 'cover';
      previewWrap.style.backgroundPosition = 'center';
    }
    if (removeBtn) removeBtn.classList.remove('hidden');
    if (uploadBtn) {
      uploadBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather-icon" style="width: 15px; height: 15px;"><polyline points="20 6 9 17 4 12"/></svg>
        Changer l'image...
      `;
    }
  } else {
    if (hiddenVal) hiddenVal.value = '';
    if (previewWrap) {
      previewWrap.classList.add('hidden');
      previewWrap.style.backgroundImage = '';
    }
    if (removeBtn) removeBtn.classList.add('hidden');
    if (uploadBtn) {
      uploadBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather-icon" style="width: 15px; height: 15px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        Choisir une image pour ce dossier...
      `;
    }
  }
}

export function updateFolderBgControlsUI() {
  const checkedRadio = document.querySelector('input[name="folder-bg-type"]:checked');
  const selectedType = checkedRadio ? checkedRadio.value : 'default';
  const presetSection = document.getElementById('folder-preset-section');
  const controls = document.getElementById('folder-bg-controls');
  const solidPalette = document.getElementById('folder-solid-palette');
  const c1Label = document.getElementById('folder-c1-label');
  const c2Wrap = document.getElementById('folder-c2-wrap');
  const angleWrap = document.getElementById('folder-angle-wrap');
  const imageSection = document.getElementById('folder-image-section');

  if (presetSection) presetSection.classList.add('hidden');
  if (controls) controls.classList.add('hidden');
  if (imageSection) imageSection.classList.add('hidden');

  if (selectedType === 'preset') {
    if (presetSection) presetSection.classList.remove('hidden');
  } else if (selectedType === 'image') {
    if (imageSection) imageSection.classList.remove('hidden');
  } else if (selectedType === 'solid') {
    if (controls) controls.classList.remove('hidden');
    if (solidPalette) solidPalette.classList.remove('hidden');
    if (c1Label) c1Label.textContent = "Couleur unie";
    if (c2Wrap) c2Wrap.classList.add('hidden');
    if (angleWrap) angleWrap.classList.add('hidden');
  } else if (selectedType === 'gradient') {
    if (controls) controls.classList.remove('hidden');
    if (solidPalette) solidPalette.classList.add('hidden');
    if (c1Label) c1Label.textContent = "Couleur 1";
    if (c2Wrap) c2Wrap.classList.remove('hidden');
    if (angleWrap) angleWrap.classList.remove('hidden');
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
    preview.textContent = "Thème principal de l'application";
  } else if (selectedType === 'preset') {
    const presetKey = document.getElementById('folder-bg-preset-val')?.value || 'street';
    preview.style.background = PRESETS[presetKey] || DEFAULT_PRO_BG;
    preview.textContent = `Univers : ${presetKey.toUpperCase()}`;
  } else if (selectedType === 'image') {
    const imgVal = document.getElementById('folder-bg-image-val')?.value || '';
    if (imgVal) {
      const match = imgVal.match(/url\((['"]?)(.*?)\1\)/);
      const url = match ? match[2] : imgVal;
      preview.style.background = `url("${url}") center/cover no-repeat`;
      preview.textContent = "Photo perso active pour ce dossier";
    } else {
      preview.style.background = '#1a1d27';
      preview.textContent = "Aucune image sélectionnée pour ce dossier";
    }
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

  let bgColor1 = '';
  let bgColor2 = '';
  let bgAngle = 135;

  if (bgType === 'preset') {
    bgColor1 = document.getElementById('folder-bg-preset-val')?.value || 'street';
  } else if (bgType === 'image') {
    bgColor1 = document.getElementById('folder-bg-image-val')?.value || '';
    if (!bgColor1) {
      alert("Veuillez sélectionner une image pour ce dossier ou choisir un autre style de fond.");
      return;
    }
  } else if (bgType === 'solid') {
    bgColor1 = document.getElementById('folder-bg-color1').value;
  } else if (bgType === 'gradient') {
    bgColor1 = document.getElementById('folder-bg-color1').value;
    bgColor2 = document.getElementById('folder-bg-color2').value;
    bgAngle = parseInt(document.getElementById('folder-bg-angle').value, 10) || 135;
  }

  if (!name) return;

  const salonSelect = document.getElementById('folder-salon-select');
  const salonId = salonSelect ? (parseInt(salonSelect.value, 10) || state.currentSalonId) : state.currentSalonId;

  const folderData = { 
    name, 
    salon_id: salonId,
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
      selectFolderView(parseInt(folderId, 10));
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

let currentModalBgState = {
  type: 'gradient', // 'preset', 'custom-image', 'generator'
  presetKey: null,
  value: null
};

export function markModalGeneratorSelected() {
  currentModalBgState = { type: 'generator', presetKey: null, value: null };
  document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
}

export function openThemeModal() {
  const curBg = state.mainBg || '';
  const isCustomUserImage = curBg.includes('custom-background') || curBg.includes('data:image/') || 
    (curBg.includes('url(') && !curBg.includes('/assets/themes/'));

  const matchingPresetKey = Object.keys(PRESETS).find(k => PRESETS[k] === curBg);

  if (isCustomUserImage) {
    currentModalBgState = { type: 'custom-image', value: curBg, presetKey: null };
  } else if (matchingPresetKey) {
    currentModalBgState = { type: 'preset', value: curBg, presetKey: matchingPresetKey };
  } else {
    currentModalBgState = { type: 'generator', value: curBg, presetKey: null };
  }

  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === currentModalBgState.presetKey);
  });

  updateMainBgControlsUI();
  updateMainBgPreview();
  syncTitlebarStyleUI();
  updateCustomBgUI();
  document.getElementById('theme-modal').classList.remove('hidden');
}

export function closeThemeModal() {
  document.getElementById('theme-modal').classList.add('hidden');
}

function setMainBgColor1(color) {
  markModalGeneratorSelected();
  const c = color || '#090a0d';
  const input = document.getElementById('main-bg-color1');
  const hex = document.getElementById('main-bg-color1-hex');
  const btn = document.getElementById('main-bg-color1-btn');
  if (input) input.value = c;
  if (hex) hex.value = c.toUpperCase();
  if (btn) btn.style.backgroundColor = c;
  document.querySelectorAll('#main-solid-swatches .solid-swatch').forEach(s => {
    s.classList.toggle('active', s.dataset.color.toLowerCase() === c.toLowerCase());
  });
}

function setMainBgColor2(color) {
  markModalGeneratorSelected();
  const c = color || '#1a1d27';
  const input = document.getElementById('main-bg-color2');
  const hex = document.getElementById('main-bg-color2-hex');
  const btn = document.getElementById('main-bg-color2-btn');
  if (input) input.value = c;
  if (hex) hex.value = c.toUpperCase();
  if (btn) btn.style.backgroundColor = c;
}

function setMainBgAngle(angle) {
  markModalGeneratorSelected();
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
  const profile = THEME_PROFILES[presetKey];
  currentModalBgState = { type: 'preset', value: bg, presetKey };
  if (profile) {
    applyThemeStyle(profile.styleId, profile.accent);
    if (profile.titlebar) {
      await applyTitlebarStyle(profile.titlebar);
    }
  }
  await setMainBackground(bg);
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === presetKey);
  });
  updateCustomBgUI();
  closeThemeModal();
}

export async function saveMainTheme() {
  let targetBg;
  if (currentModalBgState.type === 'custom-image') {
    targetBg = currentModalBgState.value || state.mainBg;
    applyThemeStyle('pro');
  } else if (currentModalBgState.type === 'preset' && currentModalBgState.presetKey) {
    targetBg = PRESETS[currentModalBgState.presetKey] || DEFAULT_PRO_BG;
    const profile = THEME_PROFILES[currentModalBgState.presetKey];
    if (profile) applyThemeStyle(profile.styleId, profile.accent);
  } else {
    targetBg = getCurrentMainBgValue();
    document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
  }

  await setMainBackground(targetBg);

  // Sauvegarder également le style de la barre de titre
  const titlebarInput = document.getElementById('main-titlebar-style');
  if (titlebarInput && titlebarInput.value) {
    await applyTitlebarStyle(titlebarInput.value);
  }

  closeThemeModal();
}

export function resetDefaultTheme() {
  applyPresetTheme('pro-dark');
  applyTitlebarStyle('transparent');
}

export function syncTitlebarStyleUI() {
  const currentStyle = (state.settings && state.settings.titlebar_style) || 'transparent';
  const hidden = document.getElementById('main-titlebar-style');
  if (hidden) hidden.value = currentStyle;
  document.querySelectorAll('.titlebar-option-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.titlebar === currentStyle);
  });
}

export async function applyTitlebarStyle(styleKey) {
  const cleanStyle = styleKey || 'transparent';
  const hidden = document.getElementById('main-titlebar-style');
  if (hidden) hidden.value = cleanStyle;

  document.querySelectorAll('.titlebar-option-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.titlebar === cleanStyle);
  });

  // Notifier GTK4 immédiatement si exécuté dans la fenêtre native WebKit
  if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.set_titlebar_style) {
    try {
      const curBg = getCurrentMainBgValue ? getCurrentMainBgValue() : null;
      window.webkit.messageHandlers.set_titlebar_style.postMessage(JSON.stringify({
        style: cleanStyle,
        bg_color: curBg
      }));
    } catch (e) {
      console.warn("Erreur notification message GTK4:", e);
    }
  }

  // Sauvegarder dans la base de données
  try {
    await api('/api/settings', 'PUT', { titlebar_style: cleanStyle });
    if (!state.settings) state.settings = {};
    state.settings.titlebar_style = cleanStyle;
  } catch (e) {
    console.error("Erreur enregistrement réglage titlebar_style:", e);
  }
}

export function initTitlebarOptions() {
  document.querySelectorAll('.titlebar-option-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const styleKey = btn.dataset.titlebar;
      applyTitlebarStyle(styleKey);
    });
  });
}

// ==========================================
// IMAGE DE FOND PERSONNALISÉE PAR L'UTILISATEUR
// ==========================================

export function updateCustomBgUI() {
  const previewWrap = document.getElementById('custom-user-bg-preview-wrap');
  const removeBtn = document.getElementById('custom-user-bg-remove-btn');
  const uploadBtn = document.getElementById('custom-user-bg-btn');
  const curBg = state.mainBg || '';

  const isCustomUserImage = curBg.includes('custom-background') || curBg.includes('data:image/') || 
    (curBg.includes('url(') && !curBg.includes('/assets/themes/'));

  if (isCustomUserImage) {
    if (previewWrap) {
      previewWrap.classList.remove('hidden');
      const match = curBg.match(/url\((['"]?)(.*?)\1\)/);
      const url = match ? match[2] : curBg;
      previewWrap.style.backgroundImage = `url("${url}")`;
      previewWrap.style.backgroundSize = 'cover';
      previewWrap.style.backgroundPosition = 'center';
    }
    if (removeBtn) removeBtn.classList.remove('hidden');
    if (uploadBtn) {
      uploadBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather-icon" style="width: 15px; height: 15px;"><polyline points="20 6 9 17 4 12"/></svg>
        Changer mon image...
      `;
    }
  } else {
    if (previewWrap) previewWrap.classList.add('hidden');
    if (removeBtn) removeBtn.classList.add('hidden');
    if (uploadBtn) {
      uploadBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather-icon" style="width: 15px; height: 15px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        Choisir une image sur mon PC...
      `;
    }
  }
}

export function initCustomBackgroundUpload() {
  const fileInput = document.getElementById('custom-user-bg-file');
  const uploadBtn = document.getElementById('custom-user-bg-btn');
  const removeBtn = document.getElementById('custom-user-bg-remove-btn');
  const previewWrap = document.getElementById('custom-user-bg-preview-wrap');

  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      // Afficher immédiatement l'aperçu dans la modale
      try {
        const localBlobUrl = URL.createObjectURL(file);
        if (previewWrap) {
          previewWrap.classList.remove('hidden');
          previewWrap.style.backgroundImage = `url("${localBlobUrl}")`;
          previewWrap.style.backgroundSize = 'cover';
          previewWrap.style.backgroundPosition = 'center';
        }
      } catch (err) {
        console.warn('createObjectURL preview non disponible:', err);
      }

      const origBtnHtml = uploadBtn.innerHTML;
      uploadBtn.disabled = true;
      uploadBtn.textContent = 'Enregistrement en cours...';

      const reader = new FileReader();
      reader.onload = (loadEvt) => {
        const rawData = loadEvt.target.result;
        
        // Redimensionner l'image si besoin via un canvas pour fluidité maximale
        const img = new Image();
        img.onload = async () => {
          const maxDim = 1920;
          let w = img.width;
          let h = img.height;

          if (w > maxDim || h > maxDim) {
            if (w > h) {
              h = Math.round((h * maxDim) / w);
              w = maxDim;
            } else {
              w = Math.round((w * maxDim) / h);
              h = maxDim;
            }
          }

          const canvas = document.createElement('canvas');
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, w, h);

          const optimizedDataUrl = canvas.toDataURL('image/jpeg', 0.85);

          try {
            const res = await api('/api/upload/background', 'POST', { image: optimizedDataUrl });
            if (res && res.success && res.bg_value) {
              currentModalBgState = { type: 'custom-image', value: res.bg_value, presetKey: null };
              applyThemeStyle('pro');
              await setMainBackground(res.bg_value);
              updateCustomBgUI();
              document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
              
              uploadBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather-icon" style="width: 15px; height: 15px;"><polyline points="20 6 9 17 4 12"/></svg>
                Changer mon image...
              `;
            } else {
              alert(res?.error || 'Erreur lors de l\'enregistrement de l\'image.');
              uploadBtn.innerHTML = origBtnHtml;
            }
          } catch (err) {
            console.error('Erreur upload background:', err);
            alert('Impossible de téléverser l\'image : ' + (err.message || ''));
            uploadBtn.innerHTML = origBtnHtml;
          } finally {
            uploadBtn.disabled = false;
            fileInput.value = '';
          }
        };
        img.src = rawData;
      };
      reader.readAsDataURL(file);
    });
  }

  if (removeBtn) {
    removeBtn.addEventListener('click', async () => {
      currentModalBgState = { type: 'preset', presetKey: 'pro-dark', value: PRESETS['pro-dark'] };
      await applyPresetTheme('pro-dark');
      updateCustomBgUI();
    });
  }
}

// ==========================================
// IMAGE DE FOND PERSONNALISÉE POUR UN DOSSIER
// ==========================================

export function initFolderBackgroundUpload() {
  const fileInput = document.getElementById('folder-user-bg-file');
  const uploadBtn = document.getElementById('folder-user-bg-btn');
  const removeBtn = document.getElementById('folder-user-bg-remove-btn');
  const previewWrap = document.getElementById('folder-user-bg-preview-wrap');
  const hiddenVal = document.getElementById('folder-bg-image-val');

  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      try {
        const localBlobUrl = URL.createObjectURL(file);
        if (previewWrap) {
          previewWrap.classList.remove('hidden');
          previewWrap.style.backgroundImage = `url("${localBlobUrl}")`;
          previewWrap.style.backgroundSize = 'cover';
          previewWrap.style.backgroundPosition = 'center';
        }
      } catch (err) {
        console.warn('createObjectURL preview non disponible:', err);
      }

      const origBtnHtml = uploadBtn.innerHTML;
      uploadBtn.disabled = true;
      uploadBtn.textContent = 'Enregistrement en cours...';

      const reader = new FileReader();
      reader.onload = (loadEvt) => {
        const rawData = loadEvt.target.result;
        const img = new Image();
        img.onload = async () => {
          const maxDim = 1920;
          let w = img.width;
          let h = img.height;

          if (w > maxDim || h > maxDim) {
            if (w > h) {
              h = Math.round((h * maxDim) / w);
              w = maxDim;
            } else {
              w = Math.round((w * maxDim) / h);
              h = maxDim;
            }
          }

          const canvas = document.createElement('canvas');
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, w, h);

          const optimizedDataUrl = canvas.toDataURL('image/jpeg', 0.85);

          try {
            const folderId = document.getElementById('folder-id')?.value || 0;
            const res = await api('/api/upload/background', 'POST', {
              image: optimizedDataUrl,
              scope: 'folder',
              folder_id: folderId
            });
            if (res && res.success && res.bg_value) {
              if (hiddenVal) hiddenVal.value = res.bg_value;
              updateFolderImageUI(res.bg_value);
              updateFolderBgPreview();
            } else {
              alert(res?.error || 'Erreur lors de l\'enregistrement de l\'image.');
              uploadBtn.innerHTML = origBtnHtml;
            }
          } catch (err) {
            console.error('Erreur upload background dossier:', err);
            alert('Impossible de téléverser l\'image : ' + (err.message || ''));
            uploadBtn.innerHTML = origBtnHtml;
          } finally {
            uploadBtn.disabled = false;
            fileInput.value = '';
          }
        };
        img.src = rawData;
      };
      reader.readAsDataURL(file);
    });
  }

  if (removeBtn) {
    removeBtn.addEventListener('click', () => {
      updateFolderImageUI('');
      updateFolderBgPreview();
    });
  }
}

export { 
  setFolderBgColor1, 
  setFolderBgColor2, 
  setFolderBgAngle, 
  setMainBgColor1, 
  setMainBgColor2, 
  setMainBgAngle 
};

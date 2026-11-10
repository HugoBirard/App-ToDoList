/**
 * Sélecteur de couleur 100% In-App (Web Native).
 * Remplace définitivement <input type="color"> sous Linux GTK/Wayland,
 * éliminant les fermetures inopinées de fenêtres et les boîtes de dialogue natives cassées.
 */

let currentTarget = null;
let onColorSelectCallback = null;

export function initColorPopover(callback) {
  onColorSelectCallback = callback;
  const popover = document.getElementById('app-color-popover');
  if (!popover) return;

  // Swatches dans le popover
  popover.querySelectorAll('.p-swatch').forEach(swatch => {
    swatch.addEventListener('click', (e) => {
      e.stopPropagation();
      const color = swatch.dataset.color;
      selectColorFromPopover(color);
    });
  });

  // Slider de teinte spectre
  const hueSlider = document.getElementById('popover-hue-slider');
  if (hueSlider) {
    hueSlider.addEventListener('input', (e) => {
      e.stopPropagation();
      const hue = parseInt(e.target.value, 10);
      const hex = hslToHex(hue, 65, 20); // nuance sombre élégante
      updatePopoverPreview(hex);
    });
  }

  // Saisie manuelle hex
  const hexInput = document.getElementById('popover-hex-input');
  if (hexInput) {
    hexInput.addEventListener('input', (e) => {
      e.stopPropagation();
      let val = hexInput.value.trim();
      if (!val.startsWith('#') && val.length > 0) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        updatePopoverPreview(val, false);
      }
    });
  }

  // Bouton Choisir / Valider
  const applyBtn = document.getElementById('popover-apply-btn');
  if (applyBtn) {
    applyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const hexInput = document.getElementById('popover-hex-input');
      if (hexInput) {
        let val = hexInput.value.trim();
        if (!val.startsWith('#')) val = '#' + val;
        if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
          selectColorFromPopover(val);
        }
      }
      closeColorPopover();
    });
  }

  // Bouton fermer
  const closeBtn = document.getElementById('popover-close-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeColorPopover();
    });
  }

  // Empêcher les clics à l'intérieur du popover de se propager
  popover.addEventListener('click', (e) => e.stopPropagation());

  // Fermer si clic ailleurs
  document.addEventListener('click', (e) => {
    if (!popover.classList.contains('hidden') && !e.target.closest('.color-picker-trigger')) {
      closeColorPopover();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !popover.classList.contains('hidden')) {
      closeColorPopover();
    }
  });
}

export function openColorPopover(targetKey, triggerBtn, currentColor) {
  const popover = document.getElementById('app-color-popover');
  if (!popover || !triggerBtn) return;

  // Si on clique sur le même bouton alors qu'il est déjà ouvert, on le ferme
  if (currentTarget === targetKey && !popover.classList.contains('hidden')) {
    closeColorPopover();
    return;
  }

  currentTarget = targetKey;
  const color = (currentColor || '#090A0D').toUpperCase();

  updatePopoverPreview(color, true);

  // Positionner le popover de façon intelligente par rapport au bouton trigger
  popover.classList.remove('hidden');
  const rect = triggerBtn.getBoundingClientRect();
  const popoverWidth = 290;
  const popoverHeight = 320;

  let left = rect.left;
  let top = rect.bottom + 8;

  // Éviter de déborder de l'écran à droite
  if (left + popoverWidth > window.innerWidth - 16) {
    left = window.innerWidth - popoverWidth - 16;
  }
  if (left < 16) left = 16;

  // Éviter de déborder en bas
  if (top + popoverHeight > window.innerHeight - 16) {
    top = rect.top - popoverHeight - 8;
  }
  if (top < 16) top = 16;

  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;

  // Marquer le trigger actif
  document.querySelectorAll('.color-picker-trigger').forEach(b => b.classList.remove('active'));
  triggerBtn.classList.add('active');
}

export function closeColorPopover() {
  const popover = document.getElementById('app-color-popover');
  if (popover) {
    popover.classList.add('hidden');
  }
  document.querySelectorAll('.color-picker-trigger').forEach(b => b.classList.remove('active'));
  currentTarget = null;
}

function updatePopoverPreview(hexColor, updateInput = true) {
  const c = hexColor.toUpperCase();
  const preview = document.getElementById('popover-preview-swatch');
  const hexInput = document.getElementById('popover-hex-input');

  if (preview) preview.style.backgroundColor = c;
  if (hexInput && updateInput) hexInput.value = c;

  const popover = document.getElementById('app-color-popover');
  if (popover) {
    popover.querySelectorAll('.p-swatch').forEach(s => {
      s.classList.toggle('active', s.dataset.color.toUpperCase() === c);
    });
  }
}

function selectColorFromPopover(hexColor) {
  if (!currentTarget) return;
  const c = hexColor.toUpperCase();
  if (onColorSelectCallback) {
    onColorSelectCallback(currentTarget, c);
  }
  closeColorPopover();
}

function hslToHex(h, s, l) {
  l /= 100;
  const a = s * Math.min(l, 1 - l) / 100;
  const f = n => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`.toUpperCase();
}

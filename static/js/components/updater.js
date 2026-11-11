/**
 * Composant de détection et d'application des mises à jour en 1 clic.
 * Affiche la notification in-app et gère la mise à jour sécurisée.
 */

import { api } from '../api.js';
import { showConfirmDialog } from './modals.js';

let updateAvailable = false;
let updateInfo = null;

export async function checkForUpdates(silent = true) {
  const checkBtn = document.getElementById('check-updates-btn');
  const origBtnText = checkBtn ? checkBtn.innerHTML : '';
  if (checkBtn && !silent) {
    checkBtn.disabled = true;
    checkBtn.textContent = 'Recherche en cours...';
  }

  try {
    const res = await api('/api/system/update-status');
    if (!res) {
      if (!silent) renderUpdateSettingsStatus('Impossible de joindre le service de mise à jour.', 'warning');
      return;
    }

    updateInfo = res;

    if (res.update_available) {
      updateAvailable = true;
      showUpdateBanner(res);
      showTabBadge(true);
      renderUpdateSettingsUI(res);
    } else {
      updateAvailable = false;
      hideUpdateBanner();
      showTabBadge(false);
      renderUpdateSettingsUI(res);
      if (!silent) {
        renderUpdateSettingsStatus('✅ Votre application ToDoList est parfaitement à jour !', 'success');
      }
    }
  } catch (err) {
    console.warn('Erreur vérification mise à jour:', err);
    if (!silent) {
      renderUpdateSettingsStatus('Erreur de connexion au serveur.', 'error');
    }
  } finally {
    if (checkBtn && !silent) {
      checkBtn.disabled = false;
      checkBtn.innerHTML = origBtnText;
    }
  }
}

export async function applyUpdate() {
  const bannerBtn = document.getElementById('update-banner-apply-btn');
  const modalBtn = document.getElementById('apply-update-btn');

  const setButtonsLoading = (loading) => {
    [bannerBtn, modalBtn].forEach(btn => {
      if (!btn) return;
      btn.disabled = loading;
      if (loading) {
        btn.dataset.origHtml = btn.innerHTML;
        btn.innerHTML = `
          <span class="spinner-small" style="display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 6px;"></span>
          Mise à jour en cours...
        `;
      } else if (btn.dataset.origHtml) {
        btn.innerHTML = btn.dataset.origHtml;
      }
    });
  };

  setButtonsLoading(true);

  try {
    const res = await api('/api/system/apply-update', 'POST');
    if (res && res.success) {
      hideUpdateBanner();
      showTabBadge(false);

      const reload = await showConfirmDialog({
        title: "🎉 Mise à jour installée avec succès !",
        message: "La nouvelle version de ToDoList est prête.\nVos données, tâches et dossiers ont été intégralement préservés.\n\nSouhaitez-vous recharger l'application maintenant pour appliquer les changements ?",
        confirmText: "Relancer l'application",
        cancelText: "Plus tard",
        icon: "check"
      });

      if (reload) {
        window.location.reload();
      } else {
        renderUpdateSettingsStatus('✅ Mise à jour installée ! Les changements prendront effet au prochain démarrage.', 'success');
      }
    } else {
      alert("Impossible d'appliquer la mise à jour : " + (res?.error || "Erreur inconnue"));
    }
  } catch (err) {
    console.error('Erreur application mise à jour:', err);
    alert("Erreur lors de la mise à jour : " + (err.message || ''));
  } finally {
    setButtonsLoading(false);
  }
}

function showUpdateBanner(info) {
  const banner = document.getElementById('update-notification-banner');
  const titleEl = document.getElementById('update-banner-title');
  const subEl = document.getElementById('update-banner-subtitle');

  if (!banner) return;

  const count = info.behind_count || 1;
  if (titleEl) {
    titleEl.textContent = `🚀 Nouvelle version disponible (${count} amélioration${count > 1 ? 's' : ''}) !`;
  }
  if (subEl) {
    if (info.commits && info.commits.length > 0) {
      subEl.textContent = `Dernier ajout : « ${info.commits[0].message} »`;
    } else {
      subEl.textContent = "Des améliorations et correctifs sont prêts à être installés.";
    }
  }

  banner.classList.remove('hidden');
}

function hideUpdateBanner() {
  const banner = document.getElementById('update-notification-banner');
  if (banner) banner.classList.add('hidden');
}

function showTabBadge(show) {
  const badge = document.getElementById('tab-update-badge');
  if (badge) badge.classList.toggle('hidden', !show);
}

function renderUpdateSettingsStatus(msg, type = 'info') {
  const statusEl = document.getElementById('update-status-msg');
  if (!statusEl) return;
  statusEl.textContent = msg;
  statusEl.className = `update-status-banner status-${type}`;
}

function renderUpdateSettingsUI(info) {
  const commitEl = document.getElementById('update-current-commit');
  const branchEl = document.getElementById('update-current-branch');
  const applyBtn = document.getElementById('apply-update-btn');
  const commitListWrap = document.getElementById('update-commits-preview');
  const commitListUl = document.getElementById('update-commits-list');

  if (commitEl) commitEl.textContent = info.current_commit || 'inconnu';
  if (branchEl) branchEl.textContent = info.branch || 'main';

  if (info.update_available) {
    renderUpdateSettingsStatus(`🎉 ${info.behind_count || 1} nouvelle(s) mise(s) à jour disponible(s) !`, 'accent');
    if (applyBtn) applyBtn.classList.remove('hidden');

    if (commitListWrap && commitListUl && info.commits && info.commits.length > 0) {
      commitListUl.innerHTML = info.commits.map(c => `
        <li>
          <code class="commit-hash">${c.hash}</code>
          <span class="commit-msg">${escapeHtml(c.message)}</span>
        </li>
      `).join('');
      commitListWrap.classList.remove('hidden');
    }
  } else {
    renderUpdateSettingsStatus(info.offline ? '⚠️ Mode hors-ligne : vérification impossible' : '✅ Votre application ToDoList est à jour.', info.offline ? 'warning' : 'success');
    if (applyBtn) applyBtn.classList.add('hidden');
    if (commitListWrap) commitListWrap.classList.add('hidden');
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function initUpdateUI() {
  const bannerApplyBtn = document.getElementById('update-banner-apply-btn');
  const bannerDismissBtn = document.getElementById('update-banner-dismiss-btn');
  const checkBtn = document.getElementById('check-updates-btn');
  const applyBtn = document.getElementById('apply-update-btn');

  if (bannerApplyBtn) bannerApplyBtn.addEventListener('click', applyUpdate);
  if (bannerDismissBtn) bannerDismissBtn.addEventListener('click', hideUpdateBanner);
  if (checkBtn) checkBtn.addEventListener('click', () => checkForUpdates(false));
  if (applyBtn) applyBtn.addEventListener('click', applyUpdate);

  // Vérification discrète en arrière-plan au démarrage (après 1.5s)
  setTimeout(() => {
    checkForUpdates(true);
  }, 1500);
}

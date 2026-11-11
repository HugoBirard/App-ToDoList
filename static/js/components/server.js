/**
 * Composant de gestion du Mode Serveur Réseau (Client Distant et Hébergement d'Équipe).
 */

import { getApiBase, setApiBase, getApiToken, setApiToken, testServerConnection, fetchNetworkInfo } from '../api.js';
import { showNotificationDialog } from './modals.js';

export function updateServerStatusUI() {
  const currentBase = getApiBase();
  const currentToken = getApiToken();
  const badge = document.getElementById('server-connection-badge');
  const currentUrlText = document.getElementById('server-current-url-text');
  const remotePill = document.getElementById('remote-server-pill');
  const remotePillText = document.getElementById('remote-server-pill-text');
  const input = document.getElementById('remote-server-input');
  const tokenInput = document.getElementById('remote-server-token');

  if (currentToken && tokenInput && !tokenInput.value) {
    tokenInput.value = currentToken;
  }

  if (currentBase) {
    if (badge) {
      badge.textContent = 'Serveur Distant (Connecté)';
      badge.className = 'sync-badge shared';
    }
    if (currentUrlText) currentUrlText.textContent = `${currentBase} (Serveur d'équipe distant)`;
    if (input && !input.value) input.value = currentBase;

    if (remotePill && remotePillText) {
      try {
        const parsed = new URL(currentBase);
        remotePillText.textContent = `Serveur : ${parsed.host}`;
      } catch {
        remotePillText.textContent = `Serveur : ${currentBase}`;
      }
      remotePill.classList.remove('hidden');
    }
  } else {
    if (badge) {
      badge.textContent = 'Serveur Local (127.0.0.1)';
      badge.className = 'sync-badge local';
    }
    if (currentUrlText) currentUrlText.textContent = 'http://127.0.0.1:4848 (Base de données locale)';
    if (remotePill) remotePill.classList.add('hidden');
  }
}

export function initServerUI(loadDataCallback) {
  const input = document.getElementById('remote-server-input');
  const tokenInput = document.getElementById('remote-server-token');
  const testBtn = document.getElementById('remote-server-test-btn');
  const connectBtn = document.getElementById('remote-server-connect-btn');
  const disconnectBtn = document.getElementById('remote-server-disconnect-btn');
  const quickDisconnectBtn = document.getElementById('remote-server-pill-disconnect');
  const feedback = document.getElementById('remote-server-feedback');

  function showFeedback(msg, type) {
    if (!feedback) return;
    feedback.textContent = msg;
    feedback.className = `discord-feedback ${type}`;
    feedback.classList.remove('hidden');
  }

  // 1. Tester la connexion
  if (testBtn) {
    testBtn.onclick = async () => {
      const targetUrl = (input?.value || '').trim();
      const token = (tokenInput?.value || '').trim();
      if (!targetUrl) {
        showFeedback('Veuillez renseigner l\'URL du serveur distant.', 'error');
        return;
      }

      const origText = testBtn.textContent;
      testBtn.disabled = true;
      testBtn.textContent = 'Test en cours...';

      const res = await testServerConnection(targetUrl, token);
      testBtn.disabled = false;
      testBtn.textContent = origText;

      if (res.success) {
        showFeedback(`✅ Connexion réussie au serveur ! (${res.foldersCount} dossier(s), ${res.tasksCount} tâche(s))`, 'success');
      } else {
        showFeedback(`❌ Impossible de joindre le serveur : ${res.message}`, 'error');
      }
    };
  }

  // 2. Se connecter au serveur distant
  if (connectBtn) {
    connectBtn.onclick = async () => {
      const targetUrl = (input?.value || '').trim();
      const token = (tokenInput?.value || '').trim();
      if (!targetUrl) {
        showFeedback('Veuillez renseigner l\'URL du serveur distant.', 'error');
        return;
      }

      connectBtn.disabled = true;
      const testRes = await testServerConnection(targetUrl, token);
      connectBtn.disabled = false;

      if (!testRes.success) {
        showFeedback(`❌ Connexion échouée : ${testRes.message}. Vérifiez l'adresse et le jeton d'accès.`, 'error');
        return;
      }

      setApiBase(targetUrl);
      setApiToken(token);
      updateServerStatusUI();
      showFeedback('✅ Connecté avec succès ! Chargement des tâches du serveur...', 'success');

      if (loadDataCallback) await loadDataCallback();

      showNotificationDialog(
        'Connexion Réseau Réussie',
        `Votre application est désormais synchronisée en direct avec le serveur d'équipe à l'adresse :\n${targetUrl}`
      );
    };
  }

  // 3. Déconnexion (Revenir en mode local)
  const handleDisconnect = async () => {
    setApiBase('');
    setApiToken('');
    if (input) input.value = '';
    if (tokenInput) tokenInput.value = '';
    updateServerStatusUI();
    showFeedback('Mode local restauré.', 'success');
    if (loadDataCallback) await loadDataCallback();
    showNotificationDialog(
      'Mode Local Activé',
      'Votre application utilise à nouveau sa base de données locale autonome.'
    );
  };

  if (disconnectBtn) disconnectBtn.onclick = handleDisconnect;
  if (quickDisconnectBtn) quickDisconnectBtn.onclick = handleDisconnect;

  // 4. Charger et afficher les adresses LAN disponibles
  loadLanAddresses();

  // Mise à jour initiale de l'état
  updateServerStatusUI();
}

async function loadLanAddresses() {
  const container = document.getElementById('server-lan-urls-container');
  if (!container) return;

  try {
    const netInfo = await fetchNetworkInfo();
    if (netInfo && netInfo.network_urls && netInfo.network_urls.length > 0) {
      container.innerHTML = '';
      netInfo.network_urls.forEach(url => {
        const item = document.createElement('div');
        item.className = 'server-lan-item';

        const span = document.createElement('span');
        span.textContent = url;
        item.appendChild(span);

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-secondary copy-url-btn';
        btn.textContent = 'Copier';
        btn.onclick = async () => {
          try {
            await navigator.clipboard.writeText(url);
            const prev = btn.textContent;
            btn.textContent = 'Copié !';
            setTimeout(() => btn.textContent = prev, 2000);
          } catch (err) {
            console.warn('Clipboard write failed:', err);
          }
        };
        item.appendChild(btn);

        container.appendChild(item);
      });
    } else {
      const textElem = document.getElementById('server-detected-lan-url');
      if (textElem) textElem.textContent = 'Lancez avec ./lancer-serveur-equipe.sh pour diffuser sur le réseau.';
    }
  } catch (err) {
    console.warn('Network info unavailable:', err);
  }
}

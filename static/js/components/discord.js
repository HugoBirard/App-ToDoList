/**
 * Composant de configuration et gestion de l'intégration Discord.
 * Permet d'activer les Webhooks Discord pour notifier une équipe de projet.
 */

import { api } from '../api.js';
import { state } from '../state.js';
import { showNotificationDialog } from './modals.js';

export function updateDiscordUIFromState() {
  const settings = state.settings || {};

  const enabledToggle = document.getElementById('discord-enabled-toggle');
  const urlInput = document.getElementById('discord-webhook-url');
  const authorInput = document.getElementById('discord-author-name');
  const badge = document.getElementById('discord-status-badge');

  const evtCreated = document.getElementById('discord-evt-created');
  const evtCompleted = document.getElementById('discord-evt-completed');
  const evtDeleted = document.getElementById('discord-evt-deleted');
  const evtFolder = document.getElementById('discord-evt-folder');

  const isEnabled = String(settings.discord_enabled) === '1';

  if (enabledToggle) enabledToggle.checked = isEnabled;
  if (urlInput) urlInput.value = settings.discord_webhook_url || '';
  if (authorInput) authorInput.value = settings.discord_author_name || '';

  if (evtCreated) evtCreated.checked = settings.discord_notify_created !== '0';
  if (evtCompleted) evtCompleted.checked = settings.discord_notify_completed !== '0';
  if (evtDeleted) evtDeleted.checked = settings.discord_notify_deleted !== '0';
  if (evtFolder) evtFolder.checked = settings.discord_notify_folder !== '0';

  if (badge) {
    if (isEnabled && settings.discord_webhook_url) {
      badge.textContent = 'Actif (Connecté)';
      badge.className = 'sync-badge shared';
    } else {
      badge.textContent = 'Inactif';
      badge.className = 'sync-badge local';
    }
  }
}

export function initDiscordUI() {
  const enabledToggle = document.getElementById('discord-enabled-toggle');
  const badge = document.getElementById('discord-status-badge');
  const testBtn = document.getElementById('discord-test-btn');
  const saveBtn = document.getElementById('discord-save-btn');
  const feedback = document.getElementById('discord-test-feedback');

  if (enabledToggle && badge) {
    enabledToggle.addEventListener('change', () => {
      if (enabledToggle.checked) {
        badge.textContent = 'Actif (Connecté)';
        badge.className = 'sync-badge shared';
      } else {
        badge.textContent = 'Inactif';
        badge.className = 'sync-badge local';
      }
    });
  }

  // Activer automatiquement le toggle dès que l'utilisateur commence à taper ou colle son URL
  const urlInputEl = document.getElementById('discord-webhook-url');
  if (urlInputEl && enabledToggle && badge) {
    urlInputEl.addEventListener('input', () => {
      const val = urlInputEl.value.trim();
      if (val && !val.startsWith('••••')) {
        enabledToggle.checked = true;
        badge.textContent = 'Prêt à connecter';
        badge.className = 'sync-badge shared';
      }
    });
  }

  // Tester le webhook
  if (testBtn) {
    testBtn.onclick = async () => {
      const urlInput = document.getElementById('discord-webhook-url');
      const authorInput = document.getElementById('discord-author-name');
      let webhookUrl = (urlInput?.value || '').trim().replace(/['"]/g, '');
      const authorName = (authorInput?.value || '').trim() || 'Équipe';

      // Si l'utilisateur n'a rien mis dans le champ, vérifier si une URL est déjà enregistrée en base
      const hasConfigured = state.settings?.discord_webhook_configured || 
        (state.settings?.discord_webhook_url && state.settings.discord_webhook_url.startsWith('••••'));

      if (!webhookUrl && !hasConfigured) {
        showFeedback('Veuillez coller l\'URL de Webhook de votre salon Discord.', 'error');
        return;
      }

      // Si l'URL commence sans https://, l'ajouter
      if (webhookUrl && !webhookUrl.startsWith('••••') && !webhookUrl.startsWith('http://') && !webhookUrl.startsWith('https://')) {
        webhookUrl = 'https://' + webhookUrl;
        if (urlInput) urlInput.value = webhookUrl;
      }

      if (webhookUrl && !webhookUrl.startsWith('••••')) {
        const lower = webhookUrl.toLowerCase();
        if (!lower.includes('discord.com/api/webhooks/') && !lower.includes('discordapp.com/api/webhooks/')) {
          showFeedback('L\'URL doit provenir de Discord (ex : https://discord.com/api/webhooks/...)', 'error');
          return;
        }
      }

      const origText = testBtn.innerHTML;
      testBtn.disabled = true;
      testBtn.innerHTML = 'Envoi en cours...';

      try {
        const res = await api('/api/discord/test', 'POST', {
          webhook_url: webhookUrl,
          author_name: authorName
        });

        if (res && res.success) {
          showFeedback('✅ Test réussi ! Le message a bien été reçu sur votre salon Discord.', 'success');
          // Mettre à jour l'UI locale
          if (enabledToggle) enabledToggle.checked = true;
          if (badge) {
            badge.textContent = 'Actif (Connecté)';
            badge.className = 'sync-badge shared';
          }
          if (state.settings) {
            state.settings.discord_enabled = '1';
            state.settings.discord_webhook_configured = true;
          }
        } else {
          showFeedback(`❌ Échec de l'envoi : ${res?.message || 'Erreur réseau ou URL invalide'}`, 'error');
        }
      } catch (err) {
        showFeedback(`❌ Erreur technique : ${err.message}`, 'error');
      } finally {
        testBtn.disabled = false;
        testBtn.innerHTML = origText;
      }
    };
  }

  // Enregistrer la configuration
  if (saveBtn) {
    saveBtn.onclick = async () => {
      const enabledToggle = document.getElementById('discord-enabled-toggle');
      const urlInput = document.getElementById('discord-webhook-url');
      const authorInput = document.getElementById('discord-author-name');

      const evtCreated = document.getElementById('discord-evt-created');
      const evtCompleted = document.getElementById('discord-evt-completed');
      const evtDeleted = document.getElementById('discord-evt-deleted');
      const evtFolder = document.getElementById('discord-evt-folder');

      const rawWebhookUrl = (urlInput?.value || '').trim();
      const payload = {
        discord_enabled: enabledToggle?.checked ? '1' : '0',
        discord_author_name: (authorInput?.value || '').trim(),
        discord_notify_created: evtCreated?.checked ? '1' : '0',
        discord_notify_completed: evtCompleted?.checked ? '1' : '0',
        discord_notify_deleted: evtDeleted?.checked ? '1' : '0',
        discord_notify_folder: evtFolder?.checked ? '1' : '0'
      };

      // Si l'utilisateur n'a pas ré-écrit l'URL masquée, ne pas écraser le secret côté serveur
      if (!rawWebhookUrl.startsWith('••••')) {
        let clean = rawWebhookUrl.replace(/['"]/g, '').trim();
        if (clean && !clean.startsWith('http://') && !clean.startsWith('https://')) {
          clean = 'https://' + clean;
        }
        payload.discord_webhook_url = clean;
      }

      const res = await api('/api/settings', 'PUT', payload);
      if (res) {
        state.settings = { ...(state.settings || {}), ...res };
        updateDiscordUIFromState();
        showFeedback('💾 Configuration Discord enregistrée avec succès !', 'success');
        showNotificationDialog({
          title: 'Intégration Discord',
          message: 'Vos réglages Discord ont été enregistrés avec succès. Les membres de votre groupe de projet recevront les notifications sur votre salon Discord.',
          icon: 'check-circle'
        });
      } else {
        showFeedback('❌ Erreur lors de l\'enregistrement des réglages.', 'error');
      }
    };
  }

  function showFeedback(msg, type) {
    if (!feedback) return;
    feedback.textContent = msg;
    feedback.className = `discord-feedback ${type}`;
    feedback.classList.remove('hidden');
    setTimeout(() => {
      feedback.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }

  // Initialiser les valeurs actuelles
  updateDiscordUIFromState();
}

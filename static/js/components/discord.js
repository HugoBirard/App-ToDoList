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
  if (authorInput) authorInput.value = settings.discord_author_name || '';

  // N'écraser urlInput que s'il est vide ou masqué
  if (urlInput) {
    if (!urlInput.value || urlInput.value.startsWith('••••')) {
      urlInput.value = settings.discord_webhook_url || '';
    }
  }

  if (evtCreated) evtCreated.checked = settings.discord_notify_created !== '0';
  if (evtCompleted) evtCompleted.checked = settings.discord_notify_completed !== '0';
  if (evtDeleted) evtDeleted.checked = settings.discord_notify_deleted !== '0';
  if (evtFolder) evtFolder.checked = settings.discord_notify_folder !== '0';

  if (badge) {
    const hasConfiguredUrl = Boolean(settings.discord_webhook_url || settings.discord_webhook_configured);
    if (isEnabled && hasConfiguredUrl) {
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
  const urlInput = document.getElementById('discord-webhook-url');
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
  if (urlInput) {
    urlInput.addEventListener('input', () => {
      const val = urlInput.value.trim();
      if (val && !val.startsWith('••••')) {
        if (enabledToggle) {
          enabledToggle.checked = true;
        }
        if (badge) {
          badge.textContent = 'Prêt à connecter';
          badge.className = 'sync-badge shared';
        }
      }
    });
  }

  // Tester le webhook
  if (testBtn) {
    testBtn.onclick = async () => {
      const authorInput = document.getElementById('discord-author-name');
      let webhookUrl = (urlInput?.value || '').trim().replace(/^["']|["']$/g, '');
      const authorName = (authorInput?.value || '').trim() || 'Équipe';

      const isConfiguredInDb = Boolean(state.settings?.discord_webhook_configured || state.settings?.discord_webhook_url);
      const isMasked = webhookUrl.startsWith('••••');

      if (!webhookUrl && !isConfiguredInDb) {
        showFeedback('Veuillez renseigner une URL de Webhook Discord.', 'error');
        return;
      }

      // Normalisation automatique si l'utilisateur a omis https://
      if (webhookUrl && !isMasked && !webhookUrl.startsWith('http://') && !webhookUrl.startsWith('https://')) {
        webhookUrl = 'https://' + webhookUrl;
        if (urlInput) urlInput.value = webhookUrl;
      }

      if (!isMasked && webhookUrl) {
        const lower = webhookUrl.toLowerCase();
        if (!lower.includes('discord.com/api/webhooks/') && !lower.includes('discordapp.com/api/webhooks/')) {
          showFeedback('L\'URL doit provenir de Discord (ex : https://discord.com/api/webhooks/ID/TOKEN).', 'error');
          return;
        }
      }

      const origText = testBtn.innerHTML;
      testBtn.disabled = true;
      testBtn.innerHTML = `
        <span class="spinner-small" style="display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 6px;"></span>
        Envoi en cours...
      `;

      try {
        const payload = {
          webhook_url: isMasked ? '' : webhookUrl,
          use_saved: isMasked || !webhookUrl,
          author_name: authorName
        };

        const res = await api('/api/discord/test', 'POST', payload);

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
        showFeedback(`❌ Erreur technique : ${err.message || err}`, 'error');
      } finally {
        testBtn.disabled = false;
        testBtn.innerHTML = origText;
      }
    };
  }

  // Enregistrer la configuration
  if (saveBtn) {
    saveBtn.onclick = async () => {
      const authorInput = document.getElementById('discord-author-name');
      const evtCreated = document.getElementById('discord-evt-created');
      const evtCompleted = document.getElementById('discord-evt-completed');
      const evtDeleted = document.getElementById('discord-evt-deleted');
      const evtFolder = document.getElementById('discord-evt-folder');

      let rawWebhookUrl = (urlInput?.value || '').trim().replace(/^["']|["']$/g, '');
      if (rawWebhookUrl.startsWith('discord.com/') || rawWebhookUrl.startsWith('discordapp.com/')) {
        rawWebhookUrl = 'https://' + rawWebhookUrl;
        if (urlInput) urlInput.value = rawWebhookUrl;
      }

      const isMasked = rawWebhookUrl.startsWith('••••');
      const hasUrl = Boolean(rawWebhookUrl) || Boolean(state.settings?.discord_webhook_configured);

      // Si une URL est renseignée mais que la case n'est pas cochée, on active par défaut
      const isEnabled = enabledToggle ? (enabledToggle.checked || (hasUrl && rawWebhookUrl.length > 10)) : true;
      if (enabledToggle) enabledToggle.checked = isEnabled;

      const payload = {
        discord_enabled: isEnabled ? '1' : '0',
        discord_author_name: (authorInput?.value || '').trim() || 'Équipe',
        discord_notify_created: evtCreated?.checked ? '1' : '0',
        discord_notify_completed: evtCompleted?.checked ? '1' : '0',
        discord_notify_deleted: evtDeleted?.checked ? '1' : '0',
        discord_notify_folder: evtFolder?.checked ? '1' : '0'
      };

      // Si l'utilisateur n'a pas ré-écrit l'URL masquée, ne pas écraser le secret côté serveur
      if (!isMasked && rawWebhookUrl) {
        let clean = rawWebhookUrl.replace(/^["']|["']$/g, '').trim();
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
          title: "Intégration Discord",
          message: "Vos réglages Discord ont été enregistrés avec succès. Les membres de votre groupe de projet recevront les notifications sur votre salon Discord.",
          icon: "check"
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
  }
}

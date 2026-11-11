"""
Module d'intégration Discord pour ToDoList.
Gère l'envoi de Rich Embeds via Webhooks Discord (création de tâche, complétion, suppression).
Exécute les requêtes de manière asynchrone pour ne jamais bloquer l'interface.
"""

import json
import logging
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger("todolist.discord")

DISCORD_BLURPLE = 0x5865F2
DISCORD_GREEN = 0x10B981
DISCORD_BLUE = 0x3B82F6
DISCORD_AMBER = 0xF59E0B
DISCORD_RED = 0xEF4444
DISCORD_PURPLE = 0x8B5CF6


def clean_webhook_url(url: str) -> str:
    """Nettoie et normalise une URL de webhook Discord."""
    if not url or not isinstance(url, str):
        return ""
    u = url.strip().strip("'\"").strip()
    if not u.startswith("https://") and not u.startswith("http://"):
        if u.startswith("discord.com") or u.startswith("discordapp.com") or u.startswith("canary.discord.com") or u.startswith("ptb.discord.com"):
            u = "https://" + u
    return u


def is_valid_discord_webhook(url: str) -> bool:
    """Vérifie que l'URL est une URL de Webhook Discord valide et sécurisée (anti-SSRF)."""
    clean_url = clean_webhook_url(url)
    if not clean_url:
        return False
    parsed = urllib.parse.urlparse(clean_url)
    if parsed.scheme != "https":
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"):
        return False
    if not parsed.path.startswith("/api/webhooks/"):
        return False
    # Doit contenir id et token
    parts = [p for p in parsed.path.split("/") if p]
    return len(parts) >= 4 and parts[0] == "api" and parts[1] == "webhooks"


def send_discord_payload(webhook_url: str, payload: dict, async_mode: bool = True) -> tuple[bool, str]:
    """
    Envoie une charge utile JSON vers un webhook Discord.
    Si async_mode est True, l'envoi s'exécute dans un thread détaché.
    """
    clean_url = clean_webhook_url(webhook_url)
    if not is_valid_discord_webhook(clean_url):
        return False, "URL de webhook Discord non valide (ex: https://discord.com/api/webhooks/...)."

    data_bytes = json.dumps(payload).encode("utf-8")

    def _do_send():
        try:
            req = urllib.request.Request(
                clean_url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ToDoList-Sync/2.0 (+https://github.com/HugoBirard/App-ToDoList)"
                },
                method="POST"
            )
            ssl_ctx = ssl.create_default_context()
            try:
                import certifi
                ssl_ctx.load_verify_locations(cafile=certifi.where())
            except Exception:
                pass
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
                status = resp.status
                return status in (200, 204), f"Succès ({status})"
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = str(e)
            logger.warning("Erreur HTTP Discord %d: %s", e.code, err_body)
            if e.code == 404:
                return False, "Erreur 404 : Ce webhook n'existe pas ou a été supprimé sur votre serveur Discord."
            elif e.code == 401:
                return False, "Erreur 401 : Le jeton de ce webhook Discord est invalide."
            elif e.code == 429:
                return False, "Erreur 429 : Trop de requêtes envoyées (Rate Limit). Veuillez réessayer dans un instant."
            return False, f"Erreur HTTP Discord {e.code} : {err_body}"
        except urllib.error.URLError as e:
            logger.warning("Erreur réseau Discord: %s", e)
            return False, f"Impossible de joindre Discord : vérifiez votre connexion internet ({e.reason})"
        except Exception as e:
            logger.warning("Erreur inattendue Discord: %s", e)
            return False, f"Erreur technique : {str(e)}"

    if async_mode:
        t = threading.Thread(target=_do_send, daemon=True)
        t.start()
        return True, "Envoi en cours en arrière-plan"
    else:
        return _do_send()


def _format_embed(title: str, description: str, color: int, fields: list[dict] = None) -> dict:
    """Construit un Rich Embed formaté selon les normes de l'API Discord."""
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {
            "text": "ToDoList • Synchronisation de Projet"
        }
    }
    if fields:
        embed["fields"] = [f for f in fields if f.get("name") and f.get("value")]
    return embed


def send_test_message(webhook_url: str, author_name: str = "Utilisateur ToDoList") -> tuple[bool, str]:
    """Envoie un message de test synchrone pour vérifier la validité de l'intégration."""
    embed = _format_embed(
        title="🎮 ToDoList connectée à Discord !",
        description="Le salon est maintenant configuré pour recevoir en temps réel les mises à jour de votre projet d'équipe.",
        color=DISCORD_BLURPLE,
        fields=[
            {"name": "👤 Configuré par", "value": author_name or "Équipe", "inline": True},
            {"name": "⚡ Statut", "value": "Opérationnel ✅", "inline": True},
            {"name": "📋 Fonctionnalités", "value": "Création, suivi, coches et suppressions synchronisés.", "inline": False}
        ]
    )
    payload = {
        "username": "ToDoList",
        "embeds": [embed]
    }
    return send_discord_payload(webhook_url, payload, async_mode=False)


def notify_task_created(webhook_url: str, task: dict, folder_name: str = "Général", author: str = "Quelqu'un"):
    """Notifie la création d'une nouvelle tâche."""
    priority_map = {
        "urgent": "🔴 Urgente",
        "high": "🟠 Haute",
        "normal": "🟢 Normale",
        "low": "⚪ Basse"
    }
    prio_str = priority_map.get(task.get("priority"), "Normale")

    fields = [
        {"name": "📁 Dossier", "value": folder_name or "Général", "inline": True},
        {"name": "🔥 Priorité", "value": prio_str, "inline": True},
        {"name": "👤 Ajoutée par", "value": author or "Équipe", "inline": True}
    ]

    due_date = task.get("due_date")
    if due_date:
        fields.append({"name": "📅 Échéance", "value": str(due_date), "inline": True})

    embed = _format_embed(
        title="📝 Nouvelle tâche créée",
        description=f"**{task.get('title', 'Sans titre')}**",
        color=DISCORD_BLUE,
        fields=fields
    )
    send_discord_payload(webhook_url, {"username": "ToDoList", "embeds": [embed]})


def notify_task_status_changed(webhook_url: str, task: dict, folder_name: str = "Général", author: str = "Quelqu'un"):
    """Notifie lorsqu'une tâche est terminée ou réouverte."""
    completed = bool(task.get("completed"))
    if completed:
        title = "✅ Tâche terminée !"
        desc = f"~~{task.get('title', 'Sans titre')}~~"
        color = DISCORD_GREEN
        action_label = "Terminée par"
    else:
        title = "🔄 Tâche réouverte"
        desc = f"**{task.get('title', 'Sans titre')}**"
        color = DISCORD_AMBER
        action_label = "Réouverte par"

    fields = [
        {"name": "📁 Dossier", "value": folder_name or "Général", "inline": True},
        {"name": f"👤 {action_label}", "value": author or "Équipe", "inline": True}
    ]

    embed = _format_embed(
        title=title,
        description=desc,
        color=color,
        fields=fields
    )
    send_discord_payload(webhook_url, {"username": "ToDoList", "embeds": [embed]})


def notify_task_deleted(webhook_url: str, task_title: str, folder_name: str = "Général", author: str = "Quelqu'un"):
    """Notifie la suppression d'une tâche."""
    embed = _format_embed(
        title="🗑️ Tâche supprimée",
        description=f"~~{task_title}~~",
        color=DISCORD_RED,
        fields=[
            {"name": "📁 Dossier", "value": folder_name or "Général", "inline": True},
            {"name": "👤 Supprimée par", "value": author or "Équipe", "inline": True}
        ]
    )
    send_discord_payload(webhook_url, {"username": "ToDoList", "embeds": [embed]})


def notify_folder_created(webhook_url: str, folder_name: str, author: str = "Quelqu'un"):
    """Notifie la création d'un nouveau dossier de projet."""
    embed = _format_embed(
        title="📁 Nouveau dossier de projet",
        description=f"Le dossier **{folder_name}** a été créé.",
        color=DISCORD_PURPLE,
        fields=[
            {"name": "👤 Créé par", "value": author or "Équipe", "inline": True}
        ]
    )
    send_discord_payload(webhook_url, {"username": "ToDoList", "embeds": [embed]})

"""
Module de détection et d'application des mises à jour pour ToDoList.
Permet la vérification en arrière-plan et la mise à jour en 1 clic
avec sauvegarde automatique préventive de la base de données.
"""

import logging
import os
import shutil
import subprocess
from .config import BASE_DIR, DEFAULT_DB_PATH

logger = logging.getLogger("todolist.updater")


def check_for_updates(timeout=5):
    """
    Vérifie si une mise à jour est disponible sur le dépôt Git distant.
    Opération rapide, non bloquante et sécurisée.
    """
    git_dir = os.path.join(BASE_DIR, ".git")
    if not os.path.isdir(git_dir):
        return {
            "is_git": False,
            "update_available": False,
            "message": "Installation autonome (hors Git)"
        }

    try:
        # Commit local actuel
        res_head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=2
        )
        current_commit = res_head.stdout.strip() if res_head.returncode == 0 else "inconnu"

        # Branche locale actuelle
        res_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=2
        )
        branch = res_branch.stdout.strip() if res_branch.returncode == 0 else "main"

        # Upstream associé ou référence par défaut
        res_upstream = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{u}"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=2
        )
        target_ref = res_upstream.stdout.strip() if res_upstream.returncode == 0 and res_upstream.stdout.strip() else f"origin/{branch}"

        # Fetch distant silencieux avec timeout strict
        try:
            subprocess.run(
                ["git", "fetch", "-q"],
                cwd=BASE_DIR, capture_output=True, timeout=timeout
            )
        except Exception:
            return {
                "is_git": True,
                "update_available": False,
                "current_commit": current_commit,
                "branch": branch,
                "offline": True,
                "message": "Vérification en ligne indisponible (hors ligne)"
            }

        # Nombre de commits de retard par rapport à l'upstream
        res_count = subprocess.run(
            ["git", "rev-list", f"HEAD..{target_ref}", "--count"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=3
        )
        behind_count = 0
        if res_count.returncode == 0:
            try:
                behind_count = int(res_count.stdout.strip())
            except ValueError:
                behind_count = 0

        if behind_count > 0:
            # Récupérer les messages des derniers commits pour informer l'utilisateur
            res_log = subprocess.run(
                ["git", "log", "-n", "5", "--pretty=format:%h|%s", f"HEAD..{target_ref}"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=3
            )
            commits = []
            if res_log.returncode == 0 and res_log.stdout.strip():
                for line in res_log.stdout.strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|", 1)
                        commits.append({"hash": parts[0], "message": parts[1]})

            # Récupérer le hash du dernier commit distant
            res_target_hash = subprocess.run(
                ["git", "rev-parse", "--short", target_ref],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=2
            )
            target_hash = res_target_hash.stdout.strip() if res_target_hash.returncode == 0 else ""

            return {
                "is_git": True,
                "update_available": True,
                "behind_count": behind_count,
                "current_commit": current_commit,
                "target_commit": target_hash,
                "branch": branch,
                "target_ref": target_ref,
                "commits": commits,
                "message": f"{behind_count} nouvelle(s) mise(s) à jour disponible(s) !"
            }

        return {
            "is_git": True,
            "update_available": False,
            "behind_count": 0,
            "current_commit": current_commit,
            "branch": branch,
            "message": "Votre application ToDoList est à jour."
        }

    except Exception as e:
        logger.warning("Erreur lors de la vérification des mises à jour: %s", e)
        return {
            "is_git": True,
            "update_available": False,
            "error": str(e),
            "message": "Impossible de vérifier les mises à jour pour le moment."
        }


def apply_update(db_path=None):
    """
    Applique la mise à jour en toute sécurité :
    1. Sauvegarde automatique préventive de la base de données SQLite.
    2. Exécution de git pull.
    3. Actualisation des raccourcis et icônes système.
    4. Retour d'état avec nouveau hash de commit.
    """
    git_dir = os.path.join(BASE_DIR, ".git")
    if not os.path.isdir(git_dir):
        return {
            "success": False,
            "error": "L'application ne s'exécute pas depuis un dépôt Git. Mise à jour automatique indisponible."
        }

    # 1. Sauvegarde préventive de la base de données
    active_db = db_path or DEFAULT_DB_PATH
    backup_file = None
    if os.path.exists(active_db):
        try:
            backup_file = f"{active_db}.pre-update.bak"
            shutil.copy2(active_db, backup_file)
            logger.info("Copie de sauvegarde préventive créée : %s", backup_file)
        except Exception as e:
            logger.warning("Impossible de créer la copie de sauvegarde : %s", e)

    # 2. Gestion propre des modifications de code locales si existantes
    had_stash = False
    try:
        res_status = subprocess.run(
            ["git", "status", "--porcelain", "-uno"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=5
        )
        if res_status.returncode == 0 and res_status.stdout.strip():
            logger.info("Mise en réserve (stash) des modifications locales temporaires")
            res_stash = subprocess.run(["git", "stash"], cwd=BASE_DIR, capture_output=True, timeout=5)
            had_stash = (res_stash.returncode == 0)

        # 3. Récupération des nouveautés (git pull)
        res_pull = subprocess.run(
            ["git", "pull"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=30
        )
        if res_pull.returncode != 0:
            if had_stash:
                subprocess.run(["git", "stash", "pop"], cwd=BASE_DIR, capture_output=True, timeout=5)
            err_msg = res_pull.stderr.strip() or res_pull.stdout.strip()
            return {
                "success": False,
                "error": f"Erreur lors du git pull : {err_msg}"
            }

        # Restauration du stash éventuel
        if had_stash:
            subprocess.run(["git", "stash", "pop"], cwd=BASE_DIR, capture_output=True, timeout=5)

        # 4. Actualisation des raccourcis et icônes
        raccourci_script = os.path.join(BASE_DIR, "installer-raccourci.sh")
        if os.path.exists(raccourci_script):
            try:
                subprocess.run(["bash", raccourci_script], cwd=BASE_DIR, capture_output=True, timeout=10)
            except Exception as e:
                logger.debug("Rafraîchissement raccourci non bloquant: %s", e)

        # 5. Récupération du nouveau commit
        res_new_head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=3
        )
        new_commit = res_new_head.stdout.strip() if res_new_head.returncode == 0 else ""

        return {
            "success": True,
            "message": "Application mise à jour avec succès !",
            "new_commit": new_commit,
            "backup_created": bool(backup_file and os.path.exists(backup_file)),
            "backup_path": backup_file
        }

    except Exception as e:
        logger.error("Exception lors de l'application de la mise à jour: %s", e)
        return {
            "success": False,
            "error": f"Erreur imprévue : {str(e)}"
        }

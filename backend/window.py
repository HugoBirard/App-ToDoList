"""
Gestionnaire d'affichage de la fenêtre autonome dédiée (style Spotify/Electron).
Garantit l'ouverture dans une vraie fenêtre d'application et JAMAIS dans un onglet navigateur.
"""

import os
import sys
import time
import shutil
import subprocess
from .config import BASE_DIR, DATA_DIR, ICON_PNG, APP_NAME

LOG_PATH = os.path.join(DATA_DIR, "app.log")


def log(message):
    """Écrit un log horodaté dans data/app.log pour le diagnostic."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


def install_desktop_shortcuts():
    """Installe le lanceur .desktop et les icônes dans le système."""
    # 0. Installer les icônes dans le thème d'icônes XDG (~/.local/share/icons/hicolor)
    try:
        icon_svg = os.path.join(STATIC_DIR, "assets", "icon.svg")
        for theme in ["hicolor", "NC"]:
            for res in ["256x256", "128x128", "48x48"]:
                dir_path = os.path.expanduser(f"~/.local/share/icons/{theme}/{res}/apps")
                os.makedirs(dir_path, exist_ok=True)
                if os.path.exists(ICON_PNG):
                    shutil.copy2(ICON_PNG, os.path.join(dir_path, "todolist.png"))
            scalable_dir = os.path.expanduser(f"~/.local/share/icons/{theme}/scalable/apps")
            os.makedirs(scalable_dir, exist_ok=True)
            if os.path.exists(icon_svg):
                shutil.copy2(icon_svg, os.path.join(scalable_dir, "todolist.svg"))
            subprocess.run(["gtk-update-icon-cache", "-f", os.path.expanduser(f"~/.local/share/icons/{theme}")], capture_output=True)
    except Exception as e:
        log(f"Erreur installation icônes système: {e}")

    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
GenericName=Gestionnaire de tâches
Comment=Gestionnaire de To-Do List local et persistant avec dossiers
Exec={os.path.join(BASE_DIR, 'start.sh')}
Icon={ICON_PNG}
Path={BASE_DIR}
Terminal=false
Categories=Office;Utility;ProjectManagement;
StartupNotify=false
Keywords=todo;todolist;taches;organisation;
"""

    # 1. Menu système des applications GNOME (~/.local/share/applications)
    local_apps = os.path.expanduser("~/.local/share/applications")
    try:
        os.makedirs(local_apps, exist_ok=True)
        target = os.path.join(local_apps, "todolist.desktop")
        with open(target, "w", encoding="utf-8") as f:
            f.write(desktop_content)
        os.chmod(target, 0o755)

        # Nettoyer l'ancien doublon ToDoList.desktop pour n'avoir qu'un seul lanceur
        duplicate = os.path.join(local_apps, "ToDoList.desktop")
        if os.path.exists(duplicate):
            try:
                os.remove(duplicate)
            except Exception:
                pass

        subprocess.run(["gio", "set", target, "metadata::trusted", "true"], capture_output=True)
        subprocess.run(["update-desktop-database", local_apps], capture_output=True)
        log("Raccourci unique installé dans ~/.local/share/applications/todolist.desktop")
    except Exception as e:
        log(f"Erreur installation raccourci local: {e}")

    # Mettre également à jour le fichier .desktop local dans le dossier du projet
    try:
        local_desktop = os.path.join(BASE_DIR, "ToDoList.desktop")
        with open(local_desktop, "w", encoding="utf-8") as f:
            f.write(desktop_content)
        os.chmod(local_desktop, 0o755)
        subprocess.run(["gio", "set", local_desktop, "metadata::trusted", "true"], capture_output=True)
    except Exception:
        pass

    # 2. Bureau si un dossier Desktop ou Bureau existe
    for folder in ["Desktop", "Bureau"]:
        desk_dir = os.path.expanduser(f"~/{folder}")
        if os.path.isdir(desk_dir):
            try:
                dest = os.path.join(desk_dir, "ToDoList.desktop")
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(desktop_content)
                os.chmod(dest, 0o755)
                subprocess.run(["gio", "set", dest, "metadata::trusted", "true"], capture_output=True)
                log(f"Raccourci installé sur {dest}")
            except Exception as e:
                log(f"Erreur installation bureau {folder}: {e}")


def open_gtk4_window(url):
    """
    PRIORITÉ 1 : Fenêtre native GTK4 + WebKit6 (isolée en sous-processus).
    Style Spotify / Electron : fenêtre autonome sans barre d'adresse ni onglets.
    """
    try:
        log("Tentative de lancement fenêtre native GTK4 + WebKit6...")
        proc = subprocess.Popen([
            sys.executable,
            "-m",
            "backend.window_gtk4",
            url
        ])
        time.sleep(0.6)
        if proc.poll() is not None and proc.returncode != 0:
            log(f"Échec GTK4 (code de sortie {proc.returncode})")
            return False

        log("Fenêtre native GTK4 active.")
        proc.wait()
        log(f"Fenêtre GTK4 fermée par l'utilisateur (code {proc.returncode})")
        return True
    except Exception as e:
        log(f"Exception GTK4: {e}")
        return False


def open_epiphany_app(url):
    """
    PRIORITÉ 2 : Fenêtre native GNOME Web (Epiphany) en mode application dédiée.
    Le moteur officiel GNOME pour exécuter des Web Apps sous forme de vraies fenêtres d'application.
    Absolument AUCUNE barre d'adresse, AUCUN onglet, intégration 100% Wayland/GTK.
    """
    bin_path = shutil.which("epiphany")
    if not bin_path:
        return False

    profile_dir = os.path.join(DATA_DIR, "epiphany_profile")
    os.makedirs(profile_dir, exist_ok=True)

    log(f"Lancement de GNOME Web (Epiphany) en mode application autonome...")
    try:
        proc = subprocess.Popen([
            bin_path,
            f"--profile={profile_dir}",
            "--application-mode",
            url
        ])
        time.sleep(0.6)
        if proc.poll() is not None and proc.returncode != 0:
            log(f"Échec Epiphany (code {proc.returncode})")
            return False

        log("Fenêtre d'application GNOME active.")
        proc.wait()
        log(f"Fenêtre d'application GNOME fermée (code {proc.returncode})")
        return True
    except Exception as e:
        log(f"Exception Epiphany: {e}")
        return False


def open_chromium_app(url):
    """
    PRIORITÉ 3 : Mode Application autonome (--app=URL) si Chrome, Chromium ou Brave est présent.
    Même moteur Chromium que Spotify et VS Code.
    """
    browsers = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser"]
    for bin_name in browsers:
        bin_path = shutil.which(bin_name)
        if bin_path:
            log(f"Tentative de lancement {bin_name} en mode application (--app={url})...")
            try:
                proc = subprocess.Popen([bin_path, f"--app={url}"])
                time.sleep(0.6)
                if proc.poll() is not None and proc.returncode != 0:
                    continue
                log(f"Fenêtre {bin_name} active.")
                proc.wait()
                log(f"Fenêtre {bin_name} fermée (code {proc.returncode})")
                return True
            except Exception as e:
                log(f"Erreur {bin_name}: {e}")
    return False


def open_gtk3_window(url):
    """
    PRIORITÉ 4 : Fenêtre native GTK3 + WebKit2 si GTK4 n'a pas pu être utilisé.
    """
    try:
        log("Tentative de lancement fenêtre native GTK3 + WebKit2...")
        proc = subprocess.Popen([
            sys.executable,
            "-m",
            "backend.window_gtk3",
            url
        ])
        time.sleep(0.6)
        if proc.poll() is not None and proc.returncode != 0:
            log(f"Échec GTK3 (code {proc.returncode})")
            return False

        proc.wait()
        return True
    except Exception as e:
        log(f"Exception GTK3: {e}")
        return False


def launch_app_window(url):
    """
    Orchestre l'ouverture stricte dans une VRAIE FENÊTRE D'APPLICATION DÉDIÉE (style Spotify/VS Code).
    Ne lance jamais un navigateur avec onglets ou barre d'adresse.
    """
    log(f"Démarrage de la fenêtre autonome dédiée pour l'URL : {url}")

    # 1. Fenêtre native GTK4 / WebKit6 (application de bureau pure)
    if open_gtk4_window(url):
        return

    # 2. Fenêtre native GNOME Web en mode application (officiel GNOME, style Spotify)
    if open_epiphany_app(url):
        return

    # 3. Chrome / Chromium en mode App autonome (--app=URL)
    if open_chromium_app(url):
        return

    # 4. Fenêtre native GTK3 / WebKit2
    if open_gtk3_window(url):
        return

    # Si aucun moteur d'application fenêtré n'est trouvé
    msg = (
        "Erreur: Aucun moteur d'application fenêtré autonome (GTK4, Epiphany --application-mode, ou Chromium --app) "
        "n'a pu être démarré pour afficher l'application."
    )
    log(msg)
    print(msg, file=sys.stderr)

"""
Lanceur autonome de fenêtre native GTK4 + WebKit6 dans un processus dédié.
Garantit une isolation totale : un crash C-level de WebKit ne tue pas le serveur principal.
"""

import sys
import os

APP_NAME = "ToDo List"


def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    url = sys.argv[1]

    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("WebKit", "6.0")
        from gi.repository import GLib, Gtk, Gdk, WebKit, Gio

        # Définit le nom exact de l'application pour Wayland et GNOME Shell (associe todolist.desktop)
        GLib.set_prgname("todolist")
        GLib.set_application_name(APP_NAME)

        app = Gtk.Application(
            application_id=None,
            flags=Gio.ApplicationFlags.NON_UNIQUE
        )

        window_created = [False]

        def on_activate(application):
            try:
                win = Gtk.ApplicationWindow(application=application)
                win.set_title(APP_NAME)
                win.set_default_size(1280, 850)
                win.maximize()  # Plein écran par défaut, avec bouton pour réduire à volonté

                # Configurer l'icône de l'application pour GTK / GNOME
                assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "assets"))
                display = Gdk.Display.get_default()
                if display:
                    icon_theme = Gtk.IconTheme.get_for_display(display)
                    if os.path.exists(assets_dir):
                        icon_theme.add_search_path(assets_dir)
                win.set_icon_name("todolist")

                # Utiliser une session réseau éphémère pour garantir l'absence totale de cache disque obsolète
                if hasattr(WebKit, "NetworkSession") and hasattr(WebKit.NetworkSession, "new_ephemeral"):
                    session = WebKit.NetworkSession.new_ephemeral()
                    webview = WebKit.WebView(network_session=session)
                else:
                    webview = WebKit.WebView()

                # Supprimer tout flash blanc natif du WebView en forçant le fond noir dès le départ
                bg_color = Gdk.RGBA()
                bg_color.parse("#08090c")
                webview.set_background_color(bg_color)

                settings = webview.get_settings()
                if settings:
                    settings.set_enable_developer_extras(False)
                    if hasattr(settings, "set_enable_page_cache"):
                        settings.set_enable_page_cache(False)
                    if hasattr(settings, "set_enable_offline_web_application_cache"):
                        settings.set_enable_offline_web_application_cache(False)

                webview.set_hexpand(True)
                webview.set_vexpand(True)

                # Raccourci F11 pour basculer en mode plein écran absolu si souhaité
                key_controller = Gtk.EventControllerKey()
                def on_key_pressed(controller, keyval, keycode, state):
                    if keyval == Gdk.KEY_F11:
                        if win.is_fullscreen():
                            win.unfullscreen()
                        else:
                            win.fullscreen()
                        return True
                    return False
                key_controller.connect("key-pressed", on_key_pressed)
                win.add_controller(key_controller)

                # Forcer le rechargement frais avec timestamp
                import time
                sep = "&" if "?" in url else "?"
                fresh_url = f"{url}{sep}v={int(time.time())}"
                webview.load_uri(fresh_url)

                win.set_child(webview)
                win.present()
                window_created[0] = True
            except Exception as err:
                sys.stderr.write(f"Erreur GTK4 on_activate: {err}\n")
                application.quit()

        app.connect("activate", on_activate)
        ret = app.run([sys.argv[0]])
        sys.exit(0 if window_created[0] else 1)
    except Exception as e:
        sys.stderr.write(f"Échec initialisation GTK4: {e}\n")
        sys.exit(2)


if __name__ == "__main__":
    main()

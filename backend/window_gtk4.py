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
        from gi.repository import Gtk, WebKit, Gio

        app = Gtk.Application(
            application_id=None,
            flags=Gio.ApplicationFlags.NON_UNIQUE
        )

        window_created = [False]

        def on_activate(application):
            try:
                win = Gtk.ApplicationWindow(application=application)
                win.set_title(APP_NAME)
                win.set_default_size(1180, 800)

                # Utiliser une session réseau éphémère pour garantir l'absence totale de cache disque obsolète
                if hasattr(WebKit, "NetworkSession") and hasattr(WebKit.NetworkSession, "new_ephemeral"):
                    session = WebKit.NetworkSession.new_ephemeral()
                    webview = WebKit.WebView(network_session=session)
                else:
                    webview = WebKit.WebView()

                settings = webview.get_settings()
                if settings:
                    settings.set_enable_developer_extras(False)
                    if hasattr(settings, "set_enable_page_cache"):
                        settings.set_enable_page_cache(False)
                    if hasattr(settings, "set_enable_offline_web_application_cache"):
                        settings.set_enable_offline_web_application_cache(False)

                webview.set_hexpand(True)
                webview.set_vexpand(True)

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

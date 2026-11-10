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

                webview = WebKit.WebView()
                settings = webview.get_settings()
                if settings:
                    settings.set_enable_developer_extras(False)

                webview.set_hexpand(True)
                webview.set_vexpand(True)
                webview.load_uri(url)

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

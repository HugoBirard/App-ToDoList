"""
Lanceur autonome de fenêtre native GTK3 + WebKit2 dans un processus dédié.
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
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gtk, WebKit2

        ok, _ = Gtk.init_check([])
        if not ok:
            sys.exit(1)

        win = Gtk.Window(title=APP_NAME)
        win.set_default_size(1180, 800)
        win.set_position(Gtk.WindowPosition.CENTER)

        webview = WebKit2.WebView()
        settings = webview.get_settings()
        if settings:
            settings.set_enable_developer_extras(False)

        webview.load_uri(url)
        win.add(webview)
        win.connect("destroy", Gtk.main_quit)
        win.show_all()
        Gtk.main()
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Échec GTK3: {e}\n")
        sys.exit(2)


if __name__ == "__main__":
    main()

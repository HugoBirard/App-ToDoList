"""
Lanceur autonome de fenêtre native GTK3 + WebKit2 dans un processus dédié (fallback).
"""

import sys
import os
import sqlite3

APP_NAME = "ToDoList"


def read_db_setting(key, default=None):
    try:
        from backend.config import get_current_db_path
        db_path = get_current_db_path()
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path, timeout=2.0)
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
    except Exception:
        pass
    return default


def parse_titlebar_arg(args):
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--titlebar="):
            return arg.split("=", 1)[1].strip().lower()
        if arg == "--titlebar" and i + 1 < len(args):
            return args[i + 1].strip().lower()
        i += 1
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    url = sys.argv[1]

    cli_style = parse_titlebar_arg(sys.argv[1:])
    env_style = os.environ.get("TODOLIST_TITLEBAR")
    db_style = read_db_setting("titlebar_style")
    active_style = cli_style or env_style or db_style or "transparent"

    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gtk, Gdk, WebKit2

        ok, _ = Gtk.init_check([])
        if not ok:
            sys.exit(1)

        win = Gtk.Window(title=APP_NAME)
        win.set_default_size(1280, 850)
        win.set_position(Gtk.WindowPosition.CENTER)
        win.maximize()

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.set_title(APP_NAME)
        win.set_titlebar(hb)

        # Style CSS GTK3
        css = b"""
            window,
            decoration {
                background-color: #08090c;
                background-image: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar {
                background: #08090c;
                background-color: #08090c;
                background-image: none;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                margin: 0;
                padding: 0 8px;
                border-radius: 0;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
            headerbar .title {
                color: #ffffff;
                font-weight: bold;
            }
        """
        if active_style == "transparent":
            css = b"""
                window,
                decoration {
                    background-color: #08090c;
                    background-image: none;
                    margin: 0;
                    padding: 0;
                    border-radius: 0;
                }
                headerbar {
                    background: transparent;
                    background-color: transparent;
                    background-image: none;
                    border: none;
                    box-shadow: none;
                    margin: 0;
                    padding: 0 8px;
                    border-radius: 0;
                    border-top-left-radius: 0;
                    border-top-right-radius: 0;
                }
            """
        elif active_style == "glass":
            css = b"""
                window,
                decoration {
                    background-color: #08090c;
                    background-image: none;
                    margin: 0;
                    padding: 0;
                    border-radius: 0;
                }
                headerbar {
                    background: #111827;
                    background-color: #111827;
                    background-image: none;
                    border: none;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.14);
                    margin: 0;
                    padding: 0 8px;
                    border-radius: 0;
                    border-top-left-radius: 0;
                    border-top-right-radius: 0;
                }
            """
        elif active_style == "neon":
            css = b"""
                window,
                decoration {
                    background-color: #08090c;
                    background-image: none;
                    margin: 0;
                    padding: 0;
                    border-radius: 0;
                }
                headerbar {
                    background: #090a12;
                    background-color: #090a12;
                    background-image: none;
                    border: none;
                    border-bottom: 2px solid #6366f1;
                    box-shadow: 0 3px 16px rgba(99, 102, 241, 0.38);
                    margin: 0;
                    padding: 0 8px;
                    border-radius: 0;
                    border-top-left-radius: 0;
                    border-top-right-radius: 0;
                }
            """

        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

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

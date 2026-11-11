"""
Tests unitaires pour la personnalisation de la barre de titre système (HeaderBar GTK).
Vérifie la génération CSS, le parsing des arguments CLI et la compatibilité GTK.
"""

import unittest
from backend.window_gtk4 import (
    TITLEBAR_STYLES,
    parse_titlebar_arg,
    generate_css,
    extract_primary_hex_color,
    apply_css_to_provider
)


class TestTitlebarCustomization(unittest.TestCase):
    def test_all_styles_defined(self):
        """Vérifie que les 13 styles (6 essentiels + 7 subcultures/artistiques) sont définis."""
        expected_styles = [
            "transparent", "match-bg", "glass", "neon", "minimal", "classic",
            "street", "techno", "cyberpunk", "y2k", "arcade", "luxury", "zen"
        ]
        for style in expected_styles:
            self.assertIn(style, TITLEBAR_STYLES)
            self.assertIn("name", TITLEBAR_STYLES[style])
            self.assertIn("description", TITLEBAR_STYLES[style])
            self.assertIn("css", TITLEBAR_STYLES[style])

    def test_parse_titlebar_arg_variations(self):
        """Vérifie le parsing des arguments en ligne de commande."""
        self.assertEqual(parse_titlebar_arg(["http://localhost", "--titlebar", "glass"]), "glass")
        self.assertEqual(parse_titlebar_arg(["http://localhost", "--titlebar=neon"]), "neon")
        self.assertEqual(parse_titlebar_arg(["http://localhost", "--titlebar", "TRANSPARENT"]), "transparent")
        self.assertIsNone(parse_titlebar_arg(["http://localhost", "--other-flag"]))
        self.assertIsNone(parse_titlebar_arg([]))

    def test_extract_primary_hex_color(self):
        """Vérifie l'extraction de la couleur hexadécimale pour match-bg."""
        self.assertEqual(extract_primary_hex_color("#0f172a"), "#0f172a")
        self.assertEqual(extract_primary_hex_color("linear-gradient(135deg, #1e1b4b 0%, #090a0d 100%)"), "#1e1b4b")
        self.assertEqual(extract_primary_hex_color(""), "#08090c")
        self.assertEqual(extract_primary_hex_color(None), "#08090c")

    def test_generate_css(self):
        """Vérifie la génération de CSS pour les différents styles."""
        css_trans = generate_css("transparent")
        self.assertIn("background: transparent;", css_trans)

        css_glass = generate_css("glass")
        self.assertIn("linear-gradient", css_glass)

        css_neon = generate_css("neon")
        self.assertIn("#6366f1", css_neon)

        css_minimal = generate_css("minimal")
        self.assertIn("min-height: 28px;", css_minimal)

        # match-bg avec couleur personnalisée
        css_match = generate_css("match-bg", "#123456")
        self.assertIn("#123456", css_match)

    def test_gtk4_css_parsing(self):
        """Vérifie que GTK4 est capable de parser sans erreur chaque CSS généré."""
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
        except (ImportError, ValueError, Exception) as e:
            raise unittest.SkipTest(f"GTK4 / PyGObject non disponible dans cet environnement: {e}")

        try:
            provider = Gtk.CssProvider()
            for style in TITLEBAR_STYLES:
                css = generate_css(style, "#090a0d")
                apply_css_to_provider(provider, css)
        except Exception as e:
            self.fail(f"Erreur de chargement GTK4 CSS: {e}")


if __name__ == "__main__":
    unittest.main()

"""
Lanceur autonome de fenêtre native GTK4 + WebKit6 dans un processus dédié.
Garantit une isolation totale : un crash C-level de WebKit ne tue pas le serveur principal.
Prend en charge la personnalisation complète de la barre de titre système (HeaderBar / CSD) :
- transparent : Fond transparent et intégré, style Spotify / Discord / VS Code
- match-bg    : Même couleur sombre que le fond actif de l'application
- glass       : Verre fumé translucide avec reflet métallique et ombre portée (Glassmorphism)
- neon        : Liseré lumineux cyber indigo électrique avec halo néon
- minimal     : Barre ultra-fine et discrète (28px), sans titre, pour un espace maximal
- classic     : Style système standard GNOME Adwaita par défaut
"""

import sys
import os
import json
import sqlite3

APP_NAME = "ToDoList"

TITLEBAR_STYLES = {
    "transparent": {
        "name": "Transparente (Seamless)",
        "description": "Fond transparent et intégré sans rupture, style Spotify / Discord / VS Code",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #08090c;
                background-color: #08090c;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: transparent;
                background-color: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                min-height: 40px;
                padding: 0 8px;
                margin: 0;
                border-radius: 0;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
            headerbar windowhandle,
            headerbar windowhandle:backdrop,
            headerbar windowcontrols,
            headerbar windowcontrols.start,
            headerbar windowcontrols.end,
            headerbar windowcontrols:backdrop,
            .todolist-headerbar windowhandle,
            .todolist-headerbar windowcontrols {
                background: transparent;
                background-color: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar .app-title-box {
                opacity: 1;
            }
            headerbar .app-title {
                color: rgba(255, 255, 255, 0.90);
                font-weight: 600;
                font-size: 13px;
                letter-spacing: 0.3px;
            }
            headerbar button,
            headerbar windowcontrols button {
                background: transparent;
                background-color: transparent;
                background-image: none;
                color: rgba(255, 255, 255, 0.7);
                border: none;
                box-shadow: none;
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                padding: 3px 6px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                color: #ffffff;
            }
        """
    },
    "match-bg": {
        "name": "Même couleur que le fond",
        "description": "Harmonie monolithique avec votre thème sombre et fine ligne de démarcation",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #08090c;
                background-color: #08090c;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: #08090c;
                background-color: #08090c;
                background-image: none;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: none;
                min-height: 40px;
                padding: 0 8px;
                margin: 0;
                border-radius: 0;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
            headerbar windowhandle,
            headerbar windowhandle:backdrop,
            headerbar windowcontrols,
            headerbar windowcontrols.start,
            headerbar windowcontrols.end,
            headerbar windowcontrols:backdrop,
            .todolist-headerbar windowhandle,
            .todolist-headerbar windowcontrols {
                background: transparent;
                background-color: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar .app-title-box {
                opacity: 1;
            }
            headerbar .app-title {
                color: #f1f5f9;
                font-weight: 600;
                font-size: 13px;
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(255, 255, 255, 0.05);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                padding: 3px 6px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: rgba(255, 255, 255, 0.14);
                color: #ffffff;
                border-color: rgba(255, 255, 255, 0.16);
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                border-color: #ef4444;
                color: #ffffff;
            }
        """
    },
    "glass": {
        "name": "Verre Fumé Glassmorphism",
        "description": "Effet translucide avec reflet métallique supérieur et ombre portée",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #08090c;
                background-color: #08090c;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: linear-gradient(180deg, rgba(26, 31, 48, 0.95) 0%, rgba(12, 16, 28, 0.95) 100%);
                background-color: #0c101c;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.14);
                box-shadow: 0 4px 18px rgba(0, 0, 0, 0.5);
                min-height: 42px;
                padding: 0 8px;
                margin: 0;
                border-radius: 0;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
            headerbar windowhandle,
            headerbar windowhandle:backdrop,
            headerbar windowcontrols,
            headerbar windowcontrols.start,
            headerbar windowcontrols.end,
            headerbar windowcontrols:backdrop,
            .todolist-headerbar windowhandle,
            .todolist-headerbar windowcontrols {
                background: transparent;
                background-color: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar .app-title-box {
                opacity: 1;
            }
            headerbar .app-title {
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 0.4px;
                text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7);
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(255, 255, 255, 0.07);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                padding: 3px 6px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.28);
                color: #ffffff;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                border-color: #f87171;
                color: #ffffff;
            }
        """
    },
    "neon": {
        "name": "Liseré Cyber Indigo",
        "description": "Bordure inférieure indigo électrique avec halo lumineux vibrant",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #08090c;
                background-color: #08090c;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: #090a12;
                background-color: #090a12;
                background-image: none;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 2px solid #6366f1;
                box-shadow: 0 3px 16px rgba(99, 102, 241, 0.38);
                min-height: 40px;
                padding: 0 8px;
                margin: 0;
                border-radius: 0;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
            headerbar windowhandle,
            headerbar windowhandle:backdrop,
            headerbar windowcontrols,
            headerbar windowcontrols.start,
            headerbar windowcontrols.end,
            headerbar windowcontrols:backdrop,
            .todolist-headerbar windowhandle,
            .todolist-headerbar windowcontrols {
                background: transparent;
                background-color: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar .app-title-box {
                opacity: 1;
            }
            headerbar .app-title {
                color: #a5b4fc;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 0.8px;
                text-shadow: 0 0 8px rgba(99, 102, 241, 0.5);
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(99, 102, 241, 0.12);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                padding: 3px 6px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: rgba(99, 102, 241, 0.35);
                border-color: #818cf8;
                color: #ffffff;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                border-color: #ef4444;
                color: #ffffff;
            }
        """
    },
    "minimal": {
        "name": "Minimaliste Compacte",
        "description": "Hauteur réduite de 28px, sans titre, boutons discrets pour maximiser l'écran",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #08090c;
                background-color: #08090c;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: transparent;
                background-color: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                min-height: 28px;
                padding: 0 4px;
                margin: 0;
                border-radius: 0;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
            headerbar windowhandle,
            headerbar windowhandle:backdrop,
            headerbar windowcontrols,
            headerbar windowcontrols.start,
            headerbar windowcontrols.end,
            headerbar windowcontrols:backdrop,
            .todolist-headerbar windowhandle,
            .todolist-headerbar windowcontrols {
                background: transparent;
                background-color: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar .app-title-box {
                opacity: 0;
            }
            headerbar button,
            headerbar windowcontrols button {
                background: transparent;
                background-color: transparent;
                background-image: none;
                color: rgba(255, 255, 255, 0.45);
                border: none;
                box-shadow: none;
                min-width: 22px;
                min-height: 22px;
                padding: 1px 3px;
                margin: 1px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                color: #ffffff;
            }
        """
    },
    "classic": {
        "name": "Système GNOME Standard",
        "description": "Thème Adwaita standard de votre environnement de bureau",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #08090c;
                background-color: #08090c;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                margin: 0;
                border-radius: 0;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
        """
    },
    "street": {
        "name": "Streetwear Acid Volt",
        "description": "Asphalte brut texturé avec liseré jaune volt fluo électrique (#ccff00)",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #101114;
                background-color: #101114;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: #121318;
                background-color: #121318;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 2px solid #ccff00;
                box-shadow: 0 3px 18px rgba(204, 255, 0, 0.35);
                min-height: 42px;
                padding: 0 8px;
                margin: 0;
            }
            headerbar windowhandle,
            headerbar windowcontrols {
                background: transparent;
                border: none;
                box-shadow: none;
            }
            headerbar .app-title {
                color: #ccff00;
                font-weight: 800;
                font-size: 13px;
                letter-spacing: 1.2px;
                text-shadow: 0 0 10px rgba(204, 255, 0, 0.4);
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(204, 255, 0, 0.08);
                color: #ccff00;
                border: 1px solid rgba(204, 255, 0, 0.25);
                border-radius: 4px;
                min-width: 28px;
                min-height: 28px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: #ccff00;
                color: #000000;
                border-color: #ccff00;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                color: #ffffff;
                border-color: #ef4444;
            }
        """
    },
    "techno": {
        "name": "Berlin Techno Monochrome",
        "description": "Noir rave profond avec ligne laser argent brossé et boutons carrés minimalistes",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #050505;
                background-color: #050505;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: #08080a;
                background-color: #08080a;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.45);
                box-shadow: 0 2px 14px rgba(255, 255, 255, 0.12);
                min-height: 40px;
                padding: 0 8px;
                margin: 0;
            }
            headerbar windowhandle,
            headerbar windowcontrols {
                background: transparent;
                border: none;
                box-shadow: none;
            }
            headerbar .app-title {
                color: #ffffff;
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 2.2px;
            }
            headerbar button,
            headerbar windowcontrols button {
                background: transparent;
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 2px;
                min-width: 26px;
                min-height: 26px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: #ffffff;
                color: #000000;
                border-color: #ffffff;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                color: #ffffff;
                border-color: #ef4444;
            }
        """
    },
    "cyberpunk": {
        "name": "Cyberpunk Neo-Tokyo",
        "description": "Double halo néon magenta (#ff007f) et cyan électrique (#00f5d4)",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #090214;
                background-color: #090214;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: linear-gradient(90deg, #110322 0%, #080a1c 100%);
                background-color: #0d0418;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 2px solid #ff007f;
                box-shadow: 0 4px 20px rgba(255, 0, 127, 0.45);
                min-height: 42px;
                padding: 0 8px;
                margin: 0;
            }
            headerbar windowhandle,
            headerbar windowcontrols {
                background: transparent;
                border: none;
                box-shadow: none;
            }
            headerbar .app-title {
                color: #00f5d4;
                font-weight: 800;
                font-size: 13px;
                letter-spacing: 1.4px;
                text-shadow: 0 0 10px rgba(0, 245, 212, 0.6);
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(255, 0, 127, 0.12);
                color: #ff007f;
                border: 1px solid rgba(255, 0, 127, 0.35);
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: #ff007f;
                color: #ffffff;
                box-shadow: 0 0 10px rgba(255, 0, 127, 0.8);
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #00f5d4;
                color: #000000;
                border-color: #00f5d4;
                box-shadow: 0 0 10px rgba(0, 245, 212, 0.8);
            }
        """
    },
    "y2k": {
        "name": "Y2K Chrome Iridescent",
        "description": "Reflet métal liquide et lilas holographique aux touches argentées",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #13141f;
                background-color: #13141f;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: linear-gradient(180deg, rgba(38, 42, 66, 0.95) 0%, rgba(18, 19, 32, 0.95) 100%);
                background-color: #161726;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 2px solid #d946ef;
                box-shadow: 0 3px 18px rgba(217, 70, 239, 0.35);
                min-height: 42px;
                padding: 0 8px;
                margin: 0;
            }
            headerbar windowhandle,
            headerbar windowcontrols {
                background: transparent;
                border: none;
                box-shadow: none;
            }
            headerbar .app-title {
                color: #e0e7ff;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 0.8px;
                text-shadow: 0 0 8px rgba(217, 70, 239, 0.4);
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(217, 70, 239, 0.12);
                color: #e0e7ff;
                border: 1px solid rgba(217, 70, 239, 0.28);
                border-radius: 8px;
                min-width: 28px;
                min-height: 28px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: rgba(217, 70, 239, 0.32);
                border-color: #d946ef;
                color: #ffffff;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                color: #ffffff;
            }
        """
    },
    "arcade": {
        "name": "80s Retro Synthwave",
        "description": "Ambiance arcade vintage avec halo rose rétro et orange coucher de soleil",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #140320;
                background-color: #140320;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: linear-gradient(90deg, #1f0430 0%, #2b082e 100%);
                background-color: #1a0426;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 2px solid #f43f5e;
                box-shadow: 0 3px 18px rgba(244, 63, 94, 0.4);
                min-height: 42px;
                padding: 0 8px;
                margin: 0;
            }
            headerbar windowhandle,
            headerbar windowcontrols {
                background: transparent;
                border: none;
                box-shadow: none;
            }
            headerbar .app-title {
                color: #fb7185;
                font-weight: 800;
                font-size: 13px;
                letter-spacing: 1.2px;
                text-shadow: 0 0 10px rgba(244, 63, 94, 0.5);
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(244, 63, 94, 0.12);
                color: #fecdd3;
                border: 1px solid rgba(244, 63, 94, 0.3);
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: #f43f5e;
                color: #ffffff;
                box-shadow: 0 0 10px rgba(244, 63, 94, 0.6);
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #fb923c;
                color: #ffffff;
                border-color: #fb923c;
            }
        """
    },
    "luxury": {
        "name": "Midnight Gold Executive",
        "description": "Noir onyx satiné rehaussé d'un fin liseré or champagne brossé (#f59e0b)",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #09090b;
                background-color: #09090b;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: linear-gradient(180deg, #141318 0%, #0d0d10 100%);
                background-color: #100f14;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 1px solid #d97706;
                box-shadow: 0 2px 16px rgba(217, 119, 6, 0.32);
                min-height: 42px;
                padding: 0 8px;
                margin: 0;
            }
            headerbar windowhandle,
            headerbar windowcontrols {
                background: transparent;
                border: none;
                box-shadow: none;
            }
            headerbar .app-title {
                color: #fef3c7;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 1.5px;
                text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(245, 158, 11, 0.08);
                color: #fde68a;
                border: 1px solid rgba(245, 158, 11, 0.22);
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: rgba(245, 158, 11, 0.25);
                border-color: #f59e0b;
                color: #ffffff;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                color: #ffffff;
            }
        """
    },
    "zen": {
        "name": "Nordic Zen Forest",
        "description": "Vert sauge scandinave profond avec doux liseré thé matcha apaisant (#34d399)",
        "css": """
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {
                background: #06110e;
                background-color: #06110e;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {
                background: linear-gradient(180deg, #0f221c 0%, #0a1713 100%);
                background-color: #0b1915;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 2px solid #34d399;
                box-shadow: 0 3px 16px rgba(52, 211, 153, 0.28);
                min-height: 42px;
                padding: 0 8px;
                margin: 0;
            }
            headerbar windowhandle,
            headerbar windowcontrols {
                background: transparent;
                border: none;
                box-shadow: none;
            }
            headerbar .app-title {
                color: #a7f3d0;
                font-weight: 600;
                font-size: 13px;
                letter-spacing: 0.8px;
            }
            headerbar button,
            headerbar windowcontrols button {
                background: rgba(52, 211, 153, 0.08);
                color: #d1fae5;
                border: 1px solid rgba(52, 211, 153, 0.2);
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                margin: 2px;
            }
            headerbar button:hover,
            headerbar windowcontrols button:hover {
                background: rgba(52, 211, 153, 0.25);
                border-color: #34d399;
                color: #ffffff;
            }
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {
                background: #ef4444;
                color: #ffffff;
            }
        """
    }
}


def read_db_setting(key, default=None):
    """Lit une clé de configuration dans la table settings de SQLite."""
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
    """Extrait le style demandé via --titlebar <style> ou --titlebar=<style>."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--titlebar="):
            return arg.split("=", 1)[1].strip().lower()
        if arg == "--titlebar" and i + 1 < len(args):
            return args[i + 1].strip().lower()
        i += 1
    return None


def extract_primary_hex_color(bg_str):
    """Extrait une couleur hexadécimale propre d'une chaîne (#090a0d ou linear-gradient(...))."""
    if not bg_str:
        return "#08090c"
    bg_clean = bg_str.strip()
    if bg_clean.startswith("#"):
        return bg_clean[:7]
    import re
    match = re.search(r"#[0-9a-fA-F]{6}", bg_clean)
    if match:
        return match.group(0)
    return "#08090c"


def apply_css_to_provider(provider, css_str):
    """Charge une chaîne CSS dans un CssProvider GTK de manière moderne et rétrocompatible."""
    if hasattr(provider, "load_from_string"):
        provider.load_from_string(css_str)
    else:
        provider.load_from_data(css_str.encode("utf-8"))


def generate_css(style_name, custom_bg=None):
    """Génère le CSS adapté au style choisi et à la couleur de fond."""
    clean_style = (style_name or "transparent").lower().strip()
    if clean_style not in TITLEBAR_STYLES:
        clean_style = "transparent"

    base_css = TITLEBAR_STYLES[clean_style]["css"]

    if clean_style == "match-bg":
        bg_hex = extract_primary_hex_color(custom_bg or read_db_setting("main_background", "#08090c"))
        return f"""
            window,
            window.background,
            window.csd,
            window.solid-csd,
            window:backdrop,
            decoration,
            decoration:backdrop,
            .todolist-window {{
                background: {bg_hex};
                background-color: {bg_hex};
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }}
            headerbar,
            headerbar:backdrop,
            window.maximized headerbar,
            window.fullscreen headerbar,
            window.tiled headerbar,
            .todolist-headerbar {{
                background: {bg_hex};
                background-color: {bg_hex};
                background-image: none;
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: none;
                min-height: 40px;
                padding: 0 8px;
                margin: 0;
                border-radius: 0;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }}
            headerbar windowhandle,
            headerbar windowhandle:backdrop,
            headerbar windowcontrols,
            headerbar windowcontrols.start,
            headerbar windowcontrols.end,
            headerbar windowcontrols:backdrop,
            .todolist-headerbar windowhandle,
            .todolist-headerbar windowcontrols {{
                background: transparent;
                background-color: transparent;
                background-image: none;
                border: none;
                box-shadow: none;
                margin: 0;
                padding: 0;
                border-radius: 0;
            }}
            headerbar .app-title-box {{
                opacity: 1;
            }}
            headerbar .app-title {{
                color: #f1f5f9;
                font-weight: 600;
                font-size: 13px;
            }}
            headerbar button,
            headerbar windowcontrols button {{
                background: rgba(255, 255, 255, 0.06);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 6px;
                min-width: 28px;
                min-height: 28px;
                padding: 3px 6px;
                margin: 2px;
            }}
            headerbar button:hover,
            headerbar windowcontrols button:hover {{
                background: rgba(255, 255, 255, 0.16);
                color: #ffffff;
                border-color: rgba(255, 255, 255, 0.22);
            }}
            headerbar button.close:hover,
            headerbar windowcontrols button.close:hover {{
                background: #ef4444;
                border-color: #ef4444;
                color: #ffffff;
            }}
        """

    return base_css


def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    url = sys.argv[1]

    # Détermination du style de départ :
    # 1. Argument CLI (--titlebar glass)
    # 2. Variable d'environnement (TODOLIST_TITLEBAR)
    # 3. Base SQLite (settings.titlebar_style)
    # 4. Défaut : transparent
    cli_style = parse_titlebar_arg(sys.argv[1:])
    env_style = os.environ.get("TODOLIST_TITLEBAR")
    db_style = read_db_setting("titlebar_style")
    active_style = cli_style or env_style or db_style or "transparent"

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
                win.add_css_class("todolist-window")
                win.set_title(APP_NAME)
                win.set_default_size(1280, 850)
                win.maximize()  # Plein écran par défaut, avec bouton pour réduire à volonté

                # Configuration de l'icône de l'application pour GTK / GNOME
                assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "assets"))
                display = Gdk.Display.get_default()
                if display:
                    icon_theme = Gtk.IconTheme.get_for_display(display)
                    if os.path.exists(assets_dir):
                        icon_theme.add_search_path(assets_dir)
                win.set_icon_name("todolist")

                # Création et configuration de la HeaderBar personnalisée
                header_bar = Gtk.HeaderBar()
                header_bar.add_css_class("todolist-headerbar")
                header_bar.set_show_title_buttons(True)
                header_bar.set_hexpand(True)

                # Titre centré élégant avec icône et libellé
                title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                title_box.add_css_class("app-title-box")

                # Icône dans le header
                try:
                    icon_img = Gtk.Image.new_from_icon_name("todolist")
                    title_box.append(icon_img)
                except Exception:
                    pass

                title_label = Gtk.Label(label=APP_NAME)
                title_label.add_css_class("app-title")
                title_box.append(title_label)

                header_bar.set_title_widget(title_box)
                win.set_titlebar(header_bar)

                # Fournisseur CSS pour le style dynamique de la HeaderBar
                css_provider = Gtk.CssProvider()
                initial_css = generate_css(active_style)
                apply_css_to_provider(css_provider, initial_css)

                if display:
                    Gtk.StyleContext.add_provider_for_display(
                        display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
                    )

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

                # Raccordement du message handler pour changement de style en direct depuis l'application
                ucm = webview.get_user_content_manager()
                if ucm:
                    try:
                        ucm.register_script_message_handler("set_titlebar_style")

                        def on_script_message(manager, js_result):
                            try:
                                raw_str = ""
                                if hasattr(js_result, "to_string"):
                                    raw_str = js_result.to_string()
                                elif hasattr(js_result, "get_js_value"):
                                    raw_str = js_result.get_js_value().to_string()
                                else:
                                    raw_str = str(js_result)

                                # Peut être une chaîne directe ("glass") ou un JSON ({"style": "match-bg", "bg": "#121316"})
                                target_style = raw_str
                                target_bg = None
                                try:
                                    data = json.loads(raw_str)
                                    if isinstance(data, dict):
                                        target_style = data.get("style", "transparent")
                                        target_bg = data.get("bg_color")
                                except Exception:
                                    pass

                                new_css = generate_css(target_style, target_bg)
                                apply_css_to_provider(css_provider, new_css)
                            except Exception as err:
                                sys.stderr.write(f"Erreur mise à jour CSS HeaderBar: {err}\n")

                        ucm.connect("script-message-received::set_titlebar_style", on_script_message)
                    except Exception as err:
                        sys.stderr.write(f"Avertissement UserContentManager: {err}\n")

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

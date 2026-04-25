"""Asset paths and template metadata for AetherGazer.

Directories, index files, and template paths.
Pure values — no imports of cv2, device, or vision.
"""
from __future__ import annotations

import sys
from pathlib import Path

# --- Directory paths ---
# Frozen (PyInstaller onedir): assets are inside _internal/ (sys._MEIPASS)
# Development: assets are at project root
if getattr(sys, "frozen", False):
    _BASE = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    # resources.py -> knowledge/ -> aether_gazer/ -> games/ -> anime_game_afk/ -> src/ -> project_root
    _BASE = Path(__file__).resolve().parents[5]

ASSETS_ROOT = _BASE / "assets" / "aether_gazer"
TEMPLATE_DIR = ASSETS_ROOT / "templates"
TEMPLATE_INDEX = TEMPLATE_DIR / "index.json"

"""Asset paths and template metadata for AetherGazer.

Directories, index files, and state-template definitions.
Pure values — no imports of cv2, device, or vision.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
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
TEXT_TEMPLATE_DIR = TEMPLATE_DIR / "text"
TEMPLATE_INDEX = TEMPLATE_DIR / "index.json"


@dataclass(frozen=True)
class StateTemplateDef:
    """Metadata for a game-state detection template."""
    name: str
    filename: str
    search_frac: tuple[float, float, float, float] | None  # (fx1, fy1, fx2, fy2)
    threshold: float
    ref_height: int = 900  # template captured at this height


# Priority order matters — check most critical states first.
# search_frac: fractional (x1, y1, x2, y2) in [0..1], converted from 1600x900 pixels.
STATE_TEMPLATES: tuple[StateTemplateDef, ...] = (
    StateTemplateDef(
        name="mission_failed",
        filename="txt_mission_failed.png",
        search_frac=(0.25, 0.056, 0.75, 0.278),
        threshold=0.60,
    ),
    StateTemplateDef(
        name="revive_prompt",
        filename="txt_revive_800.png",
        search_frac=None,
        threshold=0.70,
    ),
    StateTemplateDef(
        name="skip_story_confirm",
        filename="txt_skip_story.png",
        search_frac=(0.3125, 0.222, 0.6875, 0.389),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="continuous_battle",
        filename="txt_continuous_battle.png",
        search_frac=(0.25, 0.244, 0.75, 0.4),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="prep_battle",
        filename="txt_prep_battle.png",
        search_frac=(0.625, 0.867, 1.0, 1.0),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="battle_hud",
        filename="txt_pause.png",
        search_frac=(0.0, 0.922, 0.125, 1.0),
        threshold=0.65,
    ),
    StateTemplateDef(
        name="stage_map",
        filename="txt_progress.png",
        search_frac=(0.0, 0.911, 0.1875, 1.0),
        threshold=0.60,
    ),
)

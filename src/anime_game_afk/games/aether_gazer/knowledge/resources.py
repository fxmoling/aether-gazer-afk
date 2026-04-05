"""Asset paths and template metadata for AetherGazer.

Directories, index files, and state-template definitions.
Pure values — no imports of cv2, device, or vision.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from anime_game_afk.core.types import Rect

# --- Directory paths ---
ASSETS_ROOT = Path("assets/aether_gazer")
TEMPLATE_DIR = ASSETS_ROOT / "templates"
TEXT_TEMPLATE_DIR = TEMPLATE_DIR / "text"
TEMPLATE_INDEX = TEMPLATE_DIR / "index.json"
SCREENSHOT_DIR = ASSETS_ROOT / "screenshots"


@dataclass(frozen=True)
class StateTemplateDef:
    """Metadata for a game-state detection template."""
    name: str
    filename: str
    search_region: Rect | None
    threshold: float
    half_scale: bool = False  # True if template is 800x450


# Priority order matters — check most critical states first.
# Higher-priority states appear earlier in the list.
STATE_TEMPLATES: tuple[StateTemplateDef, ...] = (
    StateTemplateDef(
        name="mission_failed",
        filename="txt_mission_failed.png",
        search_region=Rect(400, 50, 800, 200),
        threshold=0.60,
    ),
    StateTemplateDef(
        name="revive_prompt",
        filename="txt_revive_800.png",
        search_region=None,
        threshold=0.70,
        half_scale=True,
    ),
    StateTemplateDef(
        name="skip_story_confirm",
        filename="txt_skip_story.png",
        search_region=Rect(500, 200, 600, 150),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="continuous_battle",
        filename="txt_continuous_battle.png",
        search_region=Rect(400, 220, 800, 140),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="prep_battle",
        filename="txt_prep_battle.png",
        search_region=Rect(1000, 780, 600, 120),
        threshold=0.70,
    ),
    StateTemplateDef(
        name="battle_hud",
        filename="txt_pause.png",
        search_region=Rect(0, 830, 200, 70),
        threshold=0.65,
    ),
    StateTemplateDef(
        name="stage_map",
        filename="txt_progress.png",
        search_region=Rect(0, 820, 300, 80),
        threshold=0.60,
    ),
)

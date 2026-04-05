"""Game constants for AetherGazer.

Design resolution, match thresholds, timing defaults.
Pure values — no imports of cv2, device, or vision.
"""
from anime_game_afk.core.types import Resolution

# Design coordinate system — all coordinates use this resolution
DESIGN_RESOLUTION = Resolution(width=1600, height=900)

# Screen center — used for wake-up clicks and idle dismissal
SCREEN_CENTER_X = 800
SCREEN_CENTER_Y = 450

# Back button — top-left corner, shared by most pages
BACK_BUTTON_X = 35
BACK_BUTTON_Y = 35

# Template matching thresholds
MATCH_THRESHOLD = 0.65
HIGH_CONFIDENCE = 0.80

# Timing defaults (seconds)
CLICK_WAIT = 1.0
NAV_WAIT = 1.5
PAGE_LOAD_WAIT = 2.0
BATTLE_KEY_INTERVAL = 0.25
WALK_DEFAULT_DURATION = 2.0

# Game mechanics
STAMINA_CAP = 200

# Unknown state rotation phases (cycle_position -> action)
UNKNOWN_ROTATION = {
    "space": (0, 5),
    "attack": (5, 10),
    "walk": (10, 20),
    "esc_enter": (20, 25),
}

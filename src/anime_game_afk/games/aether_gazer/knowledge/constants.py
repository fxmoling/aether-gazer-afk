"""Game constants for AetherGazer.

Match thresholds, timing defaults, game mechanics.
Pure values — no imports of cv2, device, or vision.

Coordinate convention: all positions are fractional [0.0, 1.0].
"""

# Template matching thresholds
MATCH_THRESHOLD = 0.80
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

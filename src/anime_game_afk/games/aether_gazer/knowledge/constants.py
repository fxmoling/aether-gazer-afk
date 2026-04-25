"""Game constants for AetherGazer.

Match thresholds and timing defaults.
Pure values — no imports of cv2, device, or vision.

Coordinate convention: all positions are fractional [0.0, 1.0].
"""

# Template matching thresholds
MATCH_THRESHOLD = 0.80

# Timing defaults (seconds)
CLICK_WAIT = 1.0
NAV_WAIT = 1.5
PAGE_LOAD_WAIT = 2.0

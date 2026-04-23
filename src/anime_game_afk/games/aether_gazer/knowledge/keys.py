"""Virtual key code constants for AetherGazer.

All VK codes used by the game, organized by context.
Pure values — no imports of cv2, device, or vision.
"""

# --- UI Navigation ---
VK_ESCAPE = 0x1B
VK_ENTER = 0x0D
VK_TAB = 0x09
VK_SPACE = 0x20

# --- Hub shortcuts (press from main hub to open panel) ---
VK_G = 0x47       # Daily tasks panel
VK_H = 0x48       # Mail panel
VK_J_HUB = 0x4A   # Battle select (same physical key as attack J)
VK_T = 0x54       # Tactics protocol (对策协议)

# --- Battle attack keys ---
VK_J = 0x4A       # Normal attack
VK_U = 0x55       # Skill 1
VK_I = 0x49       # Skill 2
VK_O = 0x4F       # Skill 3
VK_R = 0x52       # Ultimate

VK_1 = 0x31       # Combo 1 / QTE
VK_2 = 0x32       # Combo 2 / QTE

# --- Movement (WASD) + Camera (QE) ---
VK_W = 0x57       # Forward
VK_A = 0x41       # Left
VK_S = 0x53       # Backward
VK_D = 0x44       # Right
VK_Q = 0x51       # Camera rotate left
VK_E = 0x45       # Camera rotate right

# --- Attack rotation sequence ---
# One full cycle: J J U J I J O R 1 2
ATTACK_CYCLE_KEYS = [
    VK_J, VK_J, VK_U, VK_J, VK_I, VK_J, VK_O, VK_R, VK_1, VK_2,
]

# --- Convenience groups ---
SKILL_KEYS = [VK_U, VK_I, VK_O]
MOVE_KEYS = [VK_W, VK_A, VK_S, VK_D]

# --- Human-readable names for logging ---
KEY_NAMES: dict[int, str] = {
    VK_ESCAPE: "ESC", VK_ENTER: "Enter", VK_TAB: "Tab",
    VK_SPACE: "Space", VK_G: "G", VK_H: "H", VK_T: "T",
    VK_J: "J", VK_U: "U", VK_I: "I", VK_O: "O", VK_R: "R",
    VK_1: "1", VK_2: "2",
    VK_W: "W", VK_A: "A", VK_S: "S", VK_D: "D",
}


def key_name(vk: int) -> str:
    """Return human-readable name for a VK code."""
    return KEY_NAMES.get(vk, f"0x{vk:02X}")


def letter_to_vk(letter: str) -> int:
    """Convert a single letter (e.g. 'J') to its VK code."""
    ch = letter.upper()
    if len(ch) == 1 and "A" <= ch <= "Z":
        return ord(ch)
    if len(ch) == 1 and "0" <= ch <= "9":
        return ord(ch)
    raise ValueError(f"Unsupported key letter: {letter!r}")

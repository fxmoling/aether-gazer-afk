"""Auto-battle system — YAML combat scripts + execution + monitoring."""

from anime_game_afk.games.aether_gazer.combat.script import (
    CombatScript,
    CombatStep,
    load_script,
    load_script_file,
)

__all__ = ["CombatScript", "CombatStep", "load_script", "load_script_file"]

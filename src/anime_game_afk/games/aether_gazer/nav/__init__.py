"""DEPRECATED: This module has been migrated.

Navigator → ops/navigate/goto_page.py
Navigation graph → knowledge/navigation.py

This wrapper exists temporarily so old imports produce clear errors.
Remove after all references have been updated.
"""
import warnings


def __getattr__(name: str) -> object:
    """Raise clear deprecation error for any attribute access."""
    warnings.warn(
        f"anime_game_afk.games.aether_gazer.nav is DEPRECATED. "
        f"Attribute '{name}' has been migrated:\n"
        f"  Navigator → ops/navigate/goto_page.py\n"
        f"  Navigation graph → knowledge/navigation.py\n"
        f"Update your imports accordingly.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise ImportError(
        f"Module 'nav' is deprecated. '{name}' has moved. "
        f"See deprecation warning for new locations."
    )

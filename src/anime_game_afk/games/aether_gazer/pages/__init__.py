"""DEPRECATED: This module has been migrated.

Page definitions → knowledge/pages.py
Page identification → ops/perception/identify_page.py
Template identification → ops/perception/identify_page.py

This wrapper exists temporarily so old imports produce clear errors.
Remove after all references have been updated.
"""
import warnings


def __getattr__(name: str) -> object:
    """Raise clear deprecation error for any attribute access."""
    warnings.warn(
        f"anime_game_afk.games.aether_gazer.pages is DEPRECATED. "
        f"Attribute '{name}' has been migrated:\n"
        f"  Page definitions → knowledge/pages.py\n"
        f"  Page identification → ops/perception/identify_page.py\n"
        f"  Template matching → ops/perception/identify_page.py\n"
        f"Update your imports accordingly.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise ImportError(
        f"Module 'pages' is deprecated. '{name}' has moved. "
        f"See deprecation warning for new locations."
    )

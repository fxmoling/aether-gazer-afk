"""Auto-update checker via GitHub Releases API.

Checks whether a newer release is available and provides update info
to the GUI. Does NOT perform in-place updates — directs the user to
the GitHub release page for manual download.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from anime_game_afk import __version__
from anime_game_afk.runtime.logger import get_logger

logger = get_logger("updater")

GITHUB_OWNER = "fxmoling"
GITHUB_REPO = "anime-game-afk"
GITHUB_API_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
RELEASE_PAGE_URL = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse ``'0.1.0'`` or ``'v0.1.0'`` into a comparable tuple."""
    v = v.lstrip("v").strip()
    parts: list[int] = []
    for segment in v.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            break
    return tuple(parts) or (0,)


def check_for_update(timeout: float = 5.0) -> dict[str, Any] | None:
    """Check GitHub for a newer release.

    Returns a dict with update information, or *None* on network error.

    The call is synchronous and should be invoked from a background
    thread or with a short *timeout* (default 5 s) to avoid blocking
    the GUI.
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": f"anime-game-afk/{__version__}",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())

        latest_tag: str = data.get("tag_name", "")
        latest_version = latest_tag.lstrip("v")

        if _parse_version(latest_version) > _parse_version(__version__):
            download_url = ""
            for asset in data.get("assets", []):
                if asset.get("name", "").endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break

            return {
                "has_update": True,
                "current_version": __version__,
                "latest_version": latest_version,
                "release_url": data.get("html_url", RELEASE_PAGE_URL),
                "download_url": download_url,
                "release_notes": data.get("body", ""),
            }

        logger.info(
            "Already up to date (current={cur}, latest={lat})",
            cur=__version__,
            lat=latest_version,
        )
        return {
            "has_update": False,
            "current_version": __version__,
            "latest_version": latest_version,
        }

    except (urllib.error.URLError, json.JSONDecodeError, OSError, KeyError) as exc:
        logger.warning("Update check failed: {exc}", exc=str(exc))
        return None

"""Global pytest configuration.

Patches asyncio.sleep to return instantly during tests.
This eliminates ~100s of real wait time from 117 sleep calls
across 22 source files, reducing test time from ~112s to ~10s.
"""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Replace asyncio.sleep with an instant no-op for all tests."""
    async def _instant_sleep(seconds):
        pass  # No actual waiting

    monkeypatch.setattr("asyncio.sleep", _instant_sleep)

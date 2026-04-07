"""Checks — observe game state without side effects.

Checks take a screenshot and analyze it (OCR, template matching, color
detection, etc.).  They return a structured CheckResult with ``passed``
flag and optional data (coordinates, text, confidence).

Checks NEVER modify game state (no clicks, no key presses).

Layer 5A: imports knowledge (L4), vision (L2).
"""

# checks/ — Observation Layer (Layer 5A)

Pure observation checks that detect game state without side effects.

Checks take a screenshot and analyze it (template matching, OCR, pixel comparison).
They return a structured `CheckResult` with `passed` flag and optional metadata.

**Checks NEVER modify game state** — no clicks, no key presses, no swipes.

## Files

| File | Purpose |
|------|---------|
| `base.py` | `CheckResult` dataclass and `Check` protocol — contract for all checks |
| `battle.py` | `InBattleCheck` — triple-signal AND detection (pause icon + dodge button + skill contrast) |
| `ocr.py` | `FindTextCheck` — text detection via OCR with optional region limiting |
| `page.py` | `OnPageCheck`, `AtHubCheck` — screen identification via template matching + OCR keywords |
| `state.py` | `ScreenUnchangedCheck` — detect screen change via mean absolute pixel difference |

## Check Protocol

All checks implement:

```python
async def evaluate(ctx: OpContext) -> CheckResult:
    """Return CheckResult(passed=bool, data=..., message=str)"""
```

## Layer Dependencies

- **Depends on**: Layer 2 (vision/OCR), Layer 4 (knowledge/page templates)
- **Must not depend on**: Layer 6+ — no upward imports

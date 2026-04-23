# 多维变量 (Multidimensional Variable) Process Design

## Overview

A standalone Process that automates repeated 多维变量 roguelike dungeon runs.
Strategy: clear 1-1 → portal to 1-2 → fight → ESC+H exit with minimum score.
Loops indefinitely until user stops.

## Architecture

```
DuoweiProcess (Process)
  ├── NavigateToDuowei (one-time)
  └── Loop:
      └── DuoweiCombat (Task)
            ├── _start_challenge()
            ├── _complete_setup()      ← includes 赏金猎人 beacon select
            ├── _handle_treasure()     ← reused for 1-1 treasure + 1-2 reward
            ├── _walk_to_portal()      ← swipe(dx=0.02) + W + J
            ├── _fight_battle()        ← delegates to CombatStrategy
            ├── _handle_reward()       ← click center + confirm(0.608, 0.847)
            └── _exit_and_settle()     ← ESC → H → Enter → settlement
```

## Combat Strategy (Pluggable)

```python
class CombatStrategy(Protocol):
    async def fight(self, ctx: TaskContext) -> str:
        """Returns 'won', 'died', or 'timeout'."""
        ...

class BasicAttackCycle:
    """Default: J J U J I J O R 1 2 cycle until battle ends."""
```

## Step-by-Step Flow (Part B — Single Challenge)

### Step 1: _start_challenge()
- OCR screen for "开始挑战" or "继续挑战"
- If "继续挑战": click → handle "尚未结束的战局" dialog (ESC to settle, then retry)
- If "开始挑战": click → proceed to setup

### Step 2: _complete_setup()
- **Difficulty page**: OCR "下一步", click
- **Character page**: OCR "下一步", click
- **Beacon page**: swipe down (y offset 0.5), OCR "赏金猎人", click it, then OCR "开始挑战", click
- Wait for arena loading (~8s)

### Step 3: _handle_treasure() (1-1 initial treasure)
- OCR check for "珍宝"
- Click screen center (0.50, 0.40) to select card
- Click confirm (0.608, 0.847)
- Verify dismissed, retry if needed

### Step 4: _walk_to_portal()
- Swipe camera left: `swipe(0.55, 0.5, 0.53, 0.5, 300)` — dx=0.02, fractional, resolution-independent
- Walk W (hold_key 0.8s intervals) + press J each step
- Check every 3 steps for scene transition (OCR "击退"/"剩余"/"珍宝" or loading)
- Fallback: walk back S, scan 8 additional angles with swipe rotation
- Timeout: ~12 steps primary + 64 steps fallback

### Step 5: _fight_battle() (delegates to CombatStrategy)
- Default BasicAttackCycle: press J J U J I J O R 1 2 in loop
- Check every 5 cycles (~10s) for battle end
- Detect: "珍宝"/"确认" = won, "失败"/"复活" = died, max 30 checks = timeout

### Step 6: _handle_reward() (post-battle)
- OCR for "珍宝"/"放弃"/"确认" (actual reward screen, NOT arena HUD)
- Click center (0.50, 0.40) — selects card in multi-card, harmless in single
- Click confirm at **(0.608, 0.847)** — overlap zone for both single/multi layouts
  - Single-card button: x=0.372~0.628 → 92% = 0.608
  - Multi-card confirm: further right, 0.608 still within its area
- Up to 3 attempts

### Step 7: _exit_and_settle()
- Press ESC (1.5s wait)
- Press H (2.0s wait) — "退出并结算"
- Press Enter (5.0s wait) — confirm dialog
- Click through settlement: fixed "退出" at (0.901, 0.931) for 积分 screen
- Detect return: OCR "多维变量" + "开始挑战" or challenge hub keywords

## Error Recovery

- **Single failure**: attempt _exit_and_settle() → return to 多维变量 page → continue loop
- **3 consecutive failures**: stop Process, report error
- **Unknown state**: ESC spam as last resort

## Key Coordinates (all fractional 0.0–1.0)

| Element | Position | Notes |
|---------|----------|-------|
| Screen center | (0.50, 0.40) | Card select / dismiss |
| Reward confirm | (0.608, 0.847) | Overlap zone single/multi |
| Settlement 退出 | (0.901, 0.931) | Fixed on result screen |
| Portal swipe | dx=0.02 from (0.55, 0.5) | Calibrated for 1-1→1-2 |
| Challenge tab | (0.95, 0.92) | Hub navigation |

## Files

- `src/.../tasks/duowei_tasks.py` — DuoweiCombat task + CombatStrategy
- `src/.../processes/duowei_process.py` — DuoweiProcess (new)
- `scripts/duowei_runner.py` — E2E test wrapper

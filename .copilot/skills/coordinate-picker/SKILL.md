---
name: coordinate-picker
description: Use when needing to identify precise UI element coordinates from game screenshots — whenever placing clicks, defining button positions, or verifying coordinate accuracy for any game automation task
---

# Coordinate Picker

## Overview

Interactive HTML tool for precise coordinate picking from game screenshots. Eliminates guesswork when mapping UI element positions — user clicks directly on the screenshot and gets exact pixel + normalized coordinates.

## When to Use

- Mapping new UI element positions for click automation
- Verifying/correcting existing coordinate values
- Any time a coordinate is wrong or "off" and needs fixing
- Before writing ANY fixed-coordinate constant in task code

**MANDATORY:** Never estimate coordinates by eyeballing thumbnails or doing mental math on cropped images. Always use this picker tool.

## Workflow

### Step 1: Capture Screenshot

```python
# Take a foreground screenshot of the game window
import ctypes, ctypes.wintypes, numpy as np, cv2, os
import mss

os.makedirs('.tmp/coord-picker', exist_ok=True)

hwnd = ctypes.windll.user32.FindWindowW(None, 'AetherGazer')
ctypes.windll.user32.SetForegroundWindow(hwnd)
import time; time.sleep(0.5)

rc = ctypes.wintypes.RECT()
ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rc))
w, h = rc.right, rc.bottom

pt = ctypes.wintypes.POINT(0, 0)
ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))

from mss import MSS
with MSS() as sct:
    shot = sct.grab({'left': pt.x, 'top': pt.y, 'width': w, 'height': h})
    img = np.array(shot)[:,:,:3]

cv2.imwrite('.tmp/coord-picker/screenshot.png', img)
print(f'Saved {w}x{h} screenshot')
```

### Step 2: Open Picker

Open the HTML picker in a browser:

```powershell
Start-Process "C:\Users\Administrator\Desktop\aether-gazer-afk\.copilot\skills\coordinate-picker\picker.html"
```

User loads the screenshot (drag & drop or file picker), then clicks on target UI elements.

### Step 3: Read Coordinates

User reports coordinates from the picker. The `frac` values are the normalized coordinates (0.0-1.0) to use directly in code as `ClickOp(fx, fy)`.

## Features

- **8× zoom lens** follows cursor for pixel-precise clicking
- **Crosshair markers** on picked points
- **Both pixel and normalized coords** displayed
- **Right-click** to undo last point
- **Ctrl+Z** keyboard shortcut
- **Copy button** for each coordinate
- **Drag & drop** image loading

## Important Notes

- Screenshot must be taken at the **actual game resolution** (not thumbnail)
- Normalized coordinates `(fx, fy)` can be used directly regardless of resolution
- The picker HTML is at: `.copilot/skills/coordinate-picker/picker.html`
- Screenshots go in: `.tmp/coord-picker/`

## Code Pattern

After getting coordinates from picker:

```python
# In task class, define as class constants with verification comment
_REFRESH_BTN = (0.826, 0.856)  # Verified via coord-picker from 1920x1080 screenshot

# Use in task
await ClickOp(*self._REFRESH_BTN, wait=1.0).run(ctx)
```

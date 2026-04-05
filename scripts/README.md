# Scripts

Entry points and debug tools. All real logic lives in `src/`.

## Files

| File | Purpose |
|---|---|
| `run.py` | Main entry point: load YAML plan → run automation pipeline |
| `snap.py` | Debug tool: screenshot, click, crop for coordinate exploration |

## Usage

```bash
# Run the automation pipeline with default plan
python scripts/run.py

# Run with a custom plan
python scripts/run.py --plan path/to/my_plan.yaml

# List available processes
python scripts/run.py --list

# Dry-run: show what would execute without running
python scripts/run.py --dry-run

# Debug: take a screenshot and explore coordinates
python scripts/snap.py
```

## debug/

Historical exploration and development scripts. Kept for reference only.
These scripts may have broken imports and are NOT maintained.

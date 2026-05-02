# plans/ — Pipeline Plan Configs

YAML plan definitions consumed by the orchestrator's pipeline executor.

## Files

| File | Purpose |
|------|---------|
| `default.yaml` | Default plan template for new users — defines task execution order and enabled tasks |

## Format

Plans are YAML files defining which processes/tasks to run, in what order, with what parameters.
New plans can be added here and selected via the UI.

## Note

This directory contains **data files only** — orchestration logic lives in the parent `orchestrator/` directory.

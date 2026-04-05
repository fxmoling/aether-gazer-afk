# Architecture Restructure — Implementation Plan Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure codebase from flat scripts to 9-layer architecture per design spec.

**Approach:** Bottom-up, 4 waves. Each wave produces working, testable code.

**Spec:** `docs/superpowers/specs/2026-04-05-architecture-redesign-design.md`

---

## Waves

| Wave | Layers | Files | Description |
|------|--------|-------|-------------|
| 1 | 1-3 | `wave1-foundation.md` | Device adapter, vision toolkit, runtime services |
| 2 | 4-5 | `wave2-game-knowledge-ops.md` | Game knowledge models, atomic operations |
| 3 | 6-7 | `wave3-tasks-processes.md` | Composable tasks, complete processes |
| 4 | 8 + cleanup | `wave4-orchestrator-cleanup.md` | Pipeline, migration, old code removal |

## Execution Order

Wave 1 first. Each subsequent wave depends on the previous. Do NOT start Wave N+1 until Wave N passes evaluation.

## Docs Update

`docs-update.md` — Update outdated docs after all waves complete.

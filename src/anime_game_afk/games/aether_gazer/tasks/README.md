# tasks/ — Composable Tasks (Layer 6)

Multi-step sequences built from Layer 5 atomic ops.

## Files

| File | Responsibility |
|------|---------------|
| `base.py` | `TaskResult`, `TaskContext`, `Task` protocol |
| `navigation_tasks.py` | `ReturnToHub`, `EnterMainStory` — multi-step navigation |
| `shop_tasks.py` | `ClaimFreeStamina` — shop daily purchase |
| `mail_tasks.py` | `CollectAllMail` — mail reward collection |

## Layer Dependencies

- **Depends on**: Layer 5 (ops), Layer 4 (knowledge), Layer 3 (runtime), Layer 1 (device)
- **Must not depend on**: Layer 7 (processes) — no upward imports

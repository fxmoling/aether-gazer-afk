# memory/

Project memory — persistent knowledge base across AI-assisted development sessions.

## Purpose

Stores structured notes about project decisions, architecture, lessons learned, and progress. Loaded at the start of every new session to maintain context continuity.

## Files

| File | Contents |
|------|----------|
| `01-project-overview.md` | Project goals and compliance requirements |
| `02-reference-projects.md` | Reference projects research (MAA, M9A, ok-ww, BetterGI) |
| `03-tech-comparison.md` | Technical approach comparison and selection |
| `04-doc-review-round2.md` | Documentation review notes |
| `05-maaframework-api-research.md` | MaaFramework API research |
| `05-opc-installed.md` | OPC plugin installation record |
| `06-ui-mapping-paradigm.md` | UI coordinate verification + battle flow + anomaly catalog |
| `07-known-issues.md` | Known issues and limitations |
| `08-code-architecture.md` | 9-layer architecture design + implementation progress |
| `08-gsd-installed.md` | GSD plugin installation record |
| `09-code-review-lessons.md` | Code review lessons (7 rules + future checklist) |

## Conventions

- Files numbered with `01-`, `02-`, etc. prefix for ordering
- Content in Markdown, concise and structured
- Updated after every code change, structural change, or design decision
- Previously stored in `.claude/memory/`, migrated to project root for git tracking and easier access

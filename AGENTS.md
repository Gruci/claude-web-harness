# AGENTS.md — Codex project harness

> 담는 것: Codex 세션의 행동 규칙과 라우팅. 담지 않는 것: Claude 전용 하네스(→ `CLAUDE.md`·`HARNESS.md`)·상세 규칙(→ 각 정본 MD). 읽는 시점: Codex 세션 진입 시.

This is the Codex-only entry point for this project. Claude Code uses `CLAUDE.md` and `.claude/`; Codex uses this file, `.agents/`, and `.codex/`.

## Dual-agent boundary

- Ordinary Codex work must not load `CLAUDE.md` or scan `.claude/`. A triggered `*-cdx` adapter may read only its single matching `.claude/skills/<name>/SKILL.md`.
- Shared project truth lives in `README.md`, `DEVGUIDE.md`, `DESIGN_GUIDE.md`, `dev/`, `design/`, and `kernel/runner.py`.
- Codex-only behavior belongs in `AGENTS.md`, `.agents/`, or `.codex/`. Edit Claude-only harness files only for explicitly requested interoperability.
- Codex skill names end in `-cdx`.

## Read before editing

Read `EDITING.md` fresh immediately before every edit, then load only the documentation relevant to the target.

| Target | Required shared documentation |
|---|---|
| Any Markdown you write or edit | `dev/MD_STANDARD.md` — three rules, component test |
| Any new file or function | `dev/CONVENTIONS.md` — decided conventions and helper registry |
| Python | `DEVGUIDE.md`, then the relevant `dev/` sub-document |
| `frontend/` React and TypeScript | `DESIGN_GUIDE.md`, then the relevant `design/` sub-document |
| Database schema, tables, columns | `dev/DATA_MODEL.md` and `dev/NAMING.md` |
| Screen work of any kind | `design/RESPONSIVE.md` — desktop and mobile are defined together at plan time |
| Tests | use `$test-cdx`, which routes to `dev/TESTING.md` |
| Harness, hooks, gates | `HARNESS.md` |
| Disputing a rule | `dev/LESSONS.md` — the incident behind it |

Search first and read targeted ranges. Do not preload unrelated Markdown.

## Change workflow

- Every feature, behavioral change, refactor, performance change, or bug fix except an obvious typo or one configuration value must use `$feature-workflow-cdx`. Research and an explicitly approved plan are required before implementation.
- At implementation start, read `EDITING.md` fresh and register a task-board row tagged with your session id.
- Preserve unrelated edits. Never commit, revert, clean, reset, or delete them.
- Use task-suffixed document names when another session may be active: `docs/tasks/research_<task>.md` and `docs/tasks/plan_<task>.md`.
- Archive both documents under `docs/tasks/archive/YYYY-MM-DD-<task>/` in the same turn implementation completes, then remove the board row.

## Repository invariants

- Preserve dependency direction: domain packages → `db/` → `web/` API → `frontend/`. Never add reverse imports.
- New UI belongs in `frontend/src/` React. A backend route without its consuming component is an invisible orphan, not a finished feature.
- Before changing a signature or response shape, trace callers and consumers across DB, API, and React.
- Prefer existing helpers, the standard library, native platform features, and installed dependencies. Make surgical changes. Report unrelated dead code without removing it.
- Python and database conventions live in `dev/ARCHITECTURE.md`, `dev/NAMING.md`, `dev/DATA_MODEL.md`, and `dev/CONVENTIONS.md`. `kernel/runner.py` enforces the machine-checkable subset.

## Evidence and debugging

- Verify paths with search, database state with queries, and behavior by reading or running code. Never state an assumption as fact.
- Reproduce and trace the root cause, compare a working pattern, test one hypothesis with the smallest change, then add a regression test and fix it.
- After three failed fix attempts, stop editing and report the evidence and the likely architectural issue.
- Re-read targets that may be stale after compaction or concurrent edits.

## Verification and completion

- Run `python -X utf8 -m kernel.runner` and the checks proportionate to the change before claiming completion.
- A bug fix must show its reproduction test passing. UI work also requires a rendered inspection.
- Do not claim a test or build passed unless that command exited 0 in this checkout.
- Update the relevant shared Markdown in the same turn as durable contracts, routes, components, schemas, or user rules. Write it to `dev/MD_STANDARD.md`: one meaning per line, one fact in one place, and nothing that Glob, Grep, or git log already answers.
- Enforce checkable rules in `kernel/runner.py` or another deterministic gate. Markdown explains the rule but is not its enforcement. Check 17 validates Markdown structure at write time and `md_style_baseline.txt` may only shrink.

## Codex harness

Codex skills live in `.agents/skills/`, the lazy ladder in `.codex/lazy-persona-cdx.md`, and shared deterministic gates in `kernel/runner.py`. Use the smallest applicable skill. Delegated results must be concise and include file:line evidence.

---
name: lazy-audit-cdx
description: Whole-repository audit for over-engineering — a ranked list of what to delete, simplify, or replace with standard-library equivalents. Use for "audit this codebase", "find bloat", or a scheduled monthly review. Reports only; never applies fixes.
---

# Repository bloat audit for Codex

1. Read only `.claude/skills/lazy-audit/SKILL.md` as the shared detailed workflow, plus `.codex/lazy-persona-cdx.md` for the ladder.
2. Follow `AGENTS.md`. This skill produces a report and changes nothing.
3. Scan the whole repository rather than a diff. Rank by lines removed per unit of risk.
4. Separate confirmed dead code from merely unused-looking code. Trace callers before calling anything dead.
5. For each entry give the location, the reason it is excess, and the concrete replacement.

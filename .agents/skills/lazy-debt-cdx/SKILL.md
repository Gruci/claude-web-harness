---
name: lazy-debt-cdx
description: Harvest every `lazy:` marker in the codebase into a debt ledger so deliberate shortcuts get tracked instead of rotting. Use for "lazy debt", "what did we defer", "list the shortcuts", or a scheduled monthly review. Reports only.
---

# Debt ledger for Codex

1. Read only `.claude/skills/lazy-debt/SKILL.md` as the shared detailed workflow, plus `.codex/lazy-persona-cdx.md` for the marker format.
2. Follow `AGENTS.md`. This skill produces a report and changes nothing.
3. Collect every `lazy:` marker with its file, line, stated ceiling, and stated upgrade path.
4. Flag markers whose stated ceiling has since been crossed — those are the ones that became real debt.
5. Flag markers with no ceiling or no upgrade path. A shortcut without a stated limit is untracked debt, not a lazy decision.

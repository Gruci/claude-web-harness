---
name: feature-workflow-cdx
description: Run this project's mandatory scope interview, research, plan, approval, implementation, verification, and archive workflow. Use for features, behavioral changes, refactors, performance work, and bug fixes except an obvious typo or one configuration value.
---

# Feature workflow for Codex

1. Follow the trigger rules, dual-agent boundary, and change workflow in `AGENTS.md`.
2. Read only `.claude/skills/feature-workflow/SKILL.md` for additional shared project detail. Do not load `CLAUDE.md` or other Claude harness files.
3. Ask one concise blocking question when a material choice cannot be discovered. Skip the interview when the request already carries scope, exposure, and data-loading decisions.
4. Ignore Claude model names and tool syntax. Use Codex-native planning, tools, and agents.
5. Do not edit source before plan approval. After approval, finish the scoped implementation, verification, shared-document updates, task archive, and board cleanup without repeated non-material check-ins.

## Codex-only additions

1. Use task-suffixed names when another session may be active: `docs/tasks/research_<task>.md` and `docs/tasks/plan_<task>.md`.
2. At implementation start, read `EDITING.md` fresh and register a board row tagged with your session id. Remove it only after the work is reported complete.
3. State the disagreement in one line with one line of reasoning when an instruction conflicts with your technical judgment, then carry out the instruction.

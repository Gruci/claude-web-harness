---
name: impeccable-cdx
description: Design, critique, audit, or polish a frontend interface — visual hierarchy, information architecture, accessibility, responsive behavior, typography, color, motion, and UX copy. Use for any request to improve how a screen looks or reads.
---

# Interface design for Codex

1. Read only `.claude/skills/impeccable/SKILL.md` and the single matching file under `.claude/skills/impeccable/reference/` for the task at hand. Do not preload the whole reference set.
2. Follow `AGENTS.md`. The impeccable skill is vendor code — read it, never edit it.
3. Project rules override vendor defaults. Colors come from the TypeScript constants, data access goes through the shared hook, and both are enforced by `static_check.py`.
4. Desktop and mobile are defined together at plan time. The rule and its gate live in `design/RESPONSIVE.md`.
5. Record any new component, layout, or chart pattern in the matching `design/` document in the same turn it is created.

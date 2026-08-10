---
name: review-loop-cdx
description: Service-owner review loop for screens, metrics, and copy — evaluate business meaning and completeness rather than code quality, then rework and re-review. Use after finishing a page or dashboard, or for "review this screen".
---

# Owner review loop for Codex

1. Read only `.claude/skills/review-loop/SKILL.md` as the shared detailed workflow, plus `design/UX.md` for label rules.
2. Follow `AGENTS.md`. Ignore Claude-specific agent and model syntax.
3. Review as the person who actually uses this service daily: does this screen answer a real question, is the priority order right, does any number need explaining before it is trusted.
4. Judge business meaning and information hierarchy, not code structure. Code review belongs elsewhere.
5. Feed findings back into a rework pass, then re-review. Stop when no finding changes a user decision.

---
name: lazy-review-cdx
description: Review the current diff for over-engineering only — what to delete, what to replace with a standard-library or existing helper. Use for "is this over-engineered", "what can we delete", or right after finishing an implementation.
---

# Over-engineering review for Codex

1. Read only `.claude/skills/lazy-review/SKILL.md` as the shared detailed workflow, plus `.codex/lazy-persona-cdx.md` for the ladder.
2. Follow `AGENTS.md`. This skill hunts complexity, not correctness bugs.
3. Look for reinvented standard library, unneeded dependencies, single-implementation interfaces, speculative flexibility, and configuration for values that never change.
4. One line per finding: location, what to cut, what replaces it.
5. Apply the findings in the same turn when the change is mechanical and the diff is still open.

---
name: test-cdx
description: Create, run, and assess this project's tests using project conventions. Use for regression tests, pytest requests, coverage checks, new `_fetch_*` or `_format_*` behavior, bug-fix verification, frontend typechecks, or build validation.
---

# Testing for Codex

1. Read only `.claude/skills/test/SKILL.md` as the shared detailed workflow, and read `dev/TESTING.md` fresh.
2. Follow `AGENTS.md`. Ignore Claude-specific model and tool syntax.
3. Choose the narrowest test layer that proves the contract, then run targeted tests before broader suites.
4. For bug fixes, demonstrate failure before the fix when practical and passing after it. Do not claim success from code inspection alone.
5. Report exact commands, exit codes, failures, warnings, and any checks not run.

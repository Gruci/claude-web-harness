---
name: md-audit-cdx
description: Monthly Markdown drift audit — compare what the canonical documents claim against the code that actually exists. Use for "audit the docs", "check the MD against the code", or a scheduled monthly review. Reports only; never edits.
---

# Markdown audit for Codex

1. Read only `.claude/skills/md-audit/SKILL.md` as the shared detailed workflow, plus `dev/MD_STANDARD.md` for the judgment criteria.
2. Follow `AGENTS.md`. This skill produces a report and changes nothing.
3. The deterministic gates already cover path existence and structural signals. Audit what they cannot: semantic drift, duplicated facts across documents, and stale rationale.
4. For every finding give the file, the line, the claim, and the contradicting evidence as file:line.
5. Rank findings by how wrong a future session would act on believing them.

---
name: full-feature-cdx
description: Orchestrate a full-stack change where both backend and frontend files are edited, then cross-verify the API-to-UI boundary. Use for new pages, new endpoints with their consuming screens, and any request that spans server and client.
---

# Full-stack feature for Codex

1. Follow `AGENTS.md` and run the mandatory workflow through `$feature-workflow-cdx` first. This skill covers execution after plan approval.
2. Read only `.claude/skills/full-feature/SKILL.md` for additional shared project detail.
3. Split the approved plan by file ownership so backend and frontend work never edit the same file. Declare the ownership split before starting.
4. A backend route without its consuming React component is an invisible orphan, not a finished feature. Both sides land in the same task.
5. Cross-verify the boundary before claiming completion: the API response shape must match what the frontend actually destructures, field by field, including null and empty cases.
6. Report exact commands, exit codes, and any check not run.

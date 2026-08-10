---
name: lazy-debt
description: >
  Harvest every `lazy:` comment in the codebase into a debt ledger, so the
  deliberate shortcuts and deferrals lazy mode leaves behind get tracked
  instead of rotting into "later means never". Use when the user says "lazy
  debt", "/lazy-debt", "what did we defer", "list the shortcuts", "debt
  ledger", or "what did we mark to do later". One-shot report, changes nothing.
---

Every deliberate lazy-mode shortcut is marked with a `lazy:` comment naming
its ceiling and upgrade path. This collects them into one ledger so a deferral
can't quietly become permanent.

## Scan

Grep the repo for comment markers, skipping `node_modules`, `.git`, and build
output:

`grep -rnE '(#|//) ?lazy:' .`  (add other comment prefixes if your stack uses them)

Each hit is one ledger row. The comment prefix keeps prose that merely mentions
the convention out of the ledger.

## Output

One row per marker, grouped by file:

`<file>:<line>, <what was simplified>. ceiling: <the limit named>. upgrade: <the trigger to revisit>.`

The convention is `lazy: <ceiling>, <upgrade path>`, so pull the ceiling
and the trigger straight from the comment. Want an owner per row too? add
`git blame -L<line>,<line>`.

Flag the rot risk: any `lazy:` comment that names no upgrade path or
trigger gets a `no-trigger` tag, those are the ones that silently rot.

End with `<N> markers, <M> with no trigger.` Nothing found: `No lazy: debt. Clean ledger.`

## Boundaries

Reads and reports only, changes nothing. To persist it, ask and it writes the
ledger to a file (e.g. `LAZY-DEBT.md`). One-shot. "stop lazy-debt" or
"normal mode" to revert.

## 기록

끝나면 `python -X utf8 -m kernel.maintenance --stamp lazy-debt` 를 돌리고 `harness_maintenance.json` 을 커밋한다. 이 기록이 다음 주기의 기준점이다 — 안 남기면 다음 세션이 또 돌린다.

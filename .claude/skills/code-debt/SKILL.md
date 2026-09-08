---
name: code-debt
description: >
  Harvest every `debt:` comment in the codebase into a debt ledger, so the
  deliberate shortcuts and deferrals code master leaves behind get tracked
  instead of rotting into "later means never". Use when the user says "code
  debt", "/code-debt", "what did we defer", "list the shortcuts", "debt
  ledger", or "what did we mark to do later". One-shot report, changes nothing.
---

> 담는 것: `debt:` 부채 수확과 원장 서식. 담지 않는 것: 과잉설계 탐지(→ code-trim·code-audit). 읽는 시점: 월 1회 부채 수확 또는 [정비] 알림 시.

Every deliberate code-mode shortcut is marked with a `debt:` comment naming
its ceiling and upgrade path. This collects them into one ledger so a deferral
can't quietly become permanent.

## Scan

Grep the repo for comment markers, skipping `node_modules`, `.git`, and build
output:

`grep -rnE '(#|//) ?debt:' .`  (add other comment prefixes if your stack uses them)

Each hit is one ledger row. The comment prefix keeps prose that merely mentions
the convention out of the ledger.

## Output

One row per marker, grouped by file:

`<file>:<line>, <what was simplified>. ceiling: <the limit named>. upgrade: <the trigger to revisit>.`

The convention is `debt: <ceiling>, <upgrade path>`, so pull the ceiling
and the trigger straight from the comment. Want an owner per row too? add
`git blame -L<line>,<line>`.

Flag the rot risk: any `debt:` comment that names no upgrade path or
trigger gets a `no-trigger` tag, those are the ones that silently rot.

End with `<N> markers, <M> with no trigger.` Nothing found: `No debt: debt. Clean ledger.`

## Boundaries

Reads and reports only, changes nothing. To persist it, ask and it writes the
ledger to a file (e.g. `CODE-DEBT.md`). One-shot. "stop code-debt" or
"normal mode" to revert.

## 기록

끝나면 `python -X utf8 -m kernel.maintenance --stamp code-debt` 를 돌리고 `harness_maintenance.json` 을 커밋한다. 이 기록이 다음 주기의 기준점이다 — 안 남기면 다음 세션이 또 돌린다.

---
name: lazy-debt
description: >
  Harvest every `lazy:` comment in the codebase into a debt ledger, so the
  deliberate shortcuts and deferrals lazy mode leaves behind get tracked
  instead of rotting into "later means never". Use when the user says "lazy
  debt", "/lazy-debt", "what did we defer", "list the shortcuts", "debt
  ledger", or "what did we mark to do later". One-shot report, changes nothing.
---

# lazy-debt — lazy 마커 부채 장부

> 담는 것: 코드에 남은 `lazy:` 마커를 긁어 장부로 만드는 스캔·출력 규칙. 담지 않는 것: 마커를 남기는 기준(→ `.claude/hooks/lazy-persona.md`). 읽는 시점: 미뤄둔 것·단축한 것의 목록 요청 시.

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

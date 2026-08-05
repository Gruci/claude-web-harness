---
name: lazy-audit
description: >
  Whole-repo audit for over-engineering. Like lazy-review, but scans the
  entire codebase instead of a diff: a ranked list of what to delete, simplify,
  or replace with stdlib/native equivalents. Use when the user says "audit this
  codebase", "audit for over-engineering", "what can I delete from this repo",
  "find bloat", "lazy-audit", or "/lazy-audit". One-shot report, does
  not apply fixes.
---

# lazy-audit — 레포 전역 과설계 감사

> 담는 것: 레포 전체에서 잘라낼 것을 순위로 뽑는 태그와 출력 형식. 담지 않는 것: diff 범위 리뷰(→ `.claude/skills/lazy-review/SKILL.md`)·정확성/보안/성능 리뷰. 읽는 시점: 레포 전체에서 지울 것을 찾아달라는 요청 시.

lazy-review, repo-wide. Scan the whole tree instead of a diff. Rank
findings biggest cut first.

## Tags

Same as lazy-review:

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

## Hunt

Deps the stdlib or platform already ships, single-implementation interfaces,
factories with one product, wrappers that only delegate, files exporting one
thing, dead flags and config, hand-rolled stdlib.

## Output

One line per finding, ranked: `<tag> <what to cut>. <replacement>. [path]`.
End with `net: -<N> lines, -<M> deps possible.` Nothing to cut: `Lean already. Ship.`

## Boundaries

Scope: over-engineering and complexity only. Correctness bugs, security holes,
and performance are explicitly out of scope. Route them to a normal review
pass. Lists findings, applies nothing. One-shot.
"stop lazy-audit" or "normal mode" to revert.

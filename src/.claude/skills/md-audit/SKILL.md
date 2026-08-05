---
name: md-audit
description: 월간 MD 드리프트 감사 — 정본 MD의 서술 vs 코드 실물 전수 대조, 발견분은 보고서로만 (자동 수정 금지)
---

# md-audit — MD ↔ 코드 드리프트 감사

> 담는 것: 정본 MD의 의미 서술이 코드 실물과 어긋났는지 대조하는 감사 절차. 담지 않는 것: MD 작성 규칙 자체(→ `dev/MD_STANDARD.md`)와 기계 검사분(→ 게이트 ④). 읽는 시점: 월 1회 MD 드리프트 감사 요청 시.

> 산문(의미 서술) 부패는 static_check 게이트로 못 잡는다. 이 감사가 상한선이다.
> 경로 실존·배치표·.env 키는 게이트 ④(`python static_check.py --full`)가 자동 검사하므로 여기서 중복하지 않는다 — **이 감사의 대상은 게이트가 못 잡는 의미 서술**이다.

## 실행 절차

1. **게이트 ④ 선실행**: `python static_check.py --full` — 기계 검사분(경로·배치표·env)을 먼저 소거.
2. **대상 MD**: CLAUDE.md · DEVGUIDE.md · dev/*.md · db/DB.md · web/WEB.md · frontend/FRONTEND.md · design/*.md · 각 도메인 MD (docs/tasks/·archive 제외).
3. **병렬 팬아웃**: 읽기 전용 에이전트(Sonnet) 4~6개로 MD 그룹 분담. 각 에이전트 지시:
   - MD의 **모든 사실 주장**(함수 소속·시그니처·동작 서술·파일 구조·개수·캐시 정책·필드명)을 코드 실물 Read/Grep으로 대조.
   - 판정: 정확 / stale(코드가 변했는데 MD 미갱신) / 적극적 오류(처음부터 틀림) / 누락(코드에 있는데 MD에 없어 혼동 유발).
   - **오진 방지**: "형제 관례 파일 수" 증거 수집 — 한 파일만 보고 관례 위반이라 단정 금지.
   - **아무것도 수정 금지** — 발견만.
4. **보고서 산출**: `docs/tasks/md_audit_findings_YYYY-MM.md` — 파일별 findings(현재 잘못된 문장 인용 + 교정 방향), 숫자 요약.
5. **자동 수정 금지** — 보고서를 사용자에게 보여주고 수정 여부·범위는 사용자가 결정한다.

## 근거

- 전수감사에서 26개 MD 91건 드리프트 발견 (정본: docs/tasks/archive/2026-07-16-codebase-audit-refactor/md_audit_findings.md).
- 재발 방지 3층: ①손사본 금지(코드 사실은 포인터로) ②게이트 ④(기계 검사) ③이 월간 감사(의미 서술).

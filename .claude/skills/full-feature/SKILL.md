---
name: full-feature
description: 풀스택 기능 구현 오케스트레이터 — backend + frontend 에이전트를 병렬 실행하고 qa 에이전트로 통합 검증한다. "화면이랑 API 같이 만들어줘"·"페이지 새로 추가해줘"·"풀스택으로 구현해줘" 류의 백엔드·프론트 양쪽 파일이 모두 편집 대상인 요청, 그리고 "그 기능 다시 실행"·"이전 결과 기반으로 보완"·"프론트만 다시" 같은 후속 요청 시 반드시 이 스킬을 사용할 것.
---

# full-feature — 풀스택 오케스트레이터

> **모델 배분**: Phase 0~1(컨텍스트 확인·요구사항 분해·인터페이스 확정)과 선행 리서치·계획은 메인 루프(Opus 5)가 직접 수행. Phase 2~3의 하위 에이전트(backend·frontend·qa)는 model을 지정하지 않는다 — 각 에이전트 frontmatter가 정본이다. 스킬에서 model을 덮어쓰면 정본과 어긋난다 (CLAUDE.md 모델 라우팅).

**실행 모드: 서브 에이전트 (병렬)** — Phase 1에서 공유 인터페이스를 먼저 확정하므로 에이전트 간 실시간 통신이 구조적으로 불필요하다(결과만 수집). 팀 통신 오버헤드 > 이득 → 서브 에이전트 패턴 채택.

**데이터 전달: 반환값 기반(결과 수집) + 파일 기반(plan.md가 공유 스펙 문서 역할).**

## Phase 0: 컨텍스트 확인

- `docs/tasks/`에 기존 research/plan 존재 + 부분 수정 요청 → **부분 재실행**: 해당 에이전트만 재호출 (예: "프론트만 다시" → frontend만)
- 기존 산출물 존재 + 새 기능 → 기존 파일 archive 처리 후 새 실행
- 없음 → 초기 실행. 기능 규모가 크면 먼저 `/feature-workflow`의 리서치·계획 단계를 거친 후 이 스킬의 Phase 2로 진입.

## Phase 1: 요구사항 분해 + 인터페이스 확정

1. 기능을 **백엔드 태스크**와 **프론트엔드 태스크**로 분리한다.
2. **공유 인터페이스를 먼저 확정한다**: API 경로·메서드·응답 스키마(키 이름·타입·중첩 구조)·파라미터명.
3. **화면 작업이 포함되면 반응형 설계표도 함께 확정한다**: 화면·컴포넌트별 데스크톱·모바일 배치 + 전환 방식 (`design/RESPONSIVE.md`).
4. 인터페이스 확정 없이 병렬 실행하면 키 이름 불일치가 생기므로 이 단계를 건너뛰지 않는다.
5. 두 에이전트의 편집 대상 파일이 겹치지 않는지 확인 (겹치면 순차 실행으로 전환).

## Phase 2: 병렬 실행

아래 두 에이전트를 **동시에** 호출한다 (Agent 도구, `run_in_background: true`).

### backend 에이전트 지시 템플릿
```
[backend 에이전트]
기능: <기능명>
대상 파일: <db/reads/xxx.py>, <web/routes/xxx.py>
API 경로: <GET|POST /api/xxx>
응답 스키마: { "<key>": "<type>", ... }   ← Phase 1 확정본 그대로
작업: EDITING.md 잠금 → 편집 → 게이트 통과 → 잠금 해제 → 관련 MD 갱신
```

### frontend 에이전트 지시 템플릿
```
[frontend 에이전트]
기능: <기능명>
대상 파일: <frontend/src/pages/Xxx.tsx>, <components/xxx/>
API 엔드포인트: <GET /api/xxx> (backend 에이전트가 구현)
응답 키: <key1>, <key2>   ← Phase 1 확정본 그대로
반응형: <반응형 설계표 원문>   ← Phase 1 확정본 그대로 (design/RESPONSIVE.md 준수)
작업: DESIGN_GUIDE 준수 → 편집 → typecheck 통과 → 해당 design/ 서브MD 갱신
```

## Phase 3: 통합 검증 (qa 에이전트)

두 에이전트 완료 후 **qa 에이전트**(`subagent_type: "qa"`)를 호출한다:
```
[qa 에이전트]
검증 대상: <이번에 추가된 API·컴포넌트 목록>
Phase 1 확정 인터페이스: <스키마 원문>
작업: API 응답 shape ↔ 프론트 소비 코드 교차 대조 + orphan 검출 + pytest·typecheck 실행
```

qa 보고의 ❌ 불일치 항목 → 해당 에이전트에 수정 재지시 → qa 재검증 (불일치 0까지).

## Phase 4: 마무리

1. **`/lazy-review` 자동 실행** — 이번 변경 diff 과잉설계 검토, 발견분은 그 자리에서 반영 후 재검증
2. EDITING.md Active Edits 비어있는지 확인
3. 관련 MD 업데이트 완료 확인 (CLAUDE.md 라우팅·모듈 소유권 표 포함)
4. `python -X utf8 -m kernel.runner` 최종 통과
5. docs/tasks/ 산출물 archive 이동

## 에러 핸들링

| 상황 | 처리 |
|------|------|
| 에이전트 1회 실패 | 실패 사유를 보강해 1회 재시도 |
| 재시도도 실패 | 해당 부분 제외하고 진행, 결과 보고에 누락·원인 명시 (중간에 허락 구하지 않음) |
| 편집 파일 충돌 (같은 파일) | 병렬 중단 → 순차 실행 전환 |
| qa 3회 반복에도 불일치 | 인터페이스 설계 자체 재검토 — 사용자 에스컬레이션 |

## 테스트 시나리오

- 정상: "공지사항 목록 페이지 만들어줘" → 인터페이스 확정(GET /api/notices → {items: [{id,title,created_at}]}) → backend·frontend 병렬 → qa 대조 통과 → archive
- 에러: frontend가 `createdAt`으로 참조, backend는 `created_at` 반환 → qa가 ❌ 보고 → frontend 수정 재지시 → 재검증 통과

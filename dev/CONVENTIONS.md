# dev/CONVENTIONS.md — 결정된 관례 레지스트리

> 담는 것: 갈림길에서 이미 결정된 관례와 공용 헬퍼 레지스트리. 담지 않는 것: 레이어 구조(→ `dev/ARCHITECTURE.md`)·이름 규칙(→ `dev/NAMING.md`)·규칙의 배경(→ `dev/LESSONS.md`). 읽는 시점: 새 파일이나 함수를 쓰기 전. 재구현 전에 헬퍼 표를 먼저 본다.

> **목적: 여러 세션의 Claude가 짜도 한 명이 짠 것처럼.**
> 운영 규칙 2줄:
> 1. **관례가 갈리는 선택을 새로 하게 되면 이 표에 등재하고, 검사 가능하면 `static_check.py`에 검사를 추가한다.**
> 2. **이 표와 코드가 충돌하면 표가 정본이다** (표를 바꾸려면 사용자 합의 후).
> 산문 금지 — 표만. 신규 파일 작성 전 이 표 + 레이어 MD의 정본 예시 파일(golden exemplar)을 읽는다.

## 백엔드

| # | 주제 | 정본 | 근거·예외 |
|---|------|------|-----------|
| B1 | get_db import | `from db.connection import get_db` 단일 경로 | 간접 경유 금지 |
| B2 | 에러 반환 | `web/routes/` = `raise HTTPException` | |
| B3 | 라우트 핸들러 | 동기 `def`. `async def`는 본문에 실제 await(SSE·to_thread·request.form) 있을 때만 | static_check 게이트 |
| B4 | 커넥션 스코프 | `with get_db()` 블록 안 = fetch만. 가공·2차 커넥션 호출 금지 | static_check 게이트 |
| B5 | env 접근 | `from settings import X` 단일 (os.getenv/os.environ 직접 금지) | static_check 게이트 |
| B6 | 진입점 모듈 | import 부작용 금지 — 실행 로직은 `main()`+`__main__` 가드 | |
| B7 | timestamp 저장 | naive 금지 — KST `+09:00` 명시 aware로 저장, cutoff 비교도 aware | |
| B8 | 숫자 정제 | 0은 유효값, NULL 변환 금지 | |
| B9 | 배치의 DB 조회 | 직접 SELECT 금지 — 전부 `db/reads/` 경유 | ARCHITECTURE 정본 |
| B10 | 신규 일별 수집 배치 | self-heal(최근 N일 갭 자가복구) 필수, run_daily 직후 호출 | 배치 도입 시 적용 |
| B11 | API 파라미터 날짜범위 | `start`/`end` | |

## 프론트엔드

| # | 주제 | 정본 | 근거·예외 |
|---|------|------|-----------|
| F1 | 데이터 fetch | `useApi`(TanStack Query 래퍼) 단일 — raw fetch 금지 | 첫 구현 시 useApi 훅부터 만든다 |
| F2 | 색상 | hex 리터럴 금지 — `constants/colors.ts` 상수 또는 CSS var. **예외 = colors.ts 자신·CSS 파일** | static_check 게이트 |
| F3 | 투명도 | 문자열 접합(`+'99'`) 금지 — `hexAlpha()` 헬퍼 | |
| F4 | 차트 래퍼 | `charts/` 래퍼 경유(기본 옵션 자동 주입). raw 차트 라이브러리 직생성 금지 | |
| F5 | 사용자 노출 텍스트 | 한국어. 결측=`'-'`. 로딩=`'불러오는 중…'`. 이모지 금지(문서화된 예외만) | |
| F6 | 컴포넌트 배치 | 페이지 전용=`components/<page>/`, 2페이지+ 공용=`components/common/` | |
| F7 | 수치 표시 | 표시 변환은 `utils/format.ts` 계열 — 페이지 로컬 fmt 재구현 금지 | |
| F8 | 대형 payload 섹션 | 첫 뷰포트 밖 수백 KB 섹션은 지연 마운트(LazySection 패턴, placeholder minHeight 필수) | 필요 시 도입 |

## 과잉설계 방지 (Lazy 래칫)

| # | 규칙 | 위반 예시 | 올바른 대안 |
|---|------|----------|------------|
| P1 | 한 곳에서만 쓰는 추상화 금지 | 1회용 제네릭 래퍼 클래스 | 인라인 또는 함수 1개 |
| P2 | stdlib로 되면 외부 dep 추가 금지 | `arrow` for 단순 날짜 | `datetime` |
| P3 | 사용하지 않는 "유연성" 파라미터 금지 | `strategy=`, `mode=` (호출부 1개) | 필요해지면 그때 추가 |
| P4 | 미래 요구사항에 대한 투기적 설계 금지 | "나중에 멀티테넌트 되면…" 분기 | 현재 요구사항만 구현 |
| P5 | 이미 있는 헬퍼 재구현 금지 | 아래 헬퍼 표·CONVENTIONS 무시하고 새로 만듦 | 기존 것 재사용 |

> Lazy 스킬 연동 (`.claude/skills/`): `/lazy-review`(diff 검토), `/lazy-audit`(전체 레포 감사), `/lazy-debt`(기술부채 추적)
>
> 의도적 단순화(알려진 상한이 있는 지름길)는 `# lazy: <상한>, <업그레이드 조건>` 주석으로 표시한다 — `/lazy-debt`가 이 마커를 수확해 부채 원장을 만든다.

## RN(네이티브 앱) 포팅 대비 (R 래칫)

> 프론트는 React 웹으로 가되, **나중에 React Native 앱으로 포팅할 때 화면층만 재작성하면 되도록** 로직·토큰을 화면에서 분리해둔다. RN에서 그대로 살아남는 것: TS 순수 로직(hooks/·utils/), 디자인 토큰 값, API 레이어. 죽는 것: HTML/CSS·브라우저 API·라우터.

| # | 규칙 | 이유 |
|---|------|------|
| R1 | **화면/로직 분리** — `.tsx` 컴포넌트는 표시(JSX)만. 데이터 가공·계산·조건 분기 로직은 `hooks/`·`utils/` 순수 TS 함수로 분리 | RN 전환 시 hooks/utils는 그대로 이동, 화면만 재작성 |
| R2 | **디자인 토큰 TS 정본** — 색·간격·타이포·z-index 값은 `constants/` TS 상수가 정본, CSS `:root` 변수는 상수에서 파생(동기 유지) | 토큰 값은 RN StyleSheet에서 그대로 재사용 |
| R3 | **브라우저 전용 API 직접 호출 금지** — `window.`·`document.`·`localStorage` 등은 `utils/platform.ts` 래퍼 경유 (첫 필요 시 생성). 불가피하면 `// web-ok: 사유` (static_check 게이트 15) | RN엔 브라우저 API가 없다 — 래퍼 한 파일만 교체하면 이식 끝 |
| R4 | **라우팅 접점 최소화** — 라우터(react-router 등) import·페이지 이동 호출은 `pages/` 레벨에서만. 하위 컴포넌트에는 콜백 prop으로 전달 | 라우터는 전환 시 통째 교체 대상 — 접점이 적을수록 싸다 |

## 공용 헬퍼 레지스트리 (동일 목적 재구현 금지 — 신설 전 이 표 확인)

> 공용 헬퍼를 만들거나 2곳+에서 같은 코드가 반복되어 승격할 때 여기 등재한다.

| 모듈 | 제공 | 소비 도메인 |
|------|------|------------|
| (첫 헬퍼 신설 시 등재) | | |

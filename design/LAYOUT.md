# design/LAYOUT.md — 레이아웃·간격·그리드

> 담는 것: 화면 골격과 간격 체계, sticky 패턴의 결정 근거. 담지 않는 것: 브레이크포인트와 모바일 전환(→ `design/RESPONSIVE.md`)·컴포넌트 내부 구조(→ `design/COMPONENTS.md`). 읽는 시점: 새 페이지 골격을 잡거나 간격이 갈릴 때.

아직 레이아웃이 없다. **새 레이아웃이나 sticky 패턴을 신설한 그 턴 안에 여기 기록한다.**

## 정해야 할 것 (첫 레이아웃 작업 시)

- [ ] 앱 셸 구조 (사이드바 / 탑바 / 콘텐츠 그리드) — 데스크톱·모바일 양쪽 (`design/RESPONSIVE.md`)
- [ ] sticky 헤더/필터 스펙 (`top` 값 계산 규칙)

> 반응형 브레이크포인트 정본은 `design/RESPONSIVE.md` (768px 단일).

## 레이아웃 원칙 (impeccable 기반)

- **간격에 리듬을 준다** — 모든 간격이 동일하면 위계가 사라짐. 관련 요소는 가깝게, 섹션 간은 넓게.
- **Flexbox = 1D, Grid = 2D** — Grid가 기본이 아님. `flex-wrap`으로 충분하면 Flexbox.
- **반응형 그리드 (브레이크포인트 없이)**: `repeat(auto-fit, minmax(280px, 1fr))`.
- **z-index 시맨틱 스케일**: dropdown → sticky → modal-backdrop → modal → toast → tooltip. 임의값(999, 9999) 금지.
- **카드는 게으른 답** — 카드가 진짜 최적 어포던스일 때만 사용. 중첩 카드는 항상 틀림.
- **오버플로 체크**: `position: absolute` 드롭다운이 `overflow: hidden/auto` 컨테이너 안에 있으면 잘림 → `<dialog>`, popover API, `position: fixed`, 또는 portal 사용.

## 규칙 (확정분)

- (첫 패턴 확정 시 기록)

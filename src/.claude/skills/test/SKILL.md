테스트 작성·실행·커버리지 점검 워크플로우. dev/TESTING.md 규칙을 자동 준수한다.

> 담는 것: 테스트 요청을 받았을 때 밟는 순서. 담지 않는 것: 계층 규칙의 근거·현행 테스트 실태(→ `dev/TESTING.md`). 읽는 시점: `/test` 호출 시.

## 트리거 조건
- "테스트 짜줘", "테스트 추가해줘"
- 버그 수정 후 회귀 방어 테스트 요청
- "pytest 돌려줘", "테스트 통과하는지 확인해줘"
- 신규 `_format_*` 또는 `_fetch_*` 함수 추가 직후
- 수집·계산 도메인에 신규 `.py` 추가 직후 — 게이트 ⑫가 행동 테스트 1개를 강제한다

## Phase 1: 계층 판단 (dev/TESTING.md 규칙)

| 대상 함수 패턴 | 테스트 타입 | Mock 여부 |
|---------------|------------|----------|
| `_format_*()` | Unit | 없음 (순수 함수) |
| `_fetch_*()` | Integration | 없음 (Test DB) |
| `kofia/`, `businfo/`, `news/` | Mock | HTTP만 |

**금지**: 내부 모듈 간 Mock (`_fetch_*` mock 후 `get_*` 테스트 금지)

## Phase 2: 파일 위치 결정

현행 `tests/` 는 flat 배치 + `unit/` 하위뿐이다. `integration/`·`mock/` 3분할은 **미도입** — 그 경로에 새 파일을 만들지 말 것. 배치 실태와 exemplar 는 `dev/TESTING.md` §3 이 정본, 파일 목록은 `Glob tests/**/test_*.py`.

## Phase 3: 테스트 실행

```bash
python -m pytest tests/ -x -q            # 전체 (CI 기본)
python -m pytest tests/unit/ -x -q       # unit 만
python -m pytest tests/test_rss_sources.py -v   # 파일 단위
```

`@pytest.mark.integration` 은 마커 설정 자체가 없어 동작하지 않는다 — `-m integration` 을 쓰지 말 것.

## Phase 4: 검증 기준

- 신규 `_format_*` → Unit Test 필수 (확정 즉시)
- 버그 수정 → 해당 케이스 재현 테스트 먼저 추가 → 수정 → 통과 확인
- 수집·계산 도메인 신규 모듈 → 게이트 ⑫ 통과 확인 (`python static_check.py`)

## 주의사항
- 자주 바뀌는 WIP 코드에는 테스트 작성 금지 (확정된 순수 함수부터)
- 계산 로직(점유율, CAGR, 전월대비)은 `_format_*` Unit Test에서만 집중 검증
- 외부 HTTP 는 `monkeypatch` 로 클라이언트 함수를 스텁한다 — `responses` 패키지는 의존성이 아니다

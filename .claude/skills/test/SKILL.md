---
name: test
description: 테스트 작성·실행·커버리지 점검 워크플로우. "테스트 짜줘"·"테스트 추가해줘"·"pytest 돌려줘"·"테스트 통과하는지 확인해줘"·버그 수정 후 회귀 방어 테스트 요청·신규 _format_*/_fetch_* 함수 추가 직후에 반드시 이 스킬을 사용할 것. dev/TESTING.md 규칙을 자동 준수한다.
---

# test — 테스트 워크플로우

## Phase 1: 계층 판단 (dev/TESTING.md 규칙)

| 대상 함수 패턴 | 테스트 타입 | Mock 여부 |
|---------------|------------|----------|
| `_format_*()` | Unit | 없음 (순수 함수) |
| `_fetch_*()` | Integration | 없음 (Test DB) |
| 외부 수집 클라이언트 | Mock | HTTP만 (monkeypatch) |

**금지**: 내부 모듈 간 Mock (`_fetch_*` mock 후 `get_*` 테스트 금지)

## Phase 2: 파일 위치 결정

```
tests/
├── conftest.py    # 세션 TestClient + 공용 픽스처
├── fixtures/      # 정적 응답 픽스처 (실제 HTML/JSON)
├── test_*.py      # flat 배치 (초기)
└── unit/          # 순수 함수 unit (테스트가 늘면 분리)
```

## Phase 3: 테스트 실행

```bash
python -m pytest tests/ -x -q                  # 전체
python -m pytest tests/unit/ -v                # unit만
python -m pytest tests/test_xxx.py -v          # 특정 파일
```

## Phase 4: 검증 기준

- 신규 `_format_*` → Unit Test 필수 (로직 확정 즉시)
- 버그 수정 → 해당 케이스 **재현 테스트 먼저 추가** → 수정 → 통과 확인
- 외부 파싱 코드 → 실제 응답 픽스처 기반 회귀 테스트

## 주의사항

- 자주 바뀌는 WIP 코드에는 테스트 작성 금지 (확정된 순수 함수부터)
- 계산 로직(비율·증감·집계)은 `_format_*` Unit Test에서만 집중 검증

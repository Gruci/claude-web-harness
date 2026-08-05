# dev/TESTING.md — 테스트 전략 & 작성 규칙

> 담는 것: 무엇을 어떤 계층으로 테스트하는지의 규칙과 게이트 ⑫ 계약. 담지 않는 것: 테스트 파일 목록(→ `Glob tests/**/test_*.py`)·`/test` 실행 순서(→ `.claude/skills/test/SKILL.md`). 읽는 시점: 테스트를 쓰거나 수집·계산 모듈을 새로 만들기 전.

기능이 안정화될 때마다 해당 계층의 테스트를 추가한다. 기존 코드의 백필은 급하지 않지만, **신규 수집/계산 모듈은 §0 게이트 ⑫가 강제한다.**

---

## 0. 게이트 ⑫ — 수집/계산 모듈 행동 테스트 짝 (2026-07-27)

> 배경: 도메인 모듈 78개 중 테스트 5개(2026-07-27 전수조사). 형식 게이트(400줄·타입힌트·레이어)는
> 완성됐으나 행동 버그(naive timestamp 9시간 밀림·zero→NULL 둔갑·보조 소스 silent failure)는
> 전부 프로덕션에서 발견됐다. 형식이 아니라 **행동**을 잠그는 게이트.

- 대상: `kofia/ etf/ news/ dart/ businfo/ macro/ us_cycle/ kr_cycle/ analyst_reports/`
  `market_briefing/ dept_issues/ batches/` 의 신규 `.py` (`db/`·`web/`·`frontend/` 는 스코프 밖).
- 요구: **"이 로직이 깨지면 실패하는 테스트 1개"** — 없으면 `static_check.py` 위반 → 세션 종료 불가.
  매칭은 `tests/**/test_*.py` 파일명에 모듈 stem 포함 여부(`test_market_briefing_collector.py` ← `collector.py`).
- 테스트 형태 정본(exemplar): `tests/unit/test_institution_sources_parsers.py`
  (실HTML 픽스처 + HTTP 계층만 monkeypatch + raw=0 카나리아),
  `tests/unit/test_market_briefing_collector.py` (순수 로직 dict 직구성 + 네거티브 페어링).
- 기존 무테스트 모듈 75건은 `static_check_tests_baseline.txt` 에 동결 — **줄어들기만 해야 한다(래칫)**.
  백필은 별도 과업. 신규 등재는 불가피한 사유를 `#` 주석으로 병기할 때만.
- 파일명 매칭이라 "테스트가 실제로 그 모듈을 import 하는지"까지는 안 본다 — 이름만 맞춘 빈 테스트는
  게이트가 아니라 리뷰(2-1단계)와 exemplar 모방이 막는다. 게이트는 하한선이지 목표가 아니다.

---

## 1. 3-레이어 → 테스트 타입 매핑

`ARCHITECTURE.md`의 계층 구분을 그대로 테스트에 적용한다.

| 레이어 | 함수 패턴 | 테스트 타입 | Mocking | 속도 |
|--------|-----------|-------------|---------|------|
| Logic  | `_format_*()` | Unit | 없음 (순수 함수) | 즉시 |
| I/O    | `_fetch_*()` | Integration | 없음 (Test DB) | 보통 |
| 외부   | `kofia/api.py`, `businfo/`, `news/` | Mock | HTTP만 | 빠름 |
| Public | `get_*()` | (선택적 E2E) | I/O만 제한 | 느림 |

---

## 2. 핵심 규칙

### 2-1. `_format_*` 은 반드시 순수 Unit Test
- DB·API 연결 없이 `dict / list` 인자만으로 검증
- 계산 로직(점유율, CAGR, 전월대비 증감) 은 **여기서만** 집중 테스트
- 기능 안정화되는 순간 작성 → 이후 리팩터 시 회귀 방어선

### 2-2. Mock at the edges
- **금지**: 프로젝트 내부 모듈 간 Mocking (`_fetch_*` 를 mock 해서 `get_*` 테스트 하는 것 등)
- **허용**: 외부 HTTP (`kofia`, `businfo`, `news`), 시스템 시각 (`datetime.now`)

### 2-3. 앱 레벨 테스트는 `TestClient` 사용 (Docker Postgres·integration 마커는 미도입)
- `tests/conftest.py`의 세션 픽스처 `client` 가 `DATABASE_URL=sqlite:///:memory:`·더미 `ADMIN_PASSWORD/SECRET` 을 주입하고 `TestClient(app, raise_server_exceptions=False)` 로 앱 전체를 노출
- 현재 테스트는 **DB 미의존 경로(라우팅·인증·HMAC 세션·파서)** 위주 — 실제 Postgres 스키마를 띄우는 통합 테스트는 없음
- Docker Compose Test DB·트랜잭션 롤백 픽스처·`@pytest.mark.integration` 마커는 **미도입**(이 문서 §3의 계층형 구조는 향후 뼈대 제안)

### 2-4. Fixtures는 `tests/fixtures/` 에 보관
- 현재는 기관 공고 크롤 파서용 **실제 HTML 픽스처**(`tests/fixtures/institution_pages/*.html`)가 정본 — 파서 회귀 방어선
- 같은 데이터를 여러 테스트가 재사용 → 코드 중복 방지

---

## 3. 어디에 두는가 — 현행 배치

목록은 `Glob tests/**/test_*.py`. 여기 적는 건 그 목록으로 알 수 없는 것뿐이다.

| 위치 | 무엇이 사는가 |
|------|--------------|
| `tests/` (flat) | 앱 레벨 TestClient 테스트. 접두 `test_` 만으로 구분한다 |
| `tests/unit/` | 순수 로직·파서 unit. 게이트 ⑫가 요구하는 신규 모듈 테스트는 여기 |
| `tests/fixtures/` | 실 HTML 픽스처. 라이브 응답 저장본이라 파서 회귀의 방어선 |
| `tests/conftest.py` | 세션 `TestClient` + `admin_cookie`·member 세션 헬퍼 |

> ⚠️ `integration/`·`mock/` 3분할은 **아직 미도입** — 그 경로에 새 파일을 만들지 말 것. 향후 테스트가 늘면 잡을 뼈대 제안이다.

---

## 4. 형태는 exemplar 를 모방한다

샘플 코드를 여기 적어두지 않는다. 손사본은 실물과 갈라지고, 이 파일에 있던 예제는 실제로 존재하지 않는 픽스처(`test_db_session`)와 미도입 마커를 가르치고 있었다. **실물 테스트 2개가 정본**이다:

| exemplar | 가르치는 형태 |
|---|---|
| `tests/unit/test_institution_sources_parsers.py` | 실 HTML 픽스처 + HTTP 계층만 monkeypatch + `raw=0` 카나리아 |
| `tests/unit/test_market_briefing_collector.py` | 순수 로직 dict 직구성 + 네거티브 페어링 |

- 외부 HTTP 는 `monkeypatch` 로 클라이언트 함수를 스텁한다 — `responses` 패키지는 **의존성이 아니다**.
- 픽스처 저장 스크립트는 `scripts/save_institution_fixtures.py`(라이브 GET → `tests/fixtures/`).

---

## 5. pytest 설정 — 없다

`pyproject.toml`·`pytest.ini` 등 설정 파일이 없다. 즉 **마커도 `addopts` 도 미설정**이라 `@pytest.mark.integration` 이나 `-m integration` 은 동작하지 않는다. 통합/유닛 분리가 실제로 필요해지는 시점에 설정 파일을 만든다.

```bash
pytest                              # tests/ 전체
pytest tests/unit/                  # unit 디렉토리만
pytest tests/test_rss_sources.py    # 파일 단위 선택
```

---

## 6. 언제 테스트를 추가하는가

| 시점 | 대상 |
|------|------|
| **수집/계산 도메인 신규 모듈 작성 시** | **행동 테스트 1개 — 게이트 ⑫ 강제(§0), plan 2단계에서 미리 설계** |
| `_format_*` 함수 로직 확정 시 | Unit Test 즉시 작성 |
| DB 스키마 확정 후 | Integration Test |
| KOFIA 파싱 코드 변경 시 | Mock Test 업데이트 |
| 버그 수정 시 | 해당 케이스 재현 테스트 추가 후 수정 |

> 기능 개발 중 자주 바뀌는 코드에는 테스트를 쓰지 않는다.  
> 확정된 순수 함수부터 시작한다.

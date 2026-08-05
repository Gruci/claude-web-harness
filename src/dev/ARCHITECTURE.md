# dev/ARCHITECTURE.md — 3-레이어 아키텍처 & 함수 명명

> 담는 것: 레이어 경계 계약 · I/O와 로직 분리 규칙 · 새 파일이 모방할 정본 예시. 담지 않는 것: 이름 규칙 상세(→ `dev/NAMING.md`)·갈림길 선택(→ `dev/CONVENTIONS.md`)·파일 목록(→ `Glob`). 읽는 시점: `.py` 파일을 새로 만들거나 DB 접근 코드를 고치기 전.

---

## 읽기/쓰기 레이어 분리 (필수)

DB 접근은 **읽기와 쓰기를 디렉토리로 분리**한다.

| 디렉토리 | 역할 | 함수 prefix |
|----------|------|-------------|
| `db/reads/` | **읽기 전용** — SELECT 조회 | `get_*` / `_fetch_*` / `_format_*` |
| `db/writes/` | **쓰기 전용** — INSERT/UPDATE/DELETE/commit | `save_*` / `upsert_*` / `set_*` / `delete_*` / `refresh_*` / `map_*` / `log_*` |

- `db/reads/*.py`에 쓰기(INSERT/UPDATE/DELETE/commit) 금지 → 도메인별 `db/writes/*.py`로. **역도 금지** — 순수 SELECT 함수를 writes에 두지 말 것(2026-07-16 `check_agg_consistency`→reads 이관 사례).
- `db/writes/`가 `db/reads/`를 import(읽기 의존)하는 것은 OK. **역방향(reads → writes) 금지** — 공용 shim의 모듈 스코프 writes import를 통한 간접 경유도 금지(2026-07-16 db/core 사례. get_db는 `from db.connection import` 단일 — CONVENTIONS B1·게이트 ⑤).
- 도메인별 파일: `db/writes/{도메인}.py` (예: `ontology`·`etf`·`news`·`kofia` 등 — 전체 목록은 `Glob db/writes/*.py`).
- **배치의 DB 조회도 db/reads/ 경유**: gap-detection 등 배치 전용 쿼리는 `db/reads/{도메인}_gaps.py` 류 전용 모듈 신설(정본 예시: `equity_gaps.py`). 배치 파일 내 인라인 SELECT 금지(CONVENTIONS B13).

## 3-레이어 아키텍처 (필수)

모든 Python 코드는 아래 3계층을 엄격히 분리한다. **계층 간 I/O와 로직을 절대 혼합하지 않는다.**

| 레이어 | 명명 | 역할 |
|--------|------|------|
| I/O | `_fetch_*()` | DB/API 조회만, raw rows 그대로 반환, 가공 없음 |
| Logic | `_format_*()` | 순수 변환, I/O 없음, dict/list 조립만, 단위 테스트 가능 |
| Public | `get_*()` | fetch + format 조합, 외부 진입점 |

**적용 스코프 (2026-07-16 실태 성문화 — CONVENTIONS B11·B12):**
- `_fetch_/_format_/get_` 3함수 분할 = **db/reads 복잡 조회·배치 파이프라인**에 적용. 단순 조회(단일 SQL→dict 변환)는 `get_*` 단일 함수 + "fetch는 with 블록 안, 가공은 블록 밖"(핵심규칙 5·6)만 지키면 충분.
- **수집 클라이언트**(kofia/news/etf/dart/businfo/market_briefing 스크레이퍼)는 fetch+parse 단일 public 함수가 정착 관례 — 3분할 강제하지 않음. 단 파서 로직이 커져 단위 테스트가 필요해지면 분리.
- **KRX/pykrx 계열 고빈도 per-ticker 배치**는 `collect→upsert` 2단계 허용(수천 티커 메모리 트레이드오프, 정본 예시: `batches/equity/collectors.py`). 그 외 배치는 3단계(정본 예시: `batches/news_batch.py`).
- 어느 경우든 **핵심규칙 5(커넥션 범위)는 전 코드 예외 없음** — static_check 게이트 ① 강제.

### 핵심 규칙

1. **클로저 금지**: `async def` 안에 `def` 중첩 금지 → 모듈 수준 추출, 의존성은 파라미터로 전달
2. **I/O와 로직 분리**: DB 조회 함수 안에 계산/변환 로직 금지
3. **파이프라인 패턴**: 배치는 `fetch → process → persist` 3단계 독립 함수
4. **타입 힌트**: 모든 public + `_fetch_*`/`_format_*` 함수에 파라미터 + 반환 타입 필수
5. **커넥션 범위**: `_fetch_*` 안에서만 열고 dict 변환 후 반환 — `_format_*`까지 열려 있으면 안 됨
6. **라우트 핸들러는 `def`(동기)** ★: DB 레이어가 동기 `psycopg2`라, 라우트 핸들러를 `async def`로 쓰면 이벤트루프가 쿼리 동안 막혀 **동시 요청이 직렬화**된다. → **동기 `def`로 선언**(FastAPI 가 threadpool 에서 병렬 실행). `await`가 실제 필요한 핸들러만(`await request.form()`·`await asyncio.to_thread(...)`·SSE 스트림) `async def`. 멀티워커(`uvicorn --workers 4`)는 워커당 풀(maxconn 15) → anyio threadpool 한도 14(`web/app.py` lifespan)로 `PoolError` 방지. (2026-06-10 전환: 113개 핸들러 async→def)

### 함수 명명 패턴

```python
# db/reads/*.py
def _fetch_dashboard_raw(basis: str) -> dict | None:    # I/O: DB 조회만
def _format_dashboard_response(raw: dict) -> dict:      # Logic: 순수 변환
def get_dashboard_data(basis: str = "NAV") -> dict:     # Public: 조합

# batches/*.py
def fetch_all_news(...) -> list:      # 1단계: I/O
def process_articles(...) -> list:   # 2단계: Logic (AI 분석 등)
def persist_and_notify(...) -> int:  # 3단계: Side Effects (저장+알림)
def run(...):                        # Orchestrator: 3단계 조합

# web/routes/*.py
def _merge_region_timeseries(...) -> dict:  # 모듈 수준 헬퍼 (클로저 금지)
def api_dashboard(...) -> dict:             # 엔드포인트: 동기 def(rule 6), 헬퍼 조합만
```

### 올바른 패턴 vs 금지 패턴

```python
# ✅ 올바른 패턴
def _fetch_cat_summary_raw(basis, regions) -> dict | None:
    with get_db() as conn:
        rows = conn.execute(...).fetchall()
    return {"rows": [dict(r) for r in rows]}   # 커넥션 닫힌 후 반환

def _format_cat_summary(raw: dict) -> dict:    # I/O 없음
    for r in raw["rows"]: ...
    return result

def get_cat_summary(...) -> dict:              # 조합만
    raw = _fetch_cat_summary_raw(...)
    return {} if raw is None else _format_cat_summary(raw)

# ❌ 금지 패턴 — 커넥션 열린 채로 변환 로직
def get_cat_summary(...):
    with get_db() as conn:
        rows = conn.execute(...).fetchall()
        result = {}
        for r in rows:
            result[r["cat"]] = r["합계"] * 1e-8   # ← 금지
    return result
```

## 정본 예시 파일 (golden exemplar) — 새 파일은 이 파일을 Read 후 모방 (임의 형제 선택 금지)

| 만들려는 것 | 모방할 정본 |
|-------------|-------------|
| db/reads 단순 조회 모듈 | `db/reads/member_auth.py` |
| db/reads 복잡 조회(3분할) | `db/reads/dashboard.py` |
| db/reads 배치용 gap 조회 | `db/reads/equity_gaps.py` |
| db/writes 도메인 모듈 | `db/writes/macro.py` (bulk_upsert 경유) / 트랜잭션·감사로그 동반 CRUD는 `db/writes/dept_issues.py` |
| web/routes API 모듈 | `web/routes/ranking.py` |
| web/admin 라우트 모듈 | `web/admin/theme_rules_routes.py` |
| 일별 수집 배치(3단계+self-heal) | `batches/news_batch.py` |
| 고빈도 per-ticker 배치(2단계) | `batches/equity/collectors.py` |
| 외부 수집 클라이언트 | `dart/client.py` |
| React 페이지 | `frontend/src/pages/Bond.tsx` |
| React admin pane | `frontend/src/components/admin/salesStatus/` 구성 |
| 차트 소비 컴포넌트 | `frontend/src/components/issues/DivisionChip.tsx` (라인+마커) |

프론트 갈림길(색·fetch·interaction 등)과 공용 헬퍼 목록의 정본은 `dev/CONVENTIONS.md`.

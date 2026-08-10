# dev/ARCHITECTURE.md — 3-레이어 아키텍처 & 함수 명명

> 담는 것: 레이어 경계와 의존성 방향, I/O와 로직을 가르는 함수 명명 규칙. 담지 않는 것: 변수·필드 이름 규칙(→ `dev/NAMING.md`)·테이블 설계(→ `dev/DATA_MODEL.md`). 읽는 시점: 새 `.py` 파일이나 함수를 만들기 전, 그리고 어느 레이어에 둘지 갈릴 때.

---

## 읽기/쓰기 레이어 분리 (필수)

DB 접근은 **읽기와 쓰기를 디렉토리로 분리**한다.

| 디렉토리 | 역할 | 함수 prefix |
|----------|------|-------------|
| `db/reads/` | **읽기 전용** — SELECT 조회 | `get_*` / `_fetch_*` / `_format_*` |
| `db/writes/` | **쓰기 전용** — INSERT/UPDATE/DELETE/commit | `save_*` / `upsert_*` / `set_*` / `delete_*` / `refresh_*` / `log_*` |

- `db/reads/*.py`에 쓰기(INSERT/UPDATE/DELETE/commit) 금지 → 도메인별 `db/writes/*.py`로. **역도 금지** — 순수 SELECT 함수를 writes에 두지 말 것.
- `db/writes/`가 `db/reads/`를 import(읽기 의존)하는 것은 OK. **역방향(reads → writes) 금지.**
- 도메인별 파일: `db/writes/{도메인}.py`, `db/reads/{도메인}.py`.
- **배치·스크립트의 DB 조회도 `db/reads/` 경유** — 파일 내 인라인 SELECT 금지. 배치 전용 쿼리(갭 탐지 등)는 `db/reads/{도메인}_gaps.py` 류 전용 모듈 신설.

## 3-레이어 아키텍처 (필수)

모든 Python 코드는 아래 3계층을 엄격히 분리한다. **계층 간 I/O와 로직을 절대 혼합하지 않는다.**

| 레이어 | 명명 | 역할 |
|--------|------|------|
| I/O | `_fetch_*()` | DB/API 조회만, raw rows 그대로 반환, 가공 없음 |
| Logic | `_format_*()` | 순수 변환, I/O 없음, dict/list 조립만, 단위 테스트 가능 |
| Public | `get_*()` | fetch + format 조합, 외부 진입점 |

**적용 스코프:**
- 3함수 분할 = **db/reads 복잡 조회·배치 파이프라인**에 적용. 단순 조회(단일 SQL→dict 변환)는 `get_*` 단일 함수 + "fetch는 with 블록 안, 가공은 블록 밖"(핵심규칙 5)만 지키면 충분.
- **외부 수집 클라이언트**(스크레이퍼·외부 API)는 fetch+parse 단일 public 함수 허용 — 파서 로직이 커져 단위 테스트가 필요해지면 분리.
- 어느 경우든 **핵심규칙 5(커넥션 범위)는 전 코드 예외 없음** — static_check 게이트 강제.

### 핵심 규칙

1. **클로저 금지**: 함수 안에 `def` 중첩 금지 → 모듈 수준 추출, 의존성은 파라미터로 전달
2. **I/O와 로직 분리**: DB 조회 함수 안에 계산/변환 로직 금지
3. **파이프라인 패턴**: 배치는 `fetch → process → persist` 3단계 독립 함수
4. **타입 힌트**: 모든 public + `_fetch_*`/`_format_*` 함수에 파라미터 + 반환 타입 필수
5. **커넥션 범위**: `_fetch_*` 안에서만 열고 dict 변환 후 반환 — `_format_*`까지 열려 있으면 안 됨
6. **라우트 핸들러는 `def`(동기)** ★: DB 레이어가 동기 `psycopg2`라, 라우트 핸들러를 `async def`로 쓰면 이벤트루프가 쿼리 동안 막혀 **동시 요청이 직렬화**된다. → **동기 `def`로 선언**(FastAPI가 threadpool에서 병렬 실행). `await`가 실제 필요한 핸들러만(`await request.form()`·`await asyncio.to_thread(...)`·SSE 스트림) `async def`.

### 함수 명명 패턴

```python
# db/reads/*.py
def _fetch_summary_raw(period: str) -> dict | None:     # I/O: DB 조회만
def _format_summary_response(raw: dict) -> dict:        # Logic: 순수 변환
def get_summary_data(period: str = "1M") -> dict:       # Public: 조합

# batches/*.py
def fetch_all_items(...) -> list:      # 1단계: I/O
def process_items(...) -> list:        # 2단계: Logic
def persist_and_notify(...) -> int:    # 3단계: Side Effects
def run(...):                          # Orchestrator: 3단계 조합

# web/routes/*.py
def _merge_series(...) -> dict:        # 모듈 수준 헬퍼 (클로저 금지)
def api_summary(...) -> dict:          # 엔드포인트: 동기 def(rule 6), 헬퍼 조합만
```

### 올바른 패턴 vs 금지 패턴

```python
# ✅ 올바른 패턴
def _fetch_cat_summary_raw(period: str) -> dict | None:
    with get_db() as conn:
        rows = conn.execute(...).fetchall()
    return {"rows": [dict(r) for r in rows]}   # 커넥션 닫힌 후 반환

def _format_cat_summary(raw: dict) -> dict:    # I/O 없음
    ...

def get_cat_summary(period: str) -> dict:      # 조합만
    raw = _fetch_cat_summary_raw(period)
    return {} if raw is None else _format_cat_summary(raw)

# ❌ 금지 패턴 — 커넥션 열린 채로 변환 로직
def get_cat_summary(period: str):
    with get_db() as conn:
        rows = conn.execute(...).fetchall()
        result = {r["cat"]: r["total"] * 1e-8 for r in rows}   # ← 금지
    return result
```

## 정본 예시 파일 (golden exemplar) — 새 파일은 이 파일을 Read 후 모방 (임의 형제 선택 금지)

> **첫 구현이 정본이 된다.** 각 유형의 첫 파일을 만들 때는 이 문서 규칙을 100% 준수해 작성하고, 완성 즉시 아래 표에 등재한다. 이후 같은 유형의 파일은 반드시 정본을 Read 후 모방.

| 만들려는 것 | 모방할 정본 |
|-------------|-------------|
| db/reads 단순 조회 모듈 | (첫 구현 시 등재) |
| db/reads 복잡 조회(3분할) | (첫 구현 시 등재) |
| db/writes 도메인 모듈 | (첫 구현 시 등재) |
| web/routes API 모듈 | (첫 구현 시 등재) |
| 배치 스크립트(3단계) | (첫 구현 시 등재) |
| 외부 수집 클라이언트 | (첫 구현 시 등재) |
| React 페이지 | (첫 구현 시 등재) |
| 차트 소비 컴포넌트 | (첫 구현 시 등재) |

프론트 갈림길(색·fetch·interaction 등)과 공용 헬퍼 목록의 정본은 `dev/CONVENTIONS.md`.

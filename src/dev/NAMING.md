# dev/NAMING.md — 변수·함수·필드명 규칙

> 담는 것: 이름을 정할 때의 금지·허용 규칙과 정착 관례. 담지 않는 것: 레이어 구조(→ `dev/ARCHITECTURE.md`)·갈림길 선택(→ `dev/CONVENTIONS.md`)·컬럼 설계(→ `dev/DATA_MODEL.md`). 읽는 시점: 변수·함수·dict 키·DB 컬럼·화면 라벨의 이름을 새로 지을 때.

**핵심 원칙: 코드가 아닌 의미로 이름 짓는다** — 누가 봐도 뭔지 알 수 있어야 한다.

---

## 금지 vs 허용

| ❌ 금지 | ✅ 사용 | 이유 |
|---------|---------|------|
| `rev`, `oper`, `net` | `total_revenue`, `op_income`, `net_income` | 축약어는 모호함 |
| `a12`, `b5` (변수명) | `mgmt_fee`, `sga_codes` | 내부 코드는 변수명에 노출 금지 |
| `"운용보수_a12"` (dict 키) | `"운용보수"` | dict 키·API 응답 필드에 내부 코드 절대 금지 |
| `"A12 누계"` (툴팁 레이블) | `"집합투자기구운용보수"` | 사용자 노출 텍스트에 내부 코드 금지 |

## 범위별 규칙

| 범위 | 규칙 |
|------|------|
| 로컬 변수 | 루프 임시 변수도 의미 있는 단어. `x`, `v`, `r` 정도는 허용, `a12` 금지 |
| dict 반환 키 | 한국어 비즈니스 용어 또는 명확한 영어 (`"운용보수"`, `"fee_rate_bps"`) |
| **DB 컬럼명** | dict 키·API 필드와 **동일 규칙** — 의미 기반 풀네임. 축약어 금지(`rev`/`oper`/`mkt`/`qty`만 예외 관례 허용 시 주석), 내부코드 금지. 예: `foreign_net`·`short_ratio`·`pct_above_50ma` ✅ / `fn`·`sr` ❌. 새 컬럼 추가 전 `dev/DATA_MODEL.md` 설계 절차 준수 |
| 사용자 노출 텍스트 | 공식 한국어 명칭. 툴팁·레이블·footnote에 내부 코드 절대 금지 |
| 함수명 | 레이어별 prefix 준수 (`_fetch_*`, `_format_*`, `get_*` — 적용 스코프는 `dev/ARCHITECTURE.md` §3) |
| DB 쓰기 함수 | prefix = `save_*`/`upsert_*`/`set_*`/`delete_*`/`refresh_*`/`map_*`/`log_*` + **정착 관례(2026-07-16 실태 성문화)**: `init_*_db`(DDL 멱등 생성)·`seed_*`(초기 데이터, ON CONFLICT DO NOTHING)·`replace_*`(전량 교체 트랜잭션)·`rename_*`(식별자 이관 트랜잭션)·`insert_*`/`update_*`(감사로그 동반 CRUD). 목록 밖 이름은 **의미 있는 동사구**면 허용(예: `sync_brand_map`·`mark_notion_synced`·`recompute_duplicate_flags`) — 단 조회함수를 쓰기 prefix로 위장 금지, 순수 SELECT는 `db/reads/`의 `get_*`. 위치는 `db/writes/{도메인}.py`. 호출부는 `from db.writes.{도메인} import` 직접 import — `db/__init__.py` 미경유 |
| DB 컬럼 정착 관례 | `_net` 접미(foreign_net 등 수급 순매수 계열)·`bas_dt`/`fund_cd`/`dept_nm` 류 도메인 표준 접미·`dom`/`ovs`(국내/해외)·`pos52`(52주 위치)·`co`(company 로컬 변수) — 전역 정착 관례로 허용(static_check `_net` 화이트리스트 처리됨). 신규 확장 시엔 풀네임 우선 |

## Python 일반 규칙

1. **파일당 400줄 이하** — 초과 시 기능 단위로 파일 분리
2. **새 기능**: 기존 모듈 확장보다 새 파일 분리 우선
3. **금액 단위**: DB는 원(won), 프론트에서 조/억 변환 (`fmt()`)
4. **날짜 형식**: `YYYY-MM-DD` 문자열 통일
5. **외부 API**: 전부 `verify=False` (사내 방화벽 SSL 우회 — 방식별 정본은 `dev/CONVENTIONS.md` B6)
6. **DB 스키마 변경**: `db/schema.py`의 `init_db()` 수정 후 적용
7. **DB 함수 추가**: 신규 도메인 모듈은 호출부가 `from db.reads.{도메인} import` 직접 import(권장) — `__all__`·`db/reads/__init__.py` 재노출은 구(舊) 모듈 하위호환용으로만 유지
8. **관례 갈림길**: 두 방식이 다 말이 되는 선택은 `dev/CONVENTIONS.md` 표가 정본 — 없으면 등재 후 진행

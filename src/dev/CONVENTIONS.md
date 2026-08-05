# dev/CONVENTIONS.md — 결정된 관례 레지스트리

> 담는 것: 둘 이상의 방식이 가능한 지점에서 선택된 쪽 + 공용 헬퍼 레지스트리. 담지 않는 것: 사고 경위(→ `dev/LESSONS.md`)·세션 행동 규칙(→ `CLAUDE.md`). 읽는 시점: **새 파일·함수를 쓰기 전.**
>
> **목적: 여러 세션의 Claude가 짜도 한 명이 짠 것처럼.** (2026-07-16 사용자 지시, 545파일 전수감사 산물)
> 운영 규칙 2줄:
> 1. **관례가 갈리는 선택을 새로 하게 되면 이 표에 등재하고, 검사 가능하면 `static_check.py`에 검사를 추가한다.**
> 2. **이 표와 코드가 충돌하면 표가 정본이다** (표를 바꾸려면 사용자 합의 후).
> 산문 금지 — 표만. 신규 파일 작성 전 이 표 + 레이어 MD의 정본 예시 파일(golden exemplar)을 읽는다.

## 백엔드

| # | 주제 | 정본 | 근거·예외 |
|---|------|------|-----------|
| B1 | get_db import | `from db.connection import get_db` 단일 (core 경유 금지) | P7 게이트 ⑤. 상대경로(`..connection`)는 잔존 허용, core 경유만 금지 |
| B2 | 에러 반환 | `web/routes/` = `raise HTTPException` / `web/admin/` = JSONResponse 관례 | P7 게이트 ⑦ (routes 한정) |
| B3 | 라우트 핸들러 | 동기 `def`. `async def`는 본문에 실제 await(SSE·to_thread·request.form) 있을 때만 | P7 게이트 ③ |
| B4 | 커넥션 스코프 | `with get_db()` 블록 안 = fetch만. 가공·2차 커넥션 호출 금지 | P7 게이트 ① |
| B5 | env 접근 | `from settings import X` 단일 (os.getenv/os.environ 직접 금지) | P7 게이트 ② |
| B6 | SSL 우회 | requests 직접 호출 = `verify=False` + 인라인 disable_warnings 허용. `ssl_utils.bypass_ssl_verification()`(전역 패치)은 verify kwarg 못 받는 라이브러리(pykrx류) 전용 — web이 import하는 모듈에서 호출 금지 | 2026-07-16 P3 판단: 전역 패치 전파는 보안 회귀 |
| B7 | 진입점 모듈 | import 부작용 금지 — 실행 로직은 main()+`__main__` 가드 | 2026-07-16 batch_runner 사고 |
| B8 | timestamp 저장 | naive 금지 — KST `+09:00` 명시 aware로 저장, cutoff 비교도 aware | 크롤링 신뢰성 원칙·rss_sources 재발 사례 |
| B9 | 랭킹 기준일 resolve | 다(多)config 합산 = `db/reads/_base.resolve_complete_date`(부분수집일 방어). 단건 config은 MAX(date) 정당 | P1 A8 |
| B10 | 숫자 정제 | `db/reads/_base.sanitize_numeric` — 0은 유효값, NULL 변환 금지 | feedback_zero_is_valid_not_null |
| B11 | 수집 클라이언트(kofia/news/etf/dart/businfo/market_briefing 스크레이퍼) | fetch+parse 단일 public 함수 허용 — `_fetch_/_format_` 3분할은 db/reads·배치 파이프라인에 적용 | ARCHITECTURE §3 스코프 |
| B12 | KRX/pykrx 고빈도 per-ticker 배치 | collect→upsert 2단계 허용(메모리 트레이드오프) — 그 외 배치는 fetch→process→persist 3단계 | ARCHITECTURE 예외 |
| B13 | 배치의 DB 조회 | 직접 SELECT 금지 — gap-detection 포함 전부 `db/reads/` 경유(전용 모듈 신설: equity_gaps.py 패턴) | P2 B11 |
| B14 | 신규 일별 수집 배치 | self-heal(최근 7일+ 갭 자가복구) 필수, run_daily 직후 호출 | feedback_batch_self_healing |
| B15 | API 파라미터 날짜범위 | 신규 = `start`/`end` (start_dt/end_dt 금지). 기존 etf_detail_routes는 브레이킹이라 유지(예외) | 감사 6:1 실태 |
| B25 | API 상대기간 파라미터 | 신규 = `days` (lookback_days·period 류 신조어 금지). 기존 `period_days`·`lookback` 은 계약 유지(예외) | refactor_audit F3 |
| B16 | region 파라미터 값 | 신규 = 한국어("국내"/"해외", dependencies.py 계열). etf_detail의 영어 값은 기존 계약 유지(예외) | |
| B17 | 프롬프트 편집 API 필드 | 본문=`content`, DB 수정본 여부=`is_customized` | P2 통일 |
| B18 | LLM 호출 | claude -p = `utils/claude_cli.call_claude` · Gemini = `utils/gemini_client.call_gemini` — 자체 재구현 금지 | |
| B19 | Dooray 호출 | `utils/dooray_client` 단일 — 멤버 확인·DM 발송·업무 프로젝트 조회 전부 여기로 | 재구현 금지 (헬퍼 레지스트리) |
| B19-1 | Dooray 조회 실패 | 목록·상세는 **예외 전파** — 부분 목록을 정상 응답으로 받으면 빠진 업무가 "두레이에서 삭제됨"으로 오마킹된다. 이름 조회만 None 폴백 | 2026-07-28 업무 미러 |
| B22 | KRX 호출 간격 | `settings.KRX_CALL_DELAY` 단일 정본(기본 1.3초). pykrx 배치에서 `CALL_DELAY` 숫자 재정의·`time.sleep` 리터럴 금지 — 값이 흩어지면 한 파일만 되돌아가도 방어가 뚫린다. KRX 는 자동화 대량 조회를 탐지해 **IP 를 1일 차단**하고 재탐지 시 재적용한다 | P7 게이트 ⑰ (`static_check_krx.py`) · 2026-08-03 실차단 |
| B23 | 기준일 완전성 | 읽기 경로(`db/reads/`·`db/repository.py`·`web/`)의 kofia 최신일 resolve 는 완전일 헬퍼(`get_latest_complete_date`/`resolve_complete_date`) 경유. bare `MAX(date)`·`get_latest_date()`·`get_date_range()` 금지 — 부분 수집일이 기준일로 노출된다. 수집측(batches/·db/writes/)은 제외 | 게이트 ⑱ (`static_check_complete_date.py`) · 사이드바 기준일 실사고 |
| B24 | admin 배치 스크립트 경로 | `web/admin` 은 `_common._BATCH_SCRIPTS` 레지스트리 단일 — 경로 문자열 재하드코딩 금지. 새 배치 노출은 레지스트리에 행 추가 후 참조 | 게이트 ㉓ (`static_check_batches.py`) · refactor_audit 우회 5곳 실태 |
| B21 | 배치 스케줄 추가 | `batch_runner.py` `SCHEDULES` 테이블에 행 1개. `should_run_*` 함수·`last_*` 전역을 새로 만들지 않는다. 시각은 하한이고 하루 1회 항목은 `done_key=(batch_name, run_type 접두)` 필수 — 그 배치의 `log_batch_start` 인자와 일치해야 한다(어긋나면 매 틱 재발화). 판정 종류가 4종으로 안 되면 `schedules.py` 에 종류를 더한다 | `assert_done_keys` 가 import 시점에 강제 · 계약 서술은 `DEVGUIDE.md` 배치 스케줄 |
| B20 | 신규 수집/계산 모듈 테스트 | `kofia/ etf/ news/ dart/ businfo/ macro/ us_cycle/ kr_cycle/ analyst_reports/ market_briefing/ dept_issues/ batches/` 신규 .py 는 행동 테스트 1개 필수 — `tests/unit/test_<모듈명>.py`, exemplar `tests/unit/test_institution_sources_parsers.py` 모방 | P7 게이트 ⑫ (`static_check_tests.py`). 기존분은 `static_check_tests_baseline.txt` 래칫 동결(줄어들기만) |

## 프론트엔드

| # | 주제 | 정본 | 근거·예외 |
|---|------|------|-----------|
| F1 | 데이터 fetch | `useApi`(TanStack Query 래퍼) 단일. **예외 = admin 디렉토리**(`_get`/fetch 관례, FRONTEND.md 명문). peers의 useQuery 직접 사용은 useApi 수렴 대상(백로그) | P7 게이트 ⑨ (비admin raw fetch 금지) |
| F2 | 색상 | hex 리터럴 금지 — `constants/colors.ts` 상수 또는 CSS var. **예외 = colors.ts 자신·admin 디렉토리(자체 다크 톤)·CSS 파일** | P7 게이트 ⑧ |
| F3 | 투명도 | 문자열 접합(`+'99'`) 금지 — `hexAlpha()` | |
| F4 | 차트 interaction | 선차트=`index` / 산점도·포인트=`nearest+intersect:true` / 수평바=`{mode:'index',intersect:false,axis:'y'}` | P1 A5·design/CHARTS.md |
| F5 | 차트 래퍼 | `charts/` 래퍼 경유(CHART_DEFAULTS 자동 주입). raw Chart.js 직생성 금지 | P1 A4 |
| F6 | 사용자 노출 텍스트 | 한국어. 결측=`'-'`. 로딩=`'불러오는 중…'`. 이모지 금지(문서화된 예외만) | |
| F7 | 컴포넌트 배치 | 페이지 전용=`components/<page>/`, 2페이지+ 공용=`components/common/`(또는 도메인 루트). KR·US 공용 사이클 컴포넌트=`pages/equity/` 루트 | |
| F8 | 투자자 3계열색 | `INVESTOR_FLOW_COLORS` 단일 (외국인/기관/개인) | P3 C7 |
| F9 | KR·US 대칭 화면 | 구조·섹션 순서 동일 + "결론→근거→기회": **KR·US 사이클 모두 결론(경기국면)이 최상단**, 그 아래 근거(섹터·산업), 매수후보 랭킹은 근거 뒤(2026-07-17 사용자 확정 — 직전 "US=매수후보 최상단" 배치 철회). 한쪽만 개편 금지 | feedback_kr_us_symmetry·P5 |
| F10 | 금액 표시 | DB=원, 표시 변환은 `utils/format.fmt()` 계열 — 페이지 로컬 fmt 재구현 금지 | |
| F11 | 대형 payload 섹션 | 첫 뷰포트 밖 수백 KB 시계열·히트맵 섹션은 `components/common/LazySection.tsx` 로 지연 마운트(placeholder minHeight 필수). 정본 예시 = `UsIndustryCycle.tsx`·`KrCycleBoard.tsx` | P5 5-2·design/COMPONENTS.md |
| F12 | 모바일 분기 기준 | **뷰포트 767.98px 단일** — JSX=`hooks/useIsMobile.ts`, 비훅 컨텍스트=`window.matchMedia('(max-width: 767.98px)')`. ⛔ 컨테이너 clientWidth 기준 금지(사이드바 220px 오버헤드로 데스크톱 오발동 — 2026-07-20 graph.ts 사고) | design/LAYOUT.md 모바일 셸 |
| F13 | 모바일 time 축 | `utils/axes.mobileTimeAxis(dataLength, isMobile)` 단일 — autoSkip+maxTicksLimit 인라인 재구현 금지 (2026-07-20 2곳 중복 통합) | |
| F14 | 터치 타깃 | 반복 탭 컨트롤 ≥40px — CSS 클래스면 `@media (pointer:coarse){ … min-height:40px }`(base.css `.sh-filters`/`.filter-bar` 정본 모방), 인라인 style이면 `isMobile ? { minHeight:40, … } : null` 스프레드. 새 40px 값 재발명 전 base.css coarse 블록 확장 가능 여부 먼저 확인 | design/UX.md 모바일 터치 히트영역 |
| F15 | 동일 수치 다중 위젯 | 같은 수량(예: 카테고리별 AUM)을 그리는 위젯이 2개+면 **파생 산식(netting·합산·비중)을 한 모듈에서 공유** — 위젯마다 산식 복제 금지. peers 카테고리 산식 정본 = `peers/aum/constants.FULL_CFG` + `breakdownLogic.netFullCfg`, 도넛·바차트 공동 소비 | 2026-07-22 바차트 ETF 이중계상 사고 — 도넛만 netting, 바는 복제 산식이 어긋남 |
| F16 | region='전체' 국내+해외 합산 | `utils/regionMerge.mergeRegionRows` 단일 — 인라인 outer join 금지. **합산은 양쪽이 다 수집된 날짜만**이다(한쪽만 수집된 날은 그 지역만으로 반토막이 된다). 백엔드 대응 규칙은 B9 | 2026-08-03 AUM 추이 차트가 국내만 수집된 날을 72.3조로 찍어 카드 93.4조와 어긋남 |
| F18 | 기간·기준일 선택 UI | 기준일(as-of)은 **select(최신/전년말/월말 선택…) + MonthPicker 팝오버** — overview·/peers·/industry 동형이 정본. 모드 select 가 성립하지 않는 기간형(월+분기/반기/연간)만 `components/common/MonthField`(form-select 외형 트리거 + 같은 팝오버). select 2개(연/월)·칩 나열·`<input type="date">` 쌍·새 트리거 위젯 발명 금지 | 2026-08-04 사용자 지적 2회 — 1차 "화면마다 제각각", 2차 "peers 기준일 표기 버튼이랑 똑같이"(MonthField 커스텀 버튼을 기준일에 쓴 것도 발명으로 판정) |
| F17 | 스냅샷형 API 기본 상태 = 날짜 파라미터 생략(bare 키) | 사용자가 날짜를 직접 바꾸기 전(userDated)엔 `end`/`endDt` 를 쿼리스트링·쿼리키에서 뺀다 — 키가 날짜와 무관해져 4워커 서버캐시 수렴·프리워밍 일치·as_of 대기 체인 제거. 시계열(start~end 창이 응답을 결정)은 대상 아님. 정본 예시 = `Equity.tsx snapEndDt`·`KrCycleBoard cycleFilters`·`usePeersRanking` | page-load-perf: OR-NULL 수술(DB.md)과 한 쌍 |
| F18 | admin 저장 완료 콜백 prop | `onChanged` 단일 (onSaved·onDone 류 금지) | refactor_audit F8 |
| F19 | KR·US 사이클 grain 용어 | KR = "sector"(KRX 업종) ↔ US = "industry"(GICS Sub-Industry) — 같은 grain 의 시장별 명칭이라 교차 개명 금지 | refactor_audit F5 |

## 공용 헬퍼 레지스트리 (동일 목적 재구현 금지 — 신설 전 이 표 확인)

| 모듈 | 제공 | 소비 도메인 |
|------|------|------------|
| `utils/claude_cli.py` | call_claude·call_claude_json·strip_fence·load_prompt_file·JSON_ONLY_SUFFIX·is_available | analyst_reports·market_briefing·dept_issues |
| `utils/gemini_client.py` | call_gemini(재시도 파라미터화·response_mime_type)·GeminiRetryExhausted | forecast·briefing·news |
| `utils/dooray_client.py` | 멤버 확인·DM 발송·업무 프로젝트 조회(목록/상세/댓글·멤버 이름) | member_auth·dooray_task_batch·(구 news DM) |
| `utils/ssl_utils.py` | bypass_ssl_verification(전역—pykrx류 전용)·legacy_tls_session | pykrx 계열·kofia_rfp |
| `utils/ttl_cache.py` | TTLCache·_ttl_cache | db/reads 무거운 조회 |
| `frontend/src/utils/regionMerge.ts` | mergeRegionRows·mergeRegionSeries·mergeRegionTable(국내+해외 합산, 양쪽 수집일만) | overview AUM 추이·peers agg_series·market 차트/탐색기 |
| `utils/data_utils.py` | (수치 변환 헬퍼) | 수집 배치 |
| `db/reads/_base.py` | resolve_complete_date·sanitize_numeric·make_config 등 | db/reads 전역 |
| `web/dependencies.py` | ConfigFilter·clamp·market_or_none | web/routes 전역 |
| `web/admin/_common.py` | _spawn_batch·_BATCH_SCRIPTS·isoformat_fields·prompt_override_get/put/delete | admin 라우트 그룹 |
| `db/reads/equity_helpers.py` | resolve_latest_bas_dt(스칼라 MAX 프로브 — OR-NULL 대체, DB.md) | equity·equity_screen 계열 |
| `macro/collect.py` | collect_series·HEADERS | macro 전 수집기 |
| `us_cycle/yf_client.py` | make_session·coerce_float | prices·fundamentals·financials |
| `analyst_reports/http_client.py` | get_html | naver_research·hankyung |
| `frontend utils/format.ts` | fmt·fmtWon 등 | 전 페이지 |
| `frontend charts/` | Line/Bar/Doughnut/Scatter/ChartWrapper(+CHART_DEFAULTS) | 전 차트 |
| `frontend admin/format.tsx` | badge·fmtUpdated·PromptStatusLine | admin pane |
| `frontend components/common/` | SectionHead·MonthField(기간 선택 필드)·MonthPicker(그 팝오버 본체)·AiInsight·Footnote·IntegrityBadge | 2페이지+ 공용 |

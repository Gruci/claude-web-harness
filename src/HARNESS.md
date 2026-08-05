# HARNESS.md — Claude Code 하네스 지도

> 담는 것: 훅·에이전트·스킬·게이트가 무엇이 있고 언제 발화하는지의 한 페이지 지도. 담지 않는 것: 각 실물의 정본 내용(→ `.claude/` 각 파일·`static_check.py` 헤더). 읽는 시점: 하네스를 파악하거나 수정할 때.

하네스를 고치려면 먼저 하네스를 볼 수 있어야 한다. 이 파일이 그 입구다. 구성이 바뀌면 같은 턴에 갱신하고, 누락은 게이트 ④E가 실물과 대조해 잡는다.

## 훅 발화 순서

세션 시작부터 종료까지 시간순이다. **차단**은 exit 2로 진행을 멈추고 모델에게 피드백을 돌려준다.

| # | 이벤트 | 훅 | 조건 | 결과 |
|---|--------|----|------|------|
| ① | SessionStart | `lazy-persona.md` 주입 | 항상 | 통과 |
| ① | SessionStart | node 실행 검사 | node 없음 | 경고 문자열 |
| ① | SessionStart | `.claude/hooks/git_staleness.py` | main 이 origin/main 보다 뒤짐 | ff-only 정렬, 거부되면 경고 |
| ② | UserPromptSubmit | `check_context_growth.py` | transcript ≥ `WARN_BYTES` | 경고 + `/clear` 권고 |
| ③ | PreToolUse(Read) | `check_context_diet.py` | 추정 토큰 > `LIMIT_TOKENS` 이고 `limit` 분할 없음 | **차단** |
| ④ | PostToolUse(Edit·Write) | `check_file_rules.py` | 레거시 UI 경로 편집 | **차단** |
| ④ | PostToolUse(Edit·Write) | `check_file_rules.py` | `.py`·`.ts`·`.tsx`·`.md` 저장 후 `static_check.py --file` 위반 | **차단** |
| ④ | PostToolUse(Edit·Write) | `impeccable/scripts/hook.mjs` | 항상 | 통과 (UI 리마인더) |
| ⑤ | SubagentStop | `check_agent_return.py` | 반환 > `MAX_RETURN_CHARS` | **차단** |
| ⑥ | Stop | `check_editing_lock.py` | `EDITING.md`에 자기 `#sid` 행 잔존 | **차단** |
| ⑥ | Stop | `check_coding_rules.py` | `static_check.py` 전체 위반 잔존 | **차단** |

`check_file_rules.py`는 페이로드 파싱 실패와 30초 무응답도 차단한다(fail-closed). `check_agent_return.py`는 반환문을 못 찾으면 통과시킨다(fail-open — 전 에이전트 차단이 더 위험).

### 임계 상수

값의 정본은 코드다. 여기엔 왜 그 값인지만 적는다.

| 상수 | 값 | 정의 | 근거 |
|------|-----|------|------|
| `LIMIT_TOKENS` | 16,000 | `check_context_diet.py` | 정리 후 최대 정본 MD는 통과, 수십 KB 덤프는 차단하는 지점 |
| `CHUNK_LIMIT_LINES` | 500 | 〃 | 분할 읽기 탈출구 |
| `MAX_RETURN_CHARS` | 20,000 | `check_agent_return.py` | 상세 반환은 허용, 파일 전문 덤프는 차단 |
| `WARN_BYTES` | 15,000,000 | `check_context_growth.py` | transcript는 실컨텍스트의 3~5배 프록시 — 1M의 3분의 1 지점 |
| `MAX_LINES` | 400 | `static_check.py` | 파일 단일 책임 하한선 |

토큰 추정식은 ASCII 4자당 1토큰, 그 외 1자당 1토큰이다. 한글이 UTF-8 3바이트라 바이트로 재면 3배 과대평가된다.

## 에이전트

`.claude/agents/` 아래 정의된다. 모델과 effort의 정본은 각 파일 frontmatter다.

| 이름 | 용도 | 모델 | effort | 존재 이유 |
|------|------|------|--------|-----------|
| `qa` | API 응답과 프론트 소비의 경계면 교차검증 | opus | medium | 양쪽 코드를 동시에 로드하는 별도 컨텍스트가 필요하다 |
| `data` | KOFIA·DB 무결성 점검, 백필 범위 산정 | sonnet | medium | 대량 기계적 정독 |
| `ceo-reviewer` | 자산운용사 대표 페르소나 검수 | fable | high | 역할 분리가 본질 — 저볼륨 고스테이크 판단 |
| `orchestrator` | 독립 트랙 3개 이상의 병렬 구현 지휘 | fable | high | 공유 파일 조정이 런타임 판단이라 별도 층이 필요하다 |
| `impeccable-manual-edit-applier` | impeccable 수동 편집 적용 | inherit | medium | 벤더 스킬 소속 — 수정하지 않는다 |

메인 루프가 몇 번의 툴 호출로 끝낼 일은 위임하지 않는다. 모델 라우팅 정본은 `CLAUDE.md`다.

## 스킬

`.claude/skills/<name>/SKILL.md`. Codex 대응물은 `.agents/skills/<name>-cdx/`에 있다.

| 이름 | 트리거 | 참조 |
|------|--------|------|
| `feature-workflow` | 기능·버그 요청 | `CLAUDE.md`·`EDITING.md` |
| `deploy` | 배포 요청 | `docker/DEPLOY.md` |
| `test` | 테스트 작성 | `dev/TESTING.md` |
| `md-audit` | 월 1회 MD 드리프트 감사 | 정본 MD 전반 |
| `briefing-eval` | 시황 프롬프트 변경 전 회귀 평가 | `market_briefing/MARKET_BRIEFING.md`·`ceo-reviewer` |
| `review-loop` | 대표 검수 루프 | `ceo-reviewer` |
| `kofia-ops` | KOFIA 데이터 운영 | `kofia/KOFIA.md`·`db/DB.md` |
| `news-ops` | 뉴스 파이프라인 운영 | `news/NEWS.md` |
| `businfo-ops` | 경영공시 운영 | `businfo/BUSINFO.md` |
| `lazy-review`·`lazy-audit`·`lazy-debt` | 과설계 리뷰·감사·부채 수확 | `.claude/hooks/lazy-persona.md` |
| `impeccable` | UI 디자인 전반 | 벤더 — 수정하지 않는다 |

## static_check 게이트

전량 강제다. 위반이 있으면 exit 1이고 Stop 훅이 세션 종료를 막는다. 검사 내용의 정본은 `static_check.py` 헤더 docstring이다.

| 번호 | 검사 | 정의 파일 | 예외 |
|------|------|-----------|------|
| 1 | 파일 400줄 초과 | `static_check.py` | — |
| 2 | 중첩 def | 〃 | 일회성 스크립트 |
| 3 | `db/reads` 쓰기 SQL·commit | 〃 | — |
| 4·4b | 축약어 `net`·`oper_`·`rev_` | 〃 | dict 키·레거시 경로 |
| 5 | UI 라벨 금칙어 | 〃 | — |
| ⑩·⑪ | py `Any`·TS `any` 때우기 | 〃 | allowlist·인라인 주석 |
| ①②③⑤⑥⑦ | 백엔드 레이어 관례 | `static_check_gates.py` | 각 allowlist |
| ⑧⑨ | 프론트 hex 리터럴·raw fetch | 〃 | 각 allowlist |
| ⑫ | 수집·계산 모듈과 행동 테스트 짝 | `static_check_tests.py` | baseline 래칫 |
| ⑭ | DDL 저장 타입 잘림 — `REAL` 금지·`NUMERIC` 소수 스케일 근거 주석 | `static_check_schema.py` | baseline 래칫 |
| ④A | MD 백틱 경로 실존 | `static_check_md.py` | `md_ref_allowlist.txt` |
| ④B | 배치 스케줄 표와 코드 상수 대조 | 〃 | — |
| ④C | `.env` 키 목록과 코드 대조 | 〃 | — |
| ④D | 고아 MD — 허브에서 도달 불가 | 〃 | 도메인 동명 MD는 총칭 라우팅 인정 |
| ④E | 이 파일과 하네스 실물 대조 | 〃 | — |
| ⑬ | MD 작성 규칙 구조 신호 | `static_check_md_style.py` | `static_check_md_baseline.txt` |
| ⑯ | 프롬프트 본문↔헤더 버전 동시 갱신 | `static_check_prompt.py` | `origin/main` 부재 시 생략 |
| ⑮ | API 응답 배열 필드 옵셔널 | `static_check_api_types.py` | baseline 래칫 |
| ⑰ | KRX 호출 간격 단일 정본 | `static_check_krx.py` | — |
| ⑱ | 기준일 완전성 — bare `MAX(date)` 금지 | `static_check_complete_date.py` | allowlist 래칫 |
| ⑲ | 배치 직접 SELECT 금지(B13) | `static_check_batches.py` | BASELINE 래칫 |
| ⑳ | LLM 클라이언트 단일 정본(B18) | `static_check_llm.py` | BASELINE 래칫 |
| ㉑ | region 국내+해외 합산 정본(F16) | `static_check_region.py` | BASELINE·필터 allowlist |
| ㉒ | py 헤더 경로 주석 실경로 일치 | `static_check.py` | docs/·scripts/ 제외 |
| ㉓ | admin 배치 경로 레지스트리(B24) | `static_check_batches.py` | BASELINE 래칫 |
| ㉔ | 단일 정본 리터럴 — 로스터 재나열·시장명 3항·gnews 분기·KR 블록 라벨 짝 | `static_check_dup.py` | ROSTER_ALLOWLIST 고정 |
| ㉕ | web 파라미터 가드 정본 — 인라인 clamp·market 3항·admin 프롬프트 CRUD 직접 호출 금지 | 〃 | — |

⑬의 규칙 정본은 `dev/MD_STANDARD.md`다. 게이트는 기계 검사 가능한 부분만 강제하고, 의미 단위 판정은 `/md-audit`이 맡는다.

## MD 라우팅

무슨 작업에 어느 MD를 읽는지의 정본은 `CLAUDE.md` 라우팅표다. Codex 쪽은 `AGENTS.md`가 같은 역할을 한다.

허브는 셋이다. `DEVGUIDE.md`가 백엔드, `DESIGN_GUIDE.md`가 디자인, `CLAUDE.md`가 전체 진입점이다. 도메인 패키지는 각 패키지 안의 동명 대문자 MD가 정본이다.

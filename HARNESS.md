# HARNESS.md — 하네스 지도

> 담는 것: 훅·에이전트·스킬·게이트가 무엇이 있고 언제 발화하는지의 한 페이지 지도. 담지 않는 것: 각 항목의 정본 내용(→ `.claude/` 각 파일·`kernel/` 헤더)·세션 행동 규칙(→ `CLAUDE.md`)·이 프로젝트가 무엇인지(→ `PROJECT.md`). 읽는 시점: 하네스를 파악하거나 수정할 때.

하네스를 고치려면 먼저 하네스를 볼 수 있어야 한다. 이 파일이 그 눈이고, 구성이 바뀌면 같은
턴에 갱신한다. 빠뜨리면 검사 28이 실물과 대조해 잡는다.

## 구조

```
CLAUDE.md          세션 행동 규칙 (스택 무관)
PROJECT.md         이 프로젝트가 무엇인지 (도메인·스택)
harness_profile.py 커널이 이 프로젝트에 대해 아는 것 전부
kernel/            판정 로직. 프로젝트를 모른다
harness_gates/     이 레포 전용 게이트 (선택)
.claude/           훅·에이전트·스킬
```

아래가 위를 강제한다. 사람이 어겨도 훅이 막고, 훅이 무엇을 막을지는 프로파일 한 파일이
정한다. 그래서 다른 프로젝트로 옮길 때 고치는 파일도 `harness_profile.py` 하나다.

## 훅 발화 순서

세션 시작부터 종료까지 시간순이다. **차단**은 exit 2 로 진행을 멈추고 모델에게 피드백을 준다.

| # | 이벤트 | 훅 | 조건 | 결과 |
|---|--------|----|------|------|
| ① | SessionStart | `lazy-persona.md` 주입 | 항상 | 통과 |
| ② | SessionStart | git·origin 검사 | 저장소 아님 또는 origin 미설정 | 경고 문자열 |
| ③ | SessionStart | 프로파일 검사 | `harness_profile.py` 없음 | 경고 문자열 |
| ④ | SessionStart | 인터프리터 검사 | python 또는 node 실행 불가 | 경고 문자열 |
| ⑤ | SessionStart | `git_staleness.py` | 기본 브랜치가 origin 보다 뒤 (**startup 한정**) | ff-only 자동 정렬 |
| ⑥ | SessionStart | `check_maintenance.py` | 정비 임계치 초과 (**startup 한정**) | 밀린 정비 목록 |
| ⑦ | UserPromptSubmit | `check_context_growth.py` | transcript 가 임계 초과 | 경고 + `/clear` 권고 |
| ⑧ | PreToolUse(Read) | `check_context_diet.py` | 추정 토큰 초과인데 분할 없음 | **차단** |
| ⑨ | PostToolUse(Edit·Write) | `check_file_rules.py` | 저장한 파일이 게이트 위반 | **차단** |
| ⑩ | PostToolUse(Edit·Write) | `impeccable/scripts/hook.mjs` | 항상 | 통과 (UI 리마인더) |
| ⑪ | SubagentStop | `check_agent_return.py` | 반환이 임계 초과 | **차단** |
| ⑫ | Stop | `check_editing_lock.py` | `EDITING.md` 에 자기 행 잔존 | **차단** |
| ⑬ | Stop | `check_coding_rules.py` | 전 게이트 위반 잔존 | **차단** |
| ⑭ | Stop | `check_git_remote.py` | GitHub 원격 미설정 | **차단** |

⑨ 는 페이로드 파싱에 실패해도 차단한다(fail-closed) — 무엇을 검사할지 모르는 상태를 통과로
보고하지 않는다. ⑪ 은 반대로 fail-open 이다. 반환을 못 읽었다고 에이전트를 막는 건 더 위험하다.

⑤⑥ 만 `startup` matcher 로 분리돼 있다. `/clear` 와 compact 마다 `git pull` 과 정비 판정이
다시 도는 것을 막기 위해서다.

## 게이트

판정 정본은 `kernel/gates/` 이고 진입점은 `kernel/runner.py` 다. 대상 레이어와 어휘는 전부
`harness_profile.py` 에서 온다 — **선언이 없으면 `[SKIP]` 이고, 그건 통과가 아니라 "이 게이트는
지금 아무것도 안 지켜준다"는 뜻이다.**

| # | 게이트 | slug | 무엇을 막나 |
|---|--------|------|-------------|
| 1 | 파일 길이 상한 | `line_limit` | 단일 책임을 잃은 파일 |
| 2 | 중첩 def | `closures` | 테스트할 수 없는 숨은 로직 |
| 3 | 읽기 레이어의 쓰기 | `reads_writes` | 조회 경로에 섞인 부작용 |
| 4 | 축약 이름 | `abbrev_names` | 내부 코드가 이름으로 새는 것 |
| 5 | 축약 접두 | `abbrev_prefixes` | 〃 |
| 6 | UI 라벨 금칙어 | `ui_jargon` | 사용자에게 노출되는 조어 |
| 7 | py Any | `py_any` | 타입으로 게이트 때우기 |
| 8 | 공개 함수 타입힌트 | `type_hints` | 문서화되지 않은 모듈 경계면 |
| 9 | 시크릿 토큰 | `secrets` | 실키 하드코딩 |
| 10 | TS any | `ts_any` | 타입체커 strict 우회 |
| 11 | 커넥션 블록 내 가공 | `conn_processing` | 커넥션 점유 중 집계 |
| 12 | 설정 밖 환경변수 | `env_access` | 환경변수 읽는 지점이 흩어지는 것 |
| 13 | await 없는 async | `web_async` | 비동기인 척하는 동기 핸들러 |
| 14 | 접근자 import 경로 | `accessor_import` | 같은 헬퍼를 두 경로로 부르는 것 |
| 15 | 전역 SSL 패치 위치 | `ssl_bypass` | 검증 우회가 아무 데서나 켜지는 것 |
| 16 | 라우트 에러 응답 | `routes_error` | 에러 형식이 라우트마다 다른 것 |
| 17 | 공용 래퍼 없는 fetch | `raw_fetch` | 캐시·에러 처리 없는 직접 호출 |
| 18 | 프론트 색 리터럴 | `hex_literal` | 색 하드코딩 (rgb·hsl 우회 포함) |
| 19 | 고정 폭 | `responsive` | 폰을 깨뜨리는 px 폭과 `100vw` |
| 20 | 브라우저 API 직접 호출 | `browser_api` | 앱 이식 때 교체 범위가 퍼지는 것 |
| 21 | 앱 코드 배치 | `file_placement` | 선언 밖 배치 — 나머지 게이트를 무음으로 만든다 |
| 22 | 행동 테스트 짝 | `test_pairing` | 깨져도 아무도 모르는 수집·계산 모듈 |
| 23 | DDL 저장 타입 | `ddl_types` | 소스 정밀도를 못 담는 컬럼 |
| 24 | API 배열 옵셔널 | `api_array` | 배포 시차로 undefined 가 도착하는 것 |
| 25 | MD 작성 규칙 | `md_style` | 의미가 뭉개진 문서 |
| 26 | MD 경로 참조 | `md_path_refs` | 삭제·리네임 후 남은 유령 경로 |
| 27 | 고아 MD | `md_orphans` | 허브에서 도달 못 하는 문서 |
| 28 | 하네스 지도 | `md_harness_map` | 이 파일과 실물의 어긋남 |
| 29 | 에이전트 모델 정책 | `agent_model` | frontmatter 와 정책표의 드리프트 |
| 30 | 사고 절 승격 상태 | `lessons_promotion` | 사고를 적고 판단을 미루는 것 |

문서↔코드 대조(`doc_sync`)는 프로파일의 `DOC_SYNC` 가 정의한 만큼 늘어난다.
이 레포 전용 게이트는 `harness_gates/<이름>.py` 에 두고 `LOCAL_GATES` 로 켠다.

21 번이 나머지의 전제다. 배치가 자유로우면 첫 실코드가 선언 밖에 지어지는 순간 3·11~16 이
대상 0건으로 조용히 죽는다.

## 등급

| 등급 | 뜻 | exit |
|------|-----|------|
| `[OK]` | 검사했고 위반 0건 | 0 |
| `[SKIP]` | **검사할 대상이 없었다** — 프로파일 선언이 없거나 실물이 없다 | 0 |
| `[FAIL]` | 강제 위반 | 1 |
| `[REPORT]` | 연성 신호. 오탐 여지가 있어 합산하지 않는다 | 0 |

`[OK]` 와 `[SKIP]` 을 가르는 것이 이 하네스의 핵심이다. 이전 세대는 레이어 이름이 안 맞아
대상이 0개인데도 `[OK]` 로 찍어, 지켜주지 않는 게이트를 지켜준다고 믿게 만들었다.

## 에이전트

정본은 `.claude/agents/` 각 파일의 frontmatter 다. model·effort 는 프로파일의
`AGENT_MODEL_POLICY` 와 대조된다(검사 29) — 한쪽만 바꾸면 막힌다.

| 이름 | 용도 | 존재 이유 |
|------|------|-----------|
| `executor` | 승인된 plan 하나를 통째로 자율 실행 | 완결된 설계서를 옮기는 일은 판단이 아니라 볼륨이다 |
| `backend` | 서버 코드 편집 | 레이어 규칙을 로드한 별도 컨텍스트 |
| `frontend` | 화면 코드 편집 | 디자인 시스템을 로드한 별도 컨텍스트 |
| `qa` | API 응답과 화면 소비의 경계면 교차검증 | 양쪽을 동시에 읽는 별도 컨텍스트가 필요하다 |
| `product-reviewer` | 사용자 관점 검수 | 역할 분리가 본질 — 만든 사람은 자기 결과를 못 본다 |
| `impeccable-manual-edit-applier` | impeccable 수동 편집 적용 | 벤더 사본. 손대지 않는다 |

메인 루프가 몇 번의 툴 호출로 끝날 일을 위임하지 않는다. 부트스트랩 비용이 더 크다.

## 스킬

| 이름 | 언제 |
|------|------|
| `harness-init` | 새 프로젝트를 하네스에 연결할 때. `harness_profile.py` 가 없으면 이것부터 |
| `feature-workflow` | 기능 추가·수정·버그 수정 |
| `full-feature` | 서버와 화면을 같이 만들 때 |
| `impeccable` | UI 품질 — 비평·감사·다듬기 |
| `lazy-audit` | 레포 전체 과설계 감사 |
| `lazy-debt` | `lazy:` 부채 수확 |
| `lazy-review` | 변경분 과설계 리뷰 |
| `md-audit` | 문서와 코드의 어긋남 감사 |
| `review-loop` | 리뷰 반복 |
| `test` | 테스트 작성 |

## 정비 — 사용자가 시켜서 도는 게 아니다

월간 감사류는 "한 달에 한 번 돌리세요"라고 적어두면 아무도 안 돈다. 사용자가 명령어를 외우고
때를 판단해야 하기 때문이다. 그 판단을 훅 ⑥ 이 대신한다.

| 정비 | 무엇을 보나 | 기본 임계치 |
|------|-------------|-------------|
| `md-audit` | 문서와 코드가 어긋난 곳 | 커밋 80개 또는 30일 |
| `lazy-audit` | 필요 이상으로 복잡해진 코드 | 커밋 150개 또는 60일 |
| `lazy-debt` | 미뤄둔 `lazy:` 표시의 재고 | 표시 12개 |
| `impeccable critique` | 화면 사용성 | 화면 파일 20개 변경 또는 45일 |
| `review-loop` | 사용자 관점의 지표·문구 | 화면 파일 12개 변경 |

판정 정본은 `kernel/maintenance.py`, 임계치 조정은 프로파일의 `MAINTENANCE`, 마지막 실행
기록은 `harness_maintenance.json` 이다. 기록은 커밋한다 — 세션과 머신이 바뀌어도 공유돼야
주기가 성립한다. 화면 레이어가 선언되지 않은 프로젝트에선 화면 관련 두 항목이 아예 안 뜬다.

전부 **보고서만 내고 코드는 고치지 않는다.** 그래서 알림이 뜨면 승인 없이 실행한다.
고칠지 말지는 보고서를 본 뒤의 문제다.

## 하네스가 자라는 법

게이트는 설계된 게 아니라 사고마다 하나씩 늘었다.

사고가 나면 먼저 경위를 `dev/LESSONS.md` 에 남긴다. 무슨 일이 있었고 무엇을 잃었는지.
규칙만 적으면 다음 세션이 "이번은 예외 아닌가" 하고 넘기지만, 대가가 적혀 있으면 못 넘긴다.

그다음 기계로 검사할 수 있는지 본다. 할 수 있으면 `kernel/gates/` 에 판정을 더하고 그 절의
`> 강제:` 를 게이트 번호로 갱신한다. 못 올리면 `산문 전용 — 사유` 로 적는다. 둘 중 아무것도
안 적으면 검사 30 이 막는다. 적어놓고 판단을 미룬 상태이기 때문이다.

그래서 산문 전용으로 남은 목록이 곧 다음에 게이트로 올릴 후보다.

> 훅 command 는 상대경로로 등록한다. `%CLAUDE_PROJECT_DIR%` 표기는 이 환경에서 확장되지 않아 훅이 통째로 실패한다.
> **훅 cwd 는 셸 툴의 잔류 작업 디렉토리를 따라간다** — 루트 보장이 아니다. 프로젝트 밖으로 `cd` 한 채 턴을 끝내면 상대경로 훅이 전부 실패한다. 외부 디렉토리 작업은 서브셸로 하고 턴이 끝나기 전 루트로 되돌린다.

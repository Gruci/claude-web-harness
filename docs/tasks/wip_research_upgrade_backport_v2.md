# research_upgrade_backport_v2 — 실운영 스냅샷(2026-09-07) 2차 역이식 리서치

> 담는 것: `upgrade/harness/`(fund_monitor 실운영 최신본)와 현 템플릿의 전수 대조 결과 — 백포트 후보·템플릿 자체 결함·제외 판정. 담지 않는 것: 구현 순서와 파일 설계(→ plan). 읽는 시점: plan 작성 전.

1차 역이식(v3.3.0, `docs/tasks/archive/2026-08-21-upgrade-backport/`) 이후 실운영본에 쌓인 변경분이 대상이다. 판정 기준은 "범용 웹설계 하네스에 성립하는가"다 — 펀드 도메인 어휘·고유 경로에 묶인 것은 제외했다.

## 우선순위 요약

| 순위 | 항목 | 왜 먼저 |
|---|---|---|
| 1 | 템플릿 자체 결함 3건 수리 (§1의 R1~R3) | 백포트가 아니라 지금 깨져 있는 것 — 훅 하나는 핵심 케이스가 무음으로 죽어 있다 |
| 2 | 셸 게이트 매처 규칙 (§4 M1) | 실운영에서 게이트 4개가 무력화된 채 머지된 실사고의 재발 방지 |
| 3 | 훅 백포트 4건 (§2) | 오차단·미차단이 실측된 것들 |
| 4 | 커널 게이트 신규 9~10종 (§3) | SQLi 차단·프론트 테스트 짝 등 커버리지 공백 |
| 5 | MD 운영 규칙·스킬 보정 (§4~§5) | 산문 층 — 급하지 않으나 같은 plan에 묶으면 싸다 |

## §1 템플릿 자체 결함 — 대조 중 발견, 백포트와 무관하게 수리 대상

| # | 위치 | 결함 | 근거 |
|---|---|---|---|
| R1 | `.claude/hooks/check_worktree_residue.py:64` | `import subprocess` 누락 — `_alive()`가 매번 NameError → `except`가 삼켜 항상 "살아있음" 판정. lock 걸린 worktree의 크래시 잔해 검출이 무음으로 죽어 있다 | upgrade 쪽은 import 정상 (`upgrade/.../check_worktree_residue.py:49`) |
| R2 | `kernel/gates/core.py:74` | `check_header_path_comment`(검사 ㉒)가 구현만 있고 `kernel/runner.py`에 등록이 없다 — [SKIP]조차 안 찍히는 죽은 게이트. "무음 통과 없음" 계약 위반 | upgrade 레지스트리엔 등재됨 (`upgrade/harness/gates/__init__.py:67`) |
| R3 | `kernel/context.py:26` | `_rel`이 `.claude/worktrees/<이름>/` 접두를 안 벗기고, ROOT 밖 경로면 ValueError로 터진다. worktree 안 신규 파일에 경로 기반 검사가 전부 오탐 | upgrade `gates/rule.py:52-60`이 접두 벗기기 + 사유 주석 보유 |
| R4 | `.claude/skills/test/SKILL.md:14-21` | 코드펜스 디렉토리 트리 — 자기 `dev/MD_STANDARD.md` ①(펜스 트리 금지) 위반이고, 없는 디렉토리를 만들라는 지시가 된다 | upgrade는 "실태 정본은 TESTING.md·Glob" 한 줄로 처리 |
| R5 | `kernel/gates/duplication.py:205` | `_sources`에 scratch(일회성 스크립트) 제외 필터가 없다 — 스크립트 사본이 dup_decl 위반으로 올라와 소거 불가능한 baseline 부채가 된다 | upgrade `gates/duplication.py:36` `SKIP_PREFIXES` |
| R6 | `kernel/gates/md_graph.py:288` | MD 함수 참조 매처가 `name\s*\(`로 넓고 `_BUILTIN_CALLS` 하드코딩으로 되막는 구조 — 목록 밖 함수형 표기(SQL 집계·CSS 함수)가 위반으로 뜬다 | upgrade `gates/md.py:273`은 빈 괄호 `foo()`만 매칭 — 커버리지 대신 신뢰도 |
| R7 | `kernel/gates/md_style.py:41` | 머리 역할 계약이 `담는 것/담지 않는 것/읽는 시점` 한 표기만 인정 — 격식 문서(`문서 범위/제외 범위/열람 시점`)를 쓰면 전 파일 위반 | upgrade `gates/md_style.py:47-49` 두 표기 수용 |

## §2 훅 백포트 후보

| # | 훅 | 내용 | upgrade 근거 |
|---|---|---|---|
| H1 | `check_bash_write.py` | `gh pr merge --auto` 차단 — 필수 체크 없는 레포에서 `--auto`는 즉시 머지(=배포 트리거)다. 조각 머리 3토큰 판정 | `:70, 170-179, 289-297` |
| H2 | `check_task_residue.py` | 24시간 신선도 유예(`_is_fresh`) — 1~2단계 세션의 갓 쓴 research/plan이 남의 정리 시점에 미이관 산출물로 오차단된 실사고를 mtime으로 덮는다 | `:58, 75-81, 88-91` |
| H3 | `check_workflow_script.py` | ① `agentType:`을 `model:`과 동치 인정(에이전트 frontmatter가 모델 정본이라 현행은 정상 호출을 오차단) ② opts가 식별자면 정의부 탐색, 못 찾으면 차단(2) 대신 판정 불능 경고(1) ③ `(?<![\w.])agent\(`로 `foo.agent(` 배제 | `:36, 97-103, 125-132, 173-176` |
| H4 | `check_file_rules.py` | 페이로드 파싱 실패·검사기 타임아웃을 exit 2 대신 exit 1 비차단으로 — Edit 전면 차단 시 그 훅을 고칠 수단도 Edit이라 복구 경로가 자기 자신을 지난다. 같은 하네스의 `check_bash_write`(exit 1)와 방향 통일 | `:26-31, 70-73` |
| H5 | `check_ui_copy.py` 신규 이식 | 브랜치 diff의 신규 UI 문구만 골라 Haiku 1콜로 감수(내부어·축약·구어체·번역투) — 정적 denylist(검사 ui_jargon)가 못 잡는 명단 밖 신종을 잡는다. 문구 해시 캐시·인프라 실패 fail-open. **개조 필요**: 프롬프트의 업종·실사례를 프로파일 주입으로, `origin/main`→`default_branch()`, UI 경로·언어 프로파일화, `utils/claude_cli` 대신 하네스 자체 LLM 헬퍼 신설 | 훅 전문 + `settings.json:156-161` + 설계 서술 `upgrade/harness/HARNESS.md:37` |

제외: `check_agent_return` transcript 폴백(템플릿이 의도적으로 제거한 것), 나머지 훅 9종(범용화 차이뿐이거나 템플릿이 앞섬 — worktree_name 오탐 수리·default_branch 감지·`_hookio` 등은 역방향 이식 불필요).

## §3 커널 게이트 신규 후보

전부 도메인 어휘 없음 — 경로·심볼만 프로파일화하면 성립한다.

| # | 검사 (upgrade 번호) | 내용 | upgrade 근거 |
|---|---|---|---|
| G1 | ㊳ 함수 80줄 상한 | AST로 함수·메서드 길이 판정 — 파일 400줄 상한이 못 보는 축("한 파일에 400줄 함수 하나") | `gates/structure.py:79` |
| G2 | ㊵ 읽기 레이어 컬럼 식별자 raw 보간 금지 | `f"{column}"` 보간·join 패턴을 잡고 화이트리스트 헬퍼 경유 강제 — 바인딩 불가 자리라 새면 미인증 SQLi (실운영 보안감사 Critical) | `gates/rules.py:351` |
| G3 | ㊸㊹ 프론트 테스트 짝 | export 있는 `.ts`와 모든 `.tsx`에 `.test.*` 짝 요구 + baseline 분리 — 현 커널 tests_pairing은 파이썬 전용이라 화면 쪽이 통째로 공백 | `gates/tests_pairing.py:78, 97` |
| G4 | ㉜ 해시 네비게이션 단일 기전 | pushState·popstate 금지 + hashchange 복원 조합에 이벤트 디스패치 강제 — "주소만 바뀌고 화면이 안 따라오는" 상태는 검사만이 발견 수단 | `gates/rules.py:291, 306` |
| G5 | ㊴ TYPE_CHECKING ↔ future annotations | 짝 없으면 3.11에서만 NameError — 로컬 통과·CI 파열형 함정 | `gates/rules.py:138` |
| G6 | ㉖ CSS 캐시버스터 = 내용 해시 | `?v=` 값과 파일 sha256 대조 — 손 버전은 같은 날 두 번 고치면 안 올라간다 | `gates/assets.py:41` |
| G7 | ㉝ 쓰기 레이어 `round(` 금지 | 저장은 원 정밀도·반올림은 표시 레이어 — ddl_types(타입 잘림)의 나머지 절반 | `gates/rules.py:317` |
| G8 | ⑲ 배치 레이어 직접 SELECT 금지 | 조회는 읽기 레이어 경유 — 현 커널엔 역방향(읽기 레이어의 쓰기)만 있다 | `gates/rules.py:155` |
| G9 | ㊶ 루트 직속 잡파일 allowlist | 미추적 포함 루트 파일을 allowlist로 판정 — 현 file_placement는 `.py`만 봐서 덤프·메모·스크린샷을 놓친다 | `gates/pairing.py:51` |
| G10 | ⑯ 프롬프트 버전 범프 (선택) | 지정 프롬프트 파일 내용 변경 시 헤더 `V<major>.<minor>` 범프 강제 — 프로파일 목록이 비면 [SKIP]. LLM 기능 있는 프로젝트에서만 의미 | `gates/prompt.py:51` |

제외(특화): KRX 호출 간격·kofia 뷰·region 합산·단일 정본 리터럴 6종·admin 배치 경로·자산유형 순서·기간 리터럴·차트 격자색/래퍼(Chart.js 고정)·admin 토큰·Gemini 클라이언트. ㉕A 인라인 클램프는 dup_decl과 겹쳐 보류.

## §4 MD·운영 규칙 후보

| # | 대상 | 내용 | upgrade 근거 |
|---|---|---|---|
| M1 | `HARNESS.md` | **셸 게이트 매처는 셸 실행 툴 전부(Bash+PowerShell)를 담는다** — 한쪽만 걸면 같은 명령이 다른 툴로 그냥 나간다. 실운영에서 게이트 4개가 그렇게 무력화된 채 머지됐고, ④E는 이름 존재만 봐서 매처 문자열은 사각이라는 명시까지 | `HARNESS.md:26, 170` |
| M2 | `HARNESS.md` | 임계 상수 근거표 — 16k 토큰·500줄·20k자·15MB·400줄의 "왜 그 값인지" + 토큰 추정식(한글을 바이트로 재면 3배 과대평가). 현 템플릿은 전부 "임계 초과"로 추상화해 튜닝 근거가 사라졌다 | `HARNESS.md:74-86` |
| M3 | `HARNESS.md` | 실패 시 방향표에 두 행 복원 — 검사기 30초 무응답→비차단 경고(느린 검사기와 틀린 코드는 다른 사건), session_id 식별 불가→태그 없는 행만 차단(전 행 차단은 종료 불능) | `HARNESS.md:58-72` |
| M4 | `HARNESS.md` | allowlist(사유 있는 영구 예외) vs baseline(리팩토링이 소거할 부채) 정의 구분 — 없으면 예외 넣을 곳이 즉흥 | `HARNESS.md:178` |
| M5 | `CLAUDE.md` | 증거 원칙에 「구현·커밋은 자기 worktree에서만 — 첫 편집 전 브랜치·경로 확인」 승격 — EDITING.md에만 있으면 그걸 안 읽은 턴에 샌다 | `CLAUDE.md:65` |
| M6 | `CLAUDE.md` | 「오케스트레이션 중에도 git·검증·보드는 메인 전담 — 워커 보고는 증거가 아니다」를 위임 결정자(메인)가 읽는 층으로 승격 | `CLAUDE.md:143` |
| M7 | `CLAUDE.md` | 위임 입력 규칙(결정에 필요한 요약+경로만, 원본 대량 주입 금지) + orchestrator 발동의 부정 조건(크지만 순차인 과업은 미발동) | `CLAUDE.md:142, 145` |
| M8 | `CLAUDE.md` 라우팅표 | 「기존 데이터셋을 새 표·차트에 얹기 전 → 데이터셋 표시 규약: 순서·라벨은 화면이 정하지 않는다」 행 — 같은 데이터가 화면마다 다른 순서로 굳는 것 방지 | `CLAUDE.md:28` |
| M9 | `EDITING.md` | 백로그 운영 2규칙 — 열린 것만 남긴다(완료·기각 행 삭제) + 착수 전 서술을 실물로 대조(지난 정리에서 8건 중 5건이 이미 해결·3건은 전제가 낡음) | `EDITING.md:71-76` |
| M10 | `EDITING.md` | 트랙별 worktree가 정당할 때의 안전 절차 — 스폰 전 sentinel로 dirty + `git worktree lock`(dirty는 자동 제거 판정을, lock은 제거를 막는다) + 워커에 재생성 경로 지시. 현행은 금지만 있고 예외 절차가 없다 | `EDITING.md:36-41` |
| M11 | `dev/MD_STANDARD.md` | 계약 격식 표기 행(`문서 범위/제외 범위/열람 시점` 수용, 슬롯 3개 동일 조건) — R7 게이트 수리와 같은 커밋 | `dev/MD_STANDARD.md:86` |

참고: upgrade `CLAUDE.md:49`의 "깃에 올려라 = push→PR→CI→merge"는 백포트가 아니라 **분기 선택지**다 — 템플릿의 단순형(`push origin HEAD`)은 신규 1인 프로젝트 기본값으로 의도된 것이고, EDITING.md 4번이 이미 원격 PR·CI 유무 분기를 갖는다. CLAUDE.md에 그 분기 참조 1줄만 추가하면 정합.

## §5 스킬·에이전트 후보

| # | 대상 | 내용 |
|---|---|---|
| S1 | 스킬·에이전트 7파일 | 머리 역할 계약 인용구 복원 — upgrade엔 있는데 템플릿 이식 때 빠졌다(lazy 3종·md-audit·review-loop·test·qa·product-reviewer). 자기 MD_STANDARD ② 위반 상태 |
| S2 | `qa.md` + 프로파일 정책표 | model sonnet→opus 승격 — 경계면 shape 대조는 팬아웃이 아니라 판단이라는 실운영 결론. 검사 29 때문에 frontmatter와 `AGENT_MODEL_POLICY` 동시 수정 |
| S3 | `qa.md` | 「기존 실패는 백로그 참조 — 신규 실패만 보고」 — 알려진 적색 반복 보고 방지 |
| S4 | `test/SKILL.md` | R4 수리와 함께: 미등록 pytest 마커 함정(`-m integration`이 조용히 0개 선택) + 「외부 HTTP는 monkeypatch 스텁 — 테스트 편의로 새 의존성 금지」 |
| S5 | `feature-workflow/SKILL.md` | 브리프 패스트트랙의 복붙 3슬롯 서식(스코프/노출/데이터) — 현행은 패스트트랙을 말만 하고 서식이 없다 |
| S6 | `review-loop/SKILL.md` | 재검수 요청 서식(이전 판정/반영 수정/수정 후 내용) — 없으면 2회차 검수가 처음부터 다시 본다 |
| S7 | `product-reviewer.md` | ceo-reviewer의 「나의 관심 영역」 표 골격만 이식 — "도메인 확정 시 페르소나 구체화" 지시를 "이 표를 채워라"로 구체화 |

제외: deploy·briefing-eval·businfo-ops·kofia-ops·news-ops 스킬, data 에이전트(전부 특화). orchestrator·feature-workflow 본문·md-audit 구조는 템플릿이 앞선다.

## 다음 단계

plan에서 정할 것: R·H·G·M·S의 커밋 묶음(자체 결함 수리를 선행 분리할지), G군의 프로파일 키 설계(레이어 이름·심볼 주입), H5의 LLM 헬퍼 신설 범위, 각 게이트의 픽스처 테스트. 구현은 plan 승인 후.

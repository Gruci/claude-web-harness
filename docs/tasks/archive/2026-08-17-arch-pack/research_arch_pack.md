# docs/tasks/research_arch_pack.md — 아키텍처팩(ARCH) 리서치

> 담는 것: kernel/arch/ 아키텍처팩 신설을 위한 코드 실물 정독 결과 — 검사 전수 분류·언어팩 계약 대응·[N/A] 메커니즘·수정 지점·리스크·미해결 질문. 담지 않는 것: 설계 결정(→ plan_arch_pack.md). 읽는 시점: plan 작성 직전 1회.

리서치 시점 스냅샷이다. file:line 은 이 시점 실물 기준이다.

## 1. 검사 전수 분류표

번호·slug 정본은 `HARNESS.md` 게이트 표(번호 1~30)다. 고정 번호 게이트 30개에 가변 계열 3종(doc_sync·린터·로컬)이 더해진다.¹

분류: ① 보편(언어·아키텍처 무관) / ② 하네스-문서 온톨로지(스택 무관, 이 하네스 고유 MD·에이전트 체계 전제) / ③ 아키텍처 온톨로지(web 3-레이어 구조 전제).

| # | slug | 분류 | 의존 profile 키 | ARCH팩 추출 |
|---|------|------|----------------|-------------|
| 1 | `line_limit` | ① | 없음 | 아니오 |
| 2 | `closures` | ① | SYNTAX(언어팩 축) | 아니오 |
| 3 | `reads_writes` | ③ | LAYERS[read] | **예** |
| 4 | `abbrev_names` | ① | VOCAB[abbrev_names] | 아니오 |
| 5 | `abbrev_prefixes` | ① | VOCAB[abbrev_prefixes]·scratch | 아니오 |
| 6 | `ui_jargon` | ③² | VOCAB[ui_denylist] + ui_files 배선 | 조건부 — plan 결정 |
| 7 | `py_any` | ① | PATTERNS[any_type]·LAYERS[tests] | 아니오 |
| 8 | `type_hints` | ① | LAYERS[tests] | 아니오 |
| 9 | `secrets` | ① | 없음 | 아니오 |
| 10 | `ts_any` | ③² | ui_files 배선(함수 자체는 키 없음) | 조건부 — plan 결정 |
| 11 | `conn_processing` | ③ | SYMBOLS[db_accessor]·LAYERS[db] | **예** |
| 12 | `env_access` | ③(부분)³ | FILES[settings]·PATTERNS[env_read]·ALLOWLIST[env_access]·LAYERS[tests] | 조건부 — plan 결정 |
| 13 | `web_async` | ③ | LAYERS[web] | **예** |
| 14 | `accessor_import` | ③ | SYMBOLS[db_accessor·db_accessor_module]·LAYERS[read·write] | **예** |
| 15 | `ssl_bypass` | ③ | SYMBOLS[ssl_bypass]·FILES[ssl_util]·LAYERS[batch] | **예** |
| 16 | `routes_error` | ③ | SYMBOLS[error_response]·LAYERS[routes] | **예** |
| 17 | `raw_fetch` | ③ | ALLOWLIST[ui_fetch·ui_fetch_wrappers]·LAYERS[ui_admin] | **예** |
| 18 | `hex_literal` | ③ | ALLOWLIST[ui_hex]·LAYERS[ui_tokens·ui_admin] | **예** |
| 19 | `responsive` | ③ | LAYERS[ui_admin] | **예** |
| 20 | `browser_api` | ③ | ALLOWLIST[ui_platform]·LAYERS[ui_admin] | **예** |
| 21 | `file_placement` | ③(부분)⁴ | LAYERS 전체·ROOT_FILES·SCOPE | 조건부 — plan 결정 |
| 22 | `test_pairing` | ①⁵ | BEHAVIOR_TESTED_ROOTS·LAYERS[tests] | 아니오 |
| 23 | `ddl_types` | ③ | LAYERS[schema] (layer_raw) | **예** |
| 24 | `api_array` | ③⁶ | 없음 — `.ts`/`types` 하드코딩 | 조건부 — plan 결정 |
| 25 | `md_style` | ② | MD[style_exclude·date_exempt] | 아니오 |
| 26 | `md_path_refs` | ② | MD[doc_exclude·ref_exclude]·(부가)LAYERS[ui] | 아니오 |
| 27 | `md_orphans` | ② | HUBS·HUB_DOMAIN_MD_IMPLICIT | 아니오 |
| 28 | `md_harness_map` | ② | HARNESS_MAP | 아니오 |
| 29 | `agent_model` | ② | AGENT_MODEL_POLICY | 아니오 |
| 30 | `lessons_promotion` | ② | LESSONS_DOC·HARNESS_MAP | 아니오 |
| 가변 | `doc_sync:{doc}` | ① | DOC_SYNC | 아니오 |
| 가변 | 린터(TOOL) | ① | LINTERS(언어팩 축) | 아니오 — LANG 소관 |
| 가변 | `local:{name}` | 프로젝트 고유 | LOCAL_GATES | 아니오 |

집계(고정 30개): ① 8개 · ② 6개 · ③ 16개. ③ 16개 중 확정 추출 11개, 조건부 5개(6·10·12·21·24).

각주:

1. 과업 지시의 "36개"와 실물 번호 표 30개가 불일치한다. 가변 계열(doc_sync 항목 수·린터·로컬)을 포함해 세면 프로파일에 따라 30+α다. 본 표가 실물 전수다.
2. `ui_jargon`·`ts_any`는 함수 본문만 보면 ①이나, 발동 조건이 `kernel/runner.py:181-186`의 ui_files 배선(profile.layer("ui") 존재)에 있다. 파일 단위(core.py) 분류를 따르면 ①로 오판된다 — 배선 기준 ③을 택했다(othergates·webgates 정독 일치).
3. `env_access`는 "환경변수는 설정 모듈 경유"라는 규칙이라 레이어 3분할 자체보다 넓다. webgates·regression 정독 모두 "부분 결합"으로 판정 — 소속을 plan에서 확정한다.
4. `file_placement`의 "레이어냐 도메인 패키지냐" 배치 규칙은 아키텍처 불특정 개념이나, 구현(`kernel/gates/placement.py:30-33` layer_prefixes)이 profile.LAYERS 전체 순회에 결합돼 있다. 커널 잔류 + LAYERS 스키마 일반화가 유력하나 plan 몫이다.
5. `test_pairing`은 경계 사례 — "수집·계산 모듈엔 행동 테스트"는 아키텍처 무관이고 BEHAVIOR_TESTED_ROOTS는 자유 경로 목록이라 ①을 택했다(othergates 판정).
6. `api_array`는 "프론트/백엔드 분리 배포" 전제라 ③이지만 profile 키를 하나도 안 써서 ARCH가 끌 수단이 현재 없다 — runner 호출부(`kernel/runner.py:223-224`)나 함수 내부 수정이 별도로 필요하다.
7. `check_header_path_comment`(`kernel/gates/core.py:78`)는 정의만 있고 runner 배선이 없는 미사용 함수다 — 이번 리팩터 대상 아님, 언급만 남긴다.
8. `check_reads_writes`(`kernel/gates/core.py:120`)는 core.py 상단 docstring의 "레이어를 모르는 검사만 모았다" 선언을 어기는 유일한 함수다 — 이관 시 docstring(1~15행)도 같은 턴에 갱신해야 한다.

## 2. 언어팩 계약과 ARCH 축 대응

언어팩 계약(정본 `kernel/lang.py:6-9`): 순수 데이터 파일이 최상위 상수 5개만 선언한다. 로더는 `pack_path()`(profiles/lang/ 이 kernel/langs/ 를 이김, :48-53) → `load()`(importlib 동적 로드, 실패 시 DEFAULTS 조용한 폴백, :64-87) → `kernel/profile.py:88-108`에서 프로파일 선언이 팩 값을 덮는 3단 병합이다.

| 언어팩 필드 | 의미 | ARCH 축 대응 |
|------------|------|-------------|
| `EXT` | 소스 확장자 | 대응 없음 — 확장자는 언어 소관 |
| `SYNTAX` | ast 파서 가용성 | 대응 없음 — 파싱은 언어 소관. 단 N/A 사유 접두어로 오용 중(§3) |
| `PATTERNS` | 관용구 정규식(부분 병합 update) | 대응 후보 없음 — 아키텍처는 정규식이 아니라 레이어 존재를 선언 |
| `NOT_APPLICABLE` | dict[slug, 사유] — 게이트 단위 N/A | **핵심 대응** — ARCH팩도 dict[slug, 사유]. 단 "레이어가 없다" 선언에서 slug 목록을 유도할지, slug를 직접 나열할지가 설계 갈림(§6) |
| `LINTERS` | 외부 도구 목록(TOOL 등급 별도 경로) | 대응 없음 — 도구는 언어 소관 |

| 로더 구성물 | LANG 실물 | ARCH 복제 대상 |
|------------|----------|---------------|
| 로더 모듈 | `kernel/lang.py` (DEFAULTS·pack_path·available·load) | `kernel/arch.py` 신설 |
| shipped 팩 | `kernel/langs/{python,go,typescript}.py` | `kernel/arch/{web_layered,…}.py` 신설 |
| 프로젝트 오버라이드 | `profiles/lang/` (실물 0건, 미검증 경로) | `profiles/arch/` — 동일하게 미검증 출발 |
| 프로파일 키 | `LANG` (`kernel/profile.py:88`, getattr 기본 None) | `ARCH` — 미선언 시 None 폴백으로 하위호환 |
| 스키마 문서 | `profiles/_template.py:25-35` LANG 블록 | ARCH 블록 병기 |
| 설치 로그 | `harness_install.py:116-121` | ARCH 표시 추가(선택) |

비대칭 주의: 언어팩은 "검사기가 언어를 이해하는 방법"이라 커널 동반 이동이 원칙(`kernel/lang.py:26-28` 주석)이지만, 아키텍처는 프로젝트 정체성에 더 가깝다 — shipped 팩 vs 프로파일 소유의 무게중심이 LANG과 같지 않을 수 있다(plan 판단).

## 3. [SKIP]→[N/A] 전환 메커니즘 — 지점과 제약

N/A는 신설 등급이 아니다. LANG용으로 완성된 배관이 이미 있고 ARCH는 그 배관에 올라탄다.

| 지점 | file:line | 현재 동작 | ARCH 관련 제약 |
|------|-----------|----------|---------------|
| N/A 판정 | `kernel/runner.py:122-131` `_entry()` | `profile.not_applicable(slug)` 사유가 있으면 SKIP보다 먼저 `("N/A", …)` 반환 | 우선순위 골격은 그대로 재사용 가능 |
| 구문 게이트 판정 | `kernel/runner.py:134-147` `_syntax_section()` | 순서 N/A > TOOL > SKIP/OK | ARCH N/A가 TOOL("파서 없음")을 가리는 우선순위 정책을 plan에서 확정 |
| 사유 문자열 | `kernel/runner.py:130,144` | `f"{profile.SYNTAX}: {unneeded}"` — 언어명 접두 하드코딩 | ARCH 사유에 그대로 쓰면 "python: web 레이어 없음" 오염 — 접두 분기 또는 포맷 파라미터화 필수 |
| 사유 조회 | `kernel/profile.py:126-128` `not_applicable()` | 단일 NOT_APPLICABLE dict 조회 | ARCH 사유를 같은 dict에 병합할지 별도 채널로 둘지가 §6 최대 결정 |
| dict 병합 | `kernel/profile.py:104-106` | 언어팩 → 프로파일 오버라이드 2소스 update | ARCH가 3번째 소스 — 동일 slug 충돌 시 승자 규칙 선례 없음 |
| 등급 출력 | `kernel/runner.py:53-72` `_print_sections()` | grade 문자열을 `[{grade:<4}]`로 그대로 출력, enum 없음 | 러너 출력부 수정 불필요 — "N/A"는 `[N/A ]`로 이미 렌더됨(golden/go.txt 실증) |
| 체커 선실행 | `kernel/runner.py:172-227` | violations 인자가 `_entry` 호출 전에 평가됨 — N/A여도 체커는 돈다 | 레이어 부재 시 체커가 예외 없이 빈 결과를 내는지 게이트별 확인 필요 |
| LAYERS None | `kernel/profile.py:142-147` `layer()` | None = "미설정" = SKIP 트리거 | "아키텍처상 없음"과 "설정 깜빡함"을 가르는 값이 현재 없음 — 새 채널 없이는 N/A 전환 불가 |
| _LAYER_KEYS | `kernel/profile.py:23-26` | 12개 web 전제 키 고정 화이트리스트 | 임의 아키텍처의 레이어 선언을 받으려면 스키마 일반화 선행 |

## 4. 수정 지점 전수

| 영역 | 파일 | 성격 | 근거 지점 |
|------|------|------|----------|
| kernel/ | `kernel/arch.py` 신설 | 로더 — lang.py 4구성물(DEFAULTS·pack_path·available·load)과 두 방어(미선언→기본값, 로드 실패→조용한 폴백) 복제 | `kernel/lang.py:29-31,48-53,64-87` |
| kernel/ | `kernel/arch/` 팩 신설 | 순수 데이터 팩 — langs/python.py 형태 모방 | `kernel/langs/python.py:9-25` |
| kernel/ | `kernel/profile.py` | ARCH 로드·병합 병렬 블록, NOT_APPLICABLE 채널 결정, _LAYER_KEYS 일반화 검토 | :23-26, :83-108, :104-106, :126-128 |
| kernel/ | `kernel/runner.py` | 사유 접두 분기(SYNTAX 하드코딩 해소), _kernel_sections의 web 게이트 분리 여부 | :122-147, :130,144, :166-227 |
| kernel/ | `kernel/gates/layers.py` | web_layered 이관 주력 — 로컬 헬퍼 `_under`/`_parse`/`_is_admin_ui`는 모듈 전용이라 이전 깔끔 | :39-48, :262-264 |
| kernel/ | `kernel/gates/core.py` | `check_reads_writes` 이관 + 상단 docstring 갱신 | :1-15, :120 |
| kernel/ | `kernel/gates/placement.py` | 잔류하되 layer_prefixes의 LAYERS 결합 일반화 — runner와 설치 스크립트 양쪽이 import | :30-33; `kernel/runner.py:217`; `harness_install.py:225` |
| kernel/ | `kernel/gates/api_types.py` | ARCH가 끌 수단 부여(하드코딩 게이팅 해소) — 방식은 plan | :62 |
| kernel/ | `kernel/gates/schema.py` | `ddl_types` 이관 여부 | :42 |
| profiles/ | `profiles/_template.py` | ARCH 키 문서화 — LANG 블록과 병기 | :25-35 |
| profiles/ | 프리셋 4종(api_fastapi·batch_python·fund_monitor·web_fastapi_react) | ARCH 명시 선언 여부 — LANG은 4/5가 암묵 기본값 의존 중 | LANG 미선언 실물 확인됨 |
| profiles/ | `profiles/arch/` 신설(선택) | 오버라이드 경로 — profiles/lang/ 관례 대응, install의 비재귀 glob과 충돌 없음 | `harness_install.py:59-61` |
| harness_install.py | `--doctor` 리포트 | 언어 리포트(runner 미경유 별도 뷰)에 ARCH 병기 여부 | :110-141, :281-283 |
| harness_install.py | 설치 본체 | 통짜 복사(shutil.copy2)라 수정 불필요 — 프리셋에 ARCH 상수만 추가하면 됨 | :186-208 |
| tests/ | `tests/fixture_files.py`·`tests/fixture_go.py` | harness_profile.py 리터럴 문자열에 ARCH 한 줄 추가 후 build_fixture 재생성 | fixture_files.py:338-378; fixture_go.py:73-100; build_fixture.py:36-42 |
| tests/ | `tests/golden/{bare,full,go}.txt` | 완전 문자열 일치 대조 — 러너 변경 시 3종 `--update` 재생성 + 수동 diff 검토. go.txt는 웹레이어 SKIP 9줄 + TOOL 1줄이 N/A 전환 1차 후보 | run_golden.py:84-136; golden/go.txt:7-33 |
| .claude/hooks/ | 변경 불필요 | 두 훅(check_file_rules·check_coding_rules)은 returncode만 보는 블랙박스 — 라벨 파싱 없음. trace.py 정규식도 `[FAIL]` 줄만 매치해 N/A 확장에 안전 | check_file_rules.py:71-93; check_coding_rules.py:47-67; `kernel/trace.py:34-35` |
| MD | `HARNESS.md`·`profiles/_template.py` 주석 | 게이트 표·구성 변경분 같은 턴 갱신 — 검사 28이 실물 대조 | HARNESS.md:65-101 |

## 5. 리스크 — 심각도 순

1. **N/A 사유 접두 하드코딩** — `kernel/runner.py:130,144`가 `f"{profile.SYNTAX}: 사유"`로 언어명을 박아, ARCH 사유를 기존 채널에 그대로 얹으면 "python: web 레이어 없음"류 오염이 난다. _entry/_syntax_section 수정이 불가피하고, 이는 러너 로직 변경이라 **골든 3종 전부 재생성 대상**이다. 순수 데이터 팩 하나로 안 끝난다는 것이 7개 정독 전원 일치 결론이다.
2. **LAYERS None의 이중 의미** — None이 이미 "설정 안 채움"(SKIP)의 정본 표현이라(`kernel/profile.py:142-147`), ARCH가 같은 None에 "아키텍처상 없음"을 얹으면 사용자가 깜빡한 레이어와 원래 없는 레이어를 구분 못 한다. 게다가 `_LAYER_KEYS`(:23-26)가 web 전제 12키 고정 튜플이라 팩 추출만으로는 다른 아키텍처가 자기 레이어를 선언할 수 없다 — profile.py 스키마 일반화가 선행 조건이다.
3. **기존 사용자 프로파일(ARCH 미선언) 호환** — `getattr(_MOD,"ARCH",None)` 패턴이면 미선언은 오늘의 SKIP 동작이 그대로 보존된다(안전 기본값). 반면 프리셋 4/5가 LANG을 암묵 기본값에 의존하는 기존 관행을 ARCH가 따라 하면 전 프로젝트가 특정 아키텍처로 암묵 편입된다 — "아키텍처 비종속" 취지와 충돌하므로 프리셋엔 명시 선언이 안전하다.
4. **NOT_APPLICABLE 3소스 병합** — 현재 2소스(언어팩→프로파일) update 선례뿐이다. LANG과 ARCH가 같은 slug를 다른 사유로 선언하면(예: web_async를 go팩과 backend_only팩이 동시에) 병합 순서에 따라 사유가 비결정적으로 덮인다. N/A > TOOL 우선순위 탓에 정당한 TOOL 메시지가 가려지는 경우도 같은 축이다.
5. **골든 완전 문자열 일치의 파급** — run_golden.py가 stdout 전체를 == 비교라, 러너 한 줄 변경도 3 정답지 전체 diff다. 안전망이지만 `--update` 후 의도한 변경만 있는지 수동 검토 절차가 plan에 필수다. 픽스처 profile이 gitignore라 재생성 누락 시 구버전 캐시로 조용히 통과하는 문서화된 함정도 그대로 적용된다.
6. **ui_files 배선 축과 레이어 축의 경합** — ui_jargon·ts_any·api_array는 함수가 아니라 배선이 아키텍처를 전제하고, "UI 파일이 없음"(기존 SKIP)과 "아키텍처에 프론트가 없음"(신설 N/A)이 같은 게이트에서 경합한다. api_array는 profile 키 0개라 별도 수단 없이는 ARCH가 못 끈다.
7. **placement의 외부 소비** — layer_prefixes/domain_prefixes를 runner와 harness_install이 import하므로 layers.py만 옮기는 경계를 잘못 그으면 배치 게이트가 깨진다.
8. **arch 로더 예외 방어 미복제** — 훅이 fail-closed(exit 2)라 로더가 lang.py의 조용한 폴백을 안 베끼면 깨진 팩 하나가 러너 전체를 크래시시켜 전 게이트 빨간불이 된다.
9. **체커 선실행** — N/A 판정돼도 인자 평가 시점에 체커가 이미 돌므로, 레이어 부재를 전제 안 한 체커의 예외 여부를 게이트별로 확인해야 한다.
10. **부수 이원화·부패 위험** — --doctor의 손 리포트가 LANG/ARCH 두 벌로 갈라질 위험, profiles/arch/가 profiles/lang/처럼 실물 0건 죽은 지점이 될 위험, baseline slug 하위호환(이름 유지 시 재생성 불필요, 변경 시 동결 전멸), ② 축(md_orphans 등) 리팩터 혼입 금지.

## 6. 미해결 질문 — plan 결정 사항

| # | 질문 | 갈림길 |
|---|------|--------|
| 1 | ARCH N/A 채널 | 기존 NOT_APPLICABLE dict에 병합(러너 무수정에 가깝지만 접두 오염·충돌) vs 별도 `ARCH_NOT_APPLICABLE` + `not_applicable_arch()`(배선 추가되나 사유·우선순위 명확) |
| 2 | 팩 선언 형식 | slug 직접 나열 dict vs "없는 레이어" 선언에서 slug 목록을 커널이 유도(레이어→게이트 매핑표가 커널에 필요해짐) |
| 3 | LANG vs ARCH 동일 slug 충돌 | 병합 승자 규칙 — LANG 먼저 / ARCH 먼저 / 프로파일 최종 오버라이드 |
| 4 | N/A vs TOOL 우선순위 | 아키텍처상 없음이 파서 부재보다 먼저인가 |
| 5 | ARCH 기본값 | None(오늘의 SKIP 보존) vs web_layered 암묵 기본 — 3안과 직결 |
| 6 | 조건부 5개 소속 | ui_jargon·ts_any·env_access·file_placement·api_array 각각의 팩 경계 |
| 7 | web 게이트 물리 이동 범위 | layers.py 통째 이동 vs runner 배선만 조건부 분기(slug·baseline 하위호환 유지가 제약) |
| 8 | _LAYER_KEYS 일반화 방식 | ARCH팩이 레이어 키 집합을 선언 vs 화이트리스트 확장 유지 |
| 9 | --doctor ARCH 리포트 | 병기 vs 생략 — 이원화 부패 위험과 트레이드오프 |
| 10 | golden 재생성 검토 절차 | --update 후 diff 수동 검토를 plan Todo로 명문화 |

# plan_upgrade_backport_v2 — 실운영 스냅샷(2026-09-07) 2차 역이식

> 담는 것: `wip_research_upgrade_backport_v2.md` 채택분의 구현 설계 — 파일별 변경 스니펫·검증·트랙. 담지 않는 것: 후보 발굴 경위(→ 리서치 파일). 읽는 시점: 구현(3단계) 착수 전.

## 접근 방식

세 묶음으로 나눈다. **A 자체 결함 수리**(백포트 이전에 지금 깨진 것), **B 훅·게이트 백포트**(실운영 검증분의 범용화 이식), **C 산문·에이전트·스킬 보정**. 커밋도 이 순서의 3개로 나눠 각각 검증과 함께 닫는다.

이식 원칙: 판정 로직은 upgrade 원본을 따르되, 어휘·경로·심볼은 전부 `harness_profile.py` 주입으로 바꾼다. 커널 게이트의 대상 선정·[SKIP] 처신은 기존 `_entry`/`_syntax_section` 계약을 그대로 쓴다. 새 게이트의 소급 동결은 개별 baseline 파일이 아니라 기존 `harness_baseline.txt`(slug·파일 동결) 하나로 통일한다 — upgrade 의 baseline 3분할은 그 레포 부채 413건의 가독성 문제였고 여기엔 그 부채가 없다.

### 채택하지 않는 것 (리서치 대비 확정)

| 항목 | 판정 | 사유 |
|---|---|---|
| G6 CSS 캐시버스터 해시 | 제외 | 프리셋 스택(Vite React)은 번들러가 자산 해싱을 한다 — 손 링크 CSS 전제의 게이트라 켜질 프로젝트가 없다. `dev/REJECTED.md` 등재 |
| ㉕A 인라인 클램프 | 보류 | dup_decl(선언 재구현)이 같은 부류를 이미 잡는다. 실누출 관측 시 재론 |
| M-깃에올려라 분기 | 참조 1줄만 | CLAUDE.md 단순형은 1인 신규 프로젝트 기본값으로 의도된 것 — EDITING.md 4번의 PR·CI 분기를 가리키는 1줄만 추가 |

## 묶음 A — 자체 결함 수리 (commit 1)

### A1. `.claude/hooks/check_worktree_residue.py` — import 누락
```python
import re
import subprocess
import sys
from pathlib import Path
```
`_alive()`가 매번 NameError → `except: return True`로 삼켜져 lock 걸린 worktree 가 PID 생사와 무관하게 영구 면제되던 실버그.

### A2. `kernel/runner.py` — 죽은 게이트 등재 (검사 header_path)
`_kernel_sections` 의 `line_limit` 다음 행에:
```python
_entry("header_path", "헤더 경로 주석", core.check_header_path_comment(files), files, NO_PY),
```
헤더 주석이 없는 파일은 애초에 안 걸리므로 등재만으로 오탐이 없다.

### A3. `kernel/context.py` — worktree 접두 벗기기
```python
_WORKTREE_PREFIX = (".claude", "worktrees")

def _rel(f: Path) -> str:
    rel = f.relative_to(ROOT).as_posix()
    parts = rel.split("/")
    if len(parts) > 3 and tuple(parts[:2]) == _WORKTREE_PREFIX:
        return "/".join(parts[3:])
    return rel
```
`kernel/runner.py` `_single_file_lists` 의 `rel = p.relative_to(ROOT).as_posix()` 도 `_rel(p)` 호출로 교체한다 — 안 바꾸면 worktree 안 파일이 `.claude/` 접두로 `is_harness_own` 에 걸려 작성 시점 검사가 무음 통과한다(upgrade `gates/rule.py:52-60` 과 같은 수리).

### A4. `kernel/gates/duplication.py` — scratch 제외
`_sources` 루프에:
```python
scratch = profile.scratch()
for path in files:
    rel = _rel(path)
    if scratch and rel.startswith(scratch):
        continue
```
(모듈에 `from kernel import profile` 추가.) 일회성 스크립트 사본이 소거 불가능한 dup baseline 부채가 되는 것을 막는다.

### A5. `kernel/gates/md_style.py` — 계약 격식 표기 수용
```python
ROLE_CONTRACT = re.compile(
    r"^>\s*(?:담는 것|문서 범위):.*(?:담지 않는 것|제외 범위):.*(?:읽는 시점|열람 시점):",
    re.DOTALL)
```
`dev/MD_STANDARD.md` 연결성 표에 계약 격식 표기 행 추가(M11, 묶음 C에서).

### A6. `kernel/gates/md_graph.py` — 함수 참조 매처 축소
```python
_FN_CALL = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\(\s*\)")
```
빈 괄호 표기만 실존 검사한다 — 인자 있는 `MAX(x)`·`var(--x)` 류 함수형 표기의 오탐 공간을 원천 제거(커버리지 대신 신뢰도, upgrade `gates/md.py:273` 주석 근거). `_BUILTIN_CALLS` 는 `range()` 류 방어로 유지.

### A7. `.claude/skills/test/SKILL.md` — 코드펜스 트리 회귀 수정 (S4 포함)
Phase 2 의 디렉토리 트리 코드펜스를 제거하고 대체:
- 배치 실태 정본은 `dev/TESTING.md`, 파일 목록은 Glob — 트리를 여기 복사하지 않는다.
- 미등록 pytest 마커 함정: 마커 설정 없이 `-m <마커>` 를 쓰면 조용히 0개가 선택된다 — 마커는 설정 등재 후에만 쓴다.
- 외부 HTTP 는 `monkeypatch` 로 클라이언트 함수를 스텁한다 — 테스트 편의로 새 의존성(`responses` 등)을 들이지 않는다.

## 묶음 B — 훅·게이트 백포트 (commit 2)

### B1. `.claude/hooks/check_bash_write.py` — `gh pr merge --auto` 차단 (H1)
상수부에 `AUTO_MERGE = "gh pr merge"`, `piped_verdict` 아래에 upgrade `auto_merge()` 함수 그대로(조각 머리 3토큰 + `--auto` 토큰), `main()` 의 verdict 절 다음에:
```python
    if auto_merge(command):
        print(
            "[BASH GATE] `gh pr merge --auto` — branch protection 필수 체크가 없는 레포에서\n"
            "auto 는 기다릴 대상이 없어 즉시 머지한다(기다리는 척만 한다).\n"
            "`gh pr checks <PR>` 을 단독 실행해 pass 를 확인한 뒤 `--auto` 없이 머지하라.",
            file=sys.stderr,
        )
        sys.exit(2)
```

### B2. `.claude/hooks/check_task_residue.py` — 24시간 신선도 유예 (H2)
upgrade 판과 동일: `import time`, `FRESH_SEC = 24*60*60`, `_is_fresh(path, now)`(stat 실패 = fresh), `residue()` 필터에 `and not _is_fresh(path, now)`. 모듈 헤더에 「갓 만든 산출물도 검사하지 않는다」 절 이식(보드 행은 3단계 등록이라 1~2단계 세션을 보드 신호가 못 덮는다 — 이번 세션 실측 포함).

### B3. `.claude/hooks/check_workflow_script.py` — agentType·식별자 opts·매처 (H3)
- `CALL = re.compile(r"(?<![\w.])agent\s*\(")` — `foo.agent(` 배제.
- `MODEL_KEY = re.compile(r"\b(?:model|agentType)\s*:")` — agentType 은 에이전트 정의 frontmatter 가 모델 정본이라 동치.
- upgrade 의 `split_top_level`(최상위 쉼표 분할)과 `_identifier_defines_model` 을 이식하되 **stripped 소스** 위에서 동작시킨다(템플릿의 `strip_noncode` 유지 — 문자열 안 `model:` 오통과가 없는 쪽이 정본).
- `missing_model` → `classify_calls(source) -> tuple[missing, unknown]`: opts 가 `{` 리터럴이면 본문 검색, 식별자면 `re.search(rf"\b{ident}\s*=\s*\{{", code)` 정의부에서 검색, 정의 미발견·비정형이면 unknown. 기존 SPREAD 통과는 unknown 으로 흡수.
- `main()`: missing → exit 2(기존 메시지 + agentType 언급), unknown → 경고 exit 1. record 유지.
- 기존 `tests/test_hooks.py::test_workflow_model_required` 기대값 갱신(스프레드 케이스는 `[]` 유지 — unknown 은 별도 단언).

### B4. `.claude/hooks/check_file_rules.py` — 실패 방향 전환 (H4)
페이로드 파싱 실패와 30초 타임아웃을 exit 2 → **exit 1**. 사유: 복구 수단(Edit)이 차단 대상 그 자체라 fail-closed 가 자기잠금이 되고, Stop 훅 `check_coding_rules` 가 세션 끝에 전량 재검사하는 이중 게이트라 비차단이 구멍이 아니다. `HARNESS.md` ⑨ fail-closed 서술도 같은 턴에 갱신(묶음 C).

### B5. `.claude/hooks/check_ui_copy.py` 신규 + `settings.json` 등록 (H5)
upgrade 판을 기반으로 범용화:
- `origin/main` → `_hookio.default_branch()` (미상이면 통과 처리).
- `frontend/src` → `profile.layer("ui")` (ui 레이어 미선언 시 즉시 exit 0). 테스트 제외 pathspec 은 `:(exclude)<ui>**/*.test.ts` `.test.tsx`.
- `_PROMPT` 는 범용 기준 5종(내부 구현 용어·축약 은어·구어체·번역투·비문)만 남기고, 업종 맥락과 도메인 필수 용어는 프로파일 주입:
```python
# kernel/profile.py 에 추가
UI_COPY: dict[str, object] = dict(getattr(_MOD, "UI_COPY", {})) if _MOD else {}
```
훅에서 `UI_COPY.get("context", "")`(예: "자산운용사 사내 시스템")와 `UI_COPY.get("product_terms", ())`(비위반 처리할 도메인 용어)를 프롬프트에 삽입.
- `utils/claude_cli.py` 의존 제거 — 훅 안에 최소 인라인:
```python
def _call_haiku(prompt: str) -> str:
    done = subprocess.run(["claude", "-p", prompt, "--model", MODEL],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=CALL_TIMEOUT_SEC, shell=False)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip()[:200] or "claude CLI 실패")
    return done.stdout

def _strip_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()
```
- 추출기(`_strip_comments`·`_LITERALS`·`_JSX_TEXT`·`_JSDOC_CONT`·`_TEMPLATE_EXPR`·`_candidate`)와 해시 캐시·fail-open(stderr 고지 후 exit 0)은 원본 그대로.
- 위반 시 안내 문구의 등재처는 `harness_profile.py` `VOCAB["ui_denylist"]` 로 교체.
- `settings.json` Stop 배열 마지막에 등록: `python -X utf8 ".../check_ui_copy.py"`, `timeout: 120`, `statusMessage: "UI copy gate (Haiku)"`.
- Windows 셸 훅이므로 `claude` CLI 부재·미인증은 예외 → fail-open 경로로 흡수된다.

### B6. `kernel/gates/core.py` — 함수 80줄 상한 (G1) + TYPE_CHECKING (G5)
```python
MAX_FUNC_LINES = 80

def check_func_length(files: list[Path]) -> list[str]:
    tests = profile.layer("tests")
    exempt = profile.scratch() + ((tests,) if tests else ())
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        if exempt and rel.startswith(exempt):
            continue
        try:
            tree = ast.parse(f.read_text(encoding=READ_ENC))
        except SyntaxError:
            continue                     # 파싱 실패는 중첩 def 게이트가 보고한다
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                if span > MAX_FUNC_LINES:
                    bad.append(f"{rel}:{node.lineno}: {node.name} {span}줄 (>{MAX_FUNC_LINES})")
    return bad

def check_type_checking_future(files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in files:
        text = f.read_text(encoding=READ_ENC)
        if "if TYPE_CHECKING:" in text and "from __future__ import annotations" not in text:
            bad.append(f"{_rel(f)}: TYPE_CHECKING 블록이 있는데 `from __future__ import "
                       f"annotations` 가 없다 — 3.11 은 어노테이션을 즉시 평가해 NameError")
    return bad
```
runner 등재:
```python
_syntax_section("func_limit", "함수 길이 상한", core.check_func_length, (files,), files, NO_PY),
_entry("type_checking_future", "TYPE_CHECKING↔future annotations 짝", core.check_type_checking_future(files), files, NO_PY),
```

### B7. `kernel/gates/layers.py` — 레이어 규칙 3종 (G2·G7·G8)
```python
_COL_INTERP = re.compile(r'"\{column\}"')
_COL_JOIN = re.compile(r'\.join\(\s*f[\'"]"\{\w+\}".*for\s+\w+\s+in\s+columns')

def check_reads_col_interpolation(files: list[Path]) -> list[str]:
    """읽기 레이어의 컬럼 식별자 raw 보간 — 바인딩으로 못 묶는 자리라 새면 미인증 SQLi 다."""
    reads = profile.layer("read")
    if not reads:
        return []
    allow = tuple(profile.ALLOWLIST["sql_ident"])
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith(reads) or rel in allow:
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            if _COL_INTERP.search(line) or _COL_JOIN.search(line):
                bad.append(f"{rel}:{i}: 컬럼 식별자 raw 보간 — 화이트리스트 헬퍼(quote_col류) 경유. "
                           f"헬퍼 정의 파일은 ALLOWLIST['sql_ident'] 에 등재 — {line.strip()[:70]}")
    return bad

def check_writes_round(files: list[Path]) -> list[str]:
    """쓰기 레이어의 round() — 저장은 원 정밀도, 반올림은 표시 레이어 소관이다."""
    writes = profile.layer("write")
    if not writes:
        return []
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith(writes):
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if re.search(r"\bround\s*\(", line):
                bad.append(f"{rel}:{i}: 적재 값 round() 절삭 — {line.strip()[:60]}")
    return bad

_SELECT_BODY = re.compile(r'(?i)\bSELECT\s+[\w"*,\s.]+\bFROM\b|"""\s*WITH\s+\w+\s+AS\b')

def check_batch_direct_select(files: list[Path]) -> list[str]:
    """배치 레이어의 직접 SELECT — 조회는 읽기 레이어를 경유해 쿼리가 흩어지지 않게 한다."""
    batch = profile.layer("batch")
    read = profile.layer("read")
    if not batch:
        return []
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith(batch):
            continue
        text = f.read_text(encoding=READ_ENC)
        if ".execute(" in text and _SELECT_BODY.search(text):
            bad.append(f"{rel}: 배치 안 직접 SELECT — 조회는 {read or '읽기 레이어'} 경유")
    return bad
```
runner 등재(reads/web 계산부 인접, `batch = _under(files, "batch")` 추가):
```python
_entry("reads_col_interp", "읽기 레이어 컬럼 식별자 raw 보간", layers.check_reads_col_interpolation(files), reads, _need_layer("read")),
_entry("writes_round", "쓰기 레이어 round() 절삭", layers.check_writes_round(files), _under(files, "write"), _need_layer("write")),
_entry("batch_select", "배치 직접 SELECT", layers.check_batch_direct_select(files), batch, _need_layer("batch")),
```
`kernel/profile.py` `_ALLOWLIST_KEYS` 에 `"sql_ident"` 추가, `profiles/_template.py`·프리셋 4종·`harness_profile.py` ALLOWLIST 에 키 추가(빈 튜플).

### B8. `kernel/gates/layers.py` — 해시 네비게이션 단일 기전 (G4)
```python
def check_frontend_hash_nav(ui_files: list[Path]) -> list[str]:
    """한 라우트 안 깊이 이동은 location.hash 대입 하나로 — 이벤트를 안 내는 API 혼용 금지."""
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        text = f.read_text(encoding=READ_ENC)
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("//", "*", "/*", "{/*")):
                continue
            if re.search(r"\bhistory\.pushState\s*\(", line):
                bad.append(f"{rel}:{i}: history.pushState — 깊이 이동은 `location.hash = …` 대입이다. "
                           f"pushState 는 hashchange 를 안 내 복원 리스너가 안 깨어난다")
            if re.search(r"addEventListener\(\s*['\"]popstate['\"]", line):
                bad.append(f"{rel}:{i}: popstate 리스너 — 해시 복원은 hashchange 단일이다. "
                           f"popstate 는 같은 문서 해시 대입에 안 뜬다")
        if "hashchange" in text and "replaceState" in text and "HashChangeEvent" not in text:
            bad.append(f"{rel}: hashchange 복원 + replaceState 정정 조합 — replaceState 는 이벤트를 안 내므로 "
                       f"`window.dispatchEvent(new HashChangeEvent('hashchange'))` 로 직접 깨운다")
    return bad
```
runner: `_entry("hash_nav", "해시 네비게이션 단일 기전", layers.check_frontend_hash_nav(ui_files), ui_files, NO_UI),`

### B9. `kernel/gates/tests_pairing.py` — 프론트 테스트 짝 (G3)
```python
_EXPORT_FN = re.compile(r"^export (?:function|const \w+ = [(<])", re.M)

def check_ui_logic_test_pairing(ui_files: list[Path]) -> list[str]:
    """export 함수가 있는 .ts 는 같은 자리 동명 .test.ts 를 요구한다 — tsc·빌드는 값 오류를 못 잡는다."""
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if f.suffix != ".ts" or rel.endswith((".d.ts", ".test.ts")):
            continue
        if not _EXPORT_FN.search(f.read_text(encoding=READ_ENC)):
            continue
        if not f.with_name(f"{f.stem}.test.ts").exists():
            bad.append(f"{rel}: 대응 행동 테스트 없음 — {f.stem}.test.ts 를 같은 자리에 작성")
    return bad

def check_ui_component_test_pairing(ui_files: list[Path]) -> list[str]:
    """모든 .tsx 는 같은 자리 동명 .test.tsx 렌더 테스트를 요구한다."""
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if f.suffix != ".tsx" or rel.endswith(".test.tsx"):
            continue
        if not f.with_name(f"{f.stem}.test.tsx").exists():
            bad.append(f"{rel}: 대응 렌더 테스트 없음 — {f.stem}.test.tsx 를 같은 자리에 작성")
    return bad
```
(임포트에 `re` 추가.) runner: 
```python
_entry("ui_logic_tests", "프론트 로직 테스트 짝", tests_pairing.check_ui_logic_test_pairing(ui_files), ui_files, NO_UI),
_entry("ui_component_tests", "프론트 컴포넌트 테스트 짝", tests_pairing.check_ui_component_test_pairing(ui_files), ui_files, NO_UI),
```
소급분은 설치 시점 `harness_baseline.txt` 동결로 흡수 — 별도 baseline 파일 없음.

### B10. `kernel/gates/placement.py` — 루트 잡파일 (G9)
```python
def check_root_litter() -> list[str]:
    """루트 직속 파일은 ROOT_FILES 등재분만 — 미추적이라도 ignore 안 된 파일은 커밋 후보다."""
    allow = set(profile.ROOT_FILES) | set(SELF_FILES) | ROOT_INFRA
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, text=True)
    names = {line.strip() for line in out.stdout.splitlines()}
    strays = sorted(n for n in names if n and "/" not in n
                    and n not in allow and (ROOT / n).exists())
    return [f"{n}: 루트 직속 파일 금지 — 읽는 코드의 패키지 안에 두거나, 루트가 맞으면 "
            f"사유와 함께 프로파일 ROOT_FILES 에 등재하라" for n in strays]
```
`ROOT_INFRA` 는 하네스가 만들거나 요구하는 루트 실물(`.gitignore`·`harness_baseline.txt`·`harness_surface.txt`·`harness_trace.jsonl`·`harness_maintenance.json`·`test_pairing_baseline.txt`·`md_style_baseline.txt`·`md_ref_allowlist.txt`) 상수. runner:
```python
_entry("root_litter", "루트 직속 잡파일", placement.check_root_litter(), profile.ROOT_FILES, "설정에 루트 허용 파일을 안 적었음"),
```
프리셋 4종 `ROOT_FILES` 에 통상 루트 실물(README.md·CLAUDE.md·EDITING.md·HARNESS.md·PROJECT.md·DEVGUIDE.md·DESIGN_GUIDE.md·harness_profile.py 류) 기본값 채움. 하네스 자기 프로파일은 현행 `ROOT_FILES = ()` 유지 → 이 레포에선 [SKIP].

### B11. `kernel/gates/prompt_version.py` 신규 (G10)
```python
"""LLM 프롬프트 본문이 바뀌면 첫 줄 `V<major>.<minor>` 를 함께 올려야 한다.

프롬프트 버전은 LLM 산출물이 어느 지침으로 생성됐는지 판정할 유일한 근거다.
대상 파일 목록은 프로파일 VERSIONED_PROMPTS — 비어 있으면 [SKIP]. 원격 기본 브랜치를
못 읽으면(클론 직후·오프라인) 판정 불능이라 빈 목록을 돌려준다.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from kernel import profile
from kernel.context import READ_ENC, ROOT

_VERSION = re.compile(r"V(\d+)\.(\d+)")


def _origin_text(base: str, rel: str) -> str | None:
    done = subprocess.run(["git", "show", f"origin/{base}:{rel}"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return done.stdout if done.returncode == 0 else None


def check_prompt_version() -> list[str]:
    base = _default_branch()
    if base is None:
        return []
    bad: list[str] = []
    for rel in profile.VERSIONED_PROMPTS:
        path = ROOT / rel
        if not path.exists():
            continue
        old = _origin_text(base, rel)
        if old is None:
            continue
        new = path.read_text(encoding=READ_ENC)
        if old == new:
            continue
        old_v = _VERSION.search(old.split("\n", 1)[0])
        new_v = _VERSION.search(new.split("\n", 1)[0])
        if old_v and new_v and old_v.group(0) == new_v.group(0):
            bad.append(f"{rel}: 본문이 바뀌었는데 헤더 버전 {new_v.group(0)} 그대로 — 범프하라")
        if not new_v:
            bad.append(f"{rel}: 첫 줄에 V<major>.<minor> 버전 헤더가 없다")
    return bad
```
(`_default_branch` 는 `origin/HEAD` symbolic-ref → main/master 폴백 — `_hookio.default_branch` 와 같은 판정을 커널 쪽에 둔다.) `kernel/profile.py` 에 `VERSIONED_PROMPTS: tuple[str, ...]` 추가, runner `_doc_sections` 앞에 등재:
```python
_entry("prompt_version", "프롬프트 버전 범프", prompt_version.check_prompt_version(), profile.VERSIONED_PROMPTS, "설정에 버전 관리 프롬프트 목록을 안 적었음"),
```

### B12. 픽스처·골든 갱신
- `tests/fixture_files.py`(정본)에 심는다: 81줄 함수(`utils/long_func.py`), TYPE_CHECKING 위반(`utils/tc_future.py`), `db/reads/` 컬럼 보간, `db/writes/` round, `batches/` 직접 SELECT, 루트 잡파일 1개 + 미니 프론트(`frontend/src/` 아래 export 함수 .ts 1개·.tsx 1개·pushState 1줄) — 미니 프론트는 G3·G4 골든이 [SKIP] 으로 새는 것을 막는 최소 실물이다. 픽스처 프로파일에 `ui`·`batch`·`write` 레이어와 `sql_ident`·`ROOT_FILES` 선언 추가.
- `python -X utf8 tests/run_golden.py --update` (+ `--bare`·`--go`) 로 정답지 재동결. diff 를 눈으로 검수해 의도한 신규 위반만 늘었는지 확인한다.

## 묶음 C — 산문·에이전트·스킬 (commit 3)

| # | 파일 | 변경 |
|---|---|---|
| C1 | `HARNESS.md` 훅 표 아래 | ⚠️ 셸 게이트 매처 규칙 문단 이식(M1 — upgrade `HARNESS.md:26` 문안, 실사고 날짜 포함). 셸 툴이 늘면 매처부터 늘린다 |
| C2 | `HARNESS.md` 「단계」 아래 | 「실패 시 방향」 표 이식(M3) — 파싱 실패·타임아웃 비차단 두 행 포함, ⑨ fail-closed 서술을 B4 방향으로 교체. 「임계 상수」 표 이식(M2 — 5상수 근거 + 토큰 추정식) |
| C3 | `HARNESS.md` 게이트 절 | allowlist=사유 있는 영구 예외 / baseline=소거할 부채 정의 2줄(M4). 신규 게이트·훅(B군) 지도 행 등재 — 검사 28(지도 대조) 통과 요건 |
| C4 | `CLAUDE.md` 증거·경계 원칙 | 9번 추가: 구현·커밋은 자기 worktree에서만 — 공유 체크아웃은 읽기 구역, 첫 편집 전 브랜치·경로 확인(M5) |
| C5 | `CLAUDE.md` 모델 라우팅 | 워커 보고는 증거가 아니다(git·검증·보드는 메인 전담) + 단발 위임 입력은 요약과 경로 + 큰데 순차인 과업은 오케스트레이션 미발동(M6·M7). "깃에 올려라"에 EDITING.md 4번 분기 참조 1줄 |
| C6 | `CLAUDE.md` 라우팅표 | 행 추가: 기존 데이터셋을 새 표·차트·카드에 얹기 전 → `dev/CONVENTIONS.md` 데이터셋 표시 규약 — 순서·라벨은 화면이 정하지 않는다(M8). `dev/CONVENTIONS.md` 에 규약 절 신설(정본) |
| C7 | `EDITING.md` 백로그 절 | 열린 것만 남긴다 + 착수 전 실물 대조 2규칙(M9, upgrade `EDITING.md:71-76` 문안) |
| C8 | `EDITING.md` 3-1 | 트랙별 worktree 예외 절차: 스폰 전 sentinel dirty + `git worktree lock`, 워커 프롬프트에 리터럴 절대경로 재생성 지시(M10). 5번에 deleteBranchOnMerge 1줄 |
| C9 | `dev/MD_STANDARD.md` 연결성 표 | 계약 격식 표기 행(M11) — A5 게이트 수리와 짝 |
| C10 | `.claude/agents/qa.md` + `harness_profile.py` + `profiles/web_fastapi_react.py` | model sonnet→opus, effort medium→high(S2 — 경계면 shape 대조는 판단이라는 실운영 결론). AGENT_MODEL_POLICY 동시 갱신(검사 29 짝) + 「기존 실패는 백로그 참조, 신규 실패만 보고」(S3) + 머리 역할 계약 인용구 |
| C11 | 스킬 6종(lazy 3종·md-audit·review-loop·test)·`product-reviewer.md` | 머리 역할 계약 인용구 1줄씩 복원(S1) |
| C12 | `.claude/skills/feature-workflow/SKILL.md` | Phase 0 에 브리프 3슬롯 복붙 서식(`[브리프] 스코프/노출/데이터`) 추가(S5) |
| C13 | `.claude/skills/review-loop/SKILL.md` | 재검수 요청 서식(이전 판정/반영 수정/수정 후 내용) 추가(S6) |
| C14 | `.claude/agents/product-reviewer.md` | 「나의 관심 영역」 빈 표 골격 + "도메인 확정 시 이 표를 채워라"(S7) |
| C15 | `dev/REJECTED.md` | G6 캐시버스터 제외·㉕A 보류 등재 |
| C16 | `dev/LESSONS.md` | 이번 사고 2건 등재: worktree_residue import 누락(무음 무력화 — 훅도 행동 테스트가 필요하다), 러너 미등재 죽은 게이트(구현≠등재). 각 절 `> 강제:` — 전자는 test_hooks 확장, 후자는 산문 전용(등재 대조 게이트는 러너 자기검사라 재귀 — 사유 기재) |

## 파일 설계표

| 경로 | 책임 1줄 | 규모 |
|---|---|---|
| `.claude/hooks/check_worktree_residue.py` 수정 | import 1줄 | +1 |
| `.claude/hooks/check_bash_write.py` 수정 | auto_merge 절 | +25 |
| `.claude/hooks/check_task_residue.py` 수정 | 신선도 유예 | +20 |
| `.claude/hooks/check_workflow_script.py` 수정 | agentType·식별자 opts 판정 | +45 (총 ~235, 400 여유) |
| `.claude/hooks/check_file_rules.py` 수정 | 실패 방향 exit 1 | ±6 |
| `.claude/hooks/check_ui_copy.py` 신규 | 신규 UI 문구 LLM 감수 Stop 훅 | ~230 |
| `.claude/settings.json` 수정 | Stop 훅 1건 등록 | +8 |
| `kernel/context.py` 수정 | worktree 접두 벗기기 | +6 |
| `kernel/runner.py` 수정 | 신규 게이트 9건 등재 + _rel 교체 | +25 (총 ~424 → **분할 주의**: 등재부가 늘면 `_kernel_sections` 를 코어/레이어로 쪼개는 대신 초과 시 baseline 등재 없이 등재 행 압축 우선. 예상 424줄이라 400 초과 — `_doc_sections`·`_local_sections` 를 `kernel/sections_doc.py` 로 분리해 두 파일 모두 400 미만으로 유지 |
| `kernel/profile.py` 수정 | UI_COPY·VERSIONED_PROMPTS·sql_ident 키 | +8 |
| `kernel/gates/core.py` 수정 | 함수 상한·TYPE_CHECKING | +45 (총 ~350) |
| `kernel/gates/layers.py` 수정 | 레이어 규칙 3종 + 해시 네비 | +90 (총 ~560 → **분할**: 프론트 계열 검사를 `kernel/gates/frontend.py` 로 신설 이동 — 기존 frontend_* 4종 + hash_nav. layers 는 서버 레이어 전용으로 ~400 미만) |
| `kernel/gates/frontend.py` 신규 | 화면 레이어 검사 정본(기존 이동 + hash_nav) | ~230 |
| `kernel/gates/tests_pairing.py` 수정 | ts/tsx 짝 2종 | +35 |
| `kernel/gates/placement.py` 수정 | 루트 잡파일 | +20 |
| `kernel/gates/prompt_version.py` 신규 | 프롬프트 버전 범프 | ~60 |
| `kernel/gates/duplication.py` 수정 | scratch 제외 | +5 |
| `kernel/gates/md_style.py` 수정 | 격식 표기 수용 | ±3 |
| `kernel/gates/md_graph.py` 수정 | 매처 축소 | ±2 |
| `profiles/_template.py`·프리셋 4종 수정 | 신규 키 문서화·기본값 | +10씩 |
| `tests/fixture_files.py` 수정 | 신규 위반 실물 심기 | +60 |
| `tests/test_hooks.py` 수정 | 신규 훅 판정 테스트 | +70 (총 ~250) |
| `tests/golden/*.txt` 재동결 | — | 기계 갱신 |
| MD 11종 (C군) | 산문 이식 | 절 단위 |

## 행동 검증 테스트

| 대상 | 테스트 | 시나리오 |
|---|---|---|
| A1 | `tests/test_hooks.py::test_alive_no_nameerror` | `residue._alive(os.getpid()) is True` — import 누락이면 NameError 가 아니라 False/True 판정 자체가 성립 안 함을 단언(현재 PID 는 참) |
| A3 | `tests/test_hooks.py::test_worktree_rel_strip` | `kernel.context._rel` 에 `.claude/worktrees/x--12345678/db/reads/a.py` → `db/reads/a.py` |
| B1 | `test_auto_merge` | `gh pr merge 12 --auto` 차단 · `git commit -m "gh pr merge --auto 설명"` 통과 · `gh pr merge 12 --merge` 통과 |
| B2 | `test_task_residue_fresh` | mtime 방금 파일 통과 · 25시간 전 파일(os.utime 조작) 검출 |
| B3 | `test_workflow_model_required` 확장 | `agent('p', {agentType:'code-reviewer'})` 통과 · `const O={model:'opus'}; agent('p', O)` 통과 · 미정의 식별자 opts → unknown(경고) · `foo.agent('x')` 무시 |
| B5 | `test_ui_copy_extract` | 추출기 단위 — JSX 텍스트 추출·JSDoc 이어짐 줄 제외·`${}` 마스킹 후 "년 월" 탈락 (LLM 무호출) |
| B6~B11 | `tests/run_golden.py` | 픽스처 위반 각 1건이 정답지에 등장 — 골든 diff 검수 후 재동결. bare·go 골든에서 신규 게이트가 [SKIP]/[N/A] 로 정직하게 찍히는지 확인 |
| A2 | 골든 | miniproj 에 헤더 경로 주석 어긋난 파일 1개 심어 header_path 위반 등장 확인 |

## 트랙 후보

| 트랙 | 내용 | 편집 파일 |
|---|---|---|
| A | 훅 5종 + settings.json + test_hooks.py | `.claude/hooks/*`·`.claude/settings.json`·`tests/test_hooks.py` |
| B | 커널 게이트·프로파일·픽스처·골든 | `kernel/**`·`profiles/*`·`tests/fixture_files.py`·`tests/golden/*` |
| C | MD·에이전트·스킬 산문 | `HARNESS.md`·`CLAUDE.md`·`EDITING.md`·`dev/*`·`.claude/agents/*`·`.claude/skills/*` |

서로소 3트랙이나 **오케스트레이션 미발동** — C 는 A·B 의 결과(게이트 지도 행·⑨ 방향)를 서술해야 해서 순차 의존이고, A·B 합산이 메인 루프 단독으로 충분한 규모다. 커밋 순서 A(수리)→B(백포트)→C(산문)로 직렬 진행.

## 브레이킹 체인지·트레이드오프

- **A6 매처 축소**: 인자 있는 함수 표기(`foo(x)`)의 실존 검사가 사라진다 — 오탐 제거와 맞바꾼 커버리지 축소. 기존 위반 검출분이 골든에서 줄 수 있다(의도된 감소).
- **B4 방향 전환**: ⑨ 의 파싱 실패·타임아웃이 비차단이 된다 — Stop 이중 게이트가 받치므로 실질 구멍 없음. HARNESS.md 서술 동시 교체 필수(안 하면 검사 28 이전에 문서 거짓).
- **B9 프론트 테스트 짝**: clone 해 간 기존 프로젝트에서 위반이 대량 발생할 수 있다 — 설치 시 `harness_baseline.txt` 동결이 흡수(기존 계약 그대로).
- **B5 ui_copy**: Stop 마다 최대 1 LLM 콜(캐시 히트 시 0) — `claude` CLI 미설치 환경은 fail-open 으로 무해. 프롬프트 판정 자체의 정확도는 게이트 하한선이 아니라 보조선.
- **runner·layers 분할**(파일 설계표): import 경로가 바뀌는 소비처는 runner 하나 — grep 으로 확인 후 이동.

## Todo

1. [ ] 묶음 A: A1~A7 수리 + 관련 테스트 → `tests/test_hooks.py`·골든 재동결 → commit 1
2. [ ] 묶음 B 훅: B1~B5 + settings.json + 테스트 → 검증
3. [ ] 묶음 B 커널: B6~B11 + 프로파일 키 + B12 픽스처·골든 → `run_golden` 3종 통과 → commit 2
4. [ ] 묶음 C: C1~C16 산문·에이전트·스킬 + HARNESS.md 지도 행 → 검사 28·29 통과 → commit 3
5. [ ] 전 게이트(`kernel.runner`)·`test_hooks`·`run_golden`(full·bare·go) 최종 3종 초록 확인
6. [ ] research·plan → `docs/tasks/archive/2026-09-07-upgrade-backport-v2/` git mv, `upgrade/` 폴더 처리는 사용자 확인(REJECTED 등재상 역이식 완료 시 삭제 예정)

"""static_check.py — 코딩 규칙 정적 검사기.

CLAUDE.md 실수패턴7 / dev/ARCHITECTURE.md(읽기-쓰기 분리) / dev/NAMING.md(축약 금지) 자동 검사.

검사 항목(기존 6종 + 게이밍 방지 2종 — 이 파일):
  1. 400줄 초과 파일 (전체 추적 .py)
  2. 중첩 def(클로저) — ast 기반, 전 레이어 (scripts/·docs/ 일회성 제외; 2026-07-03 db/reads→전역 확장)
  3. db/reads/*.py 내 쓰기 SQL(CREATE/ALTER/DROP/INSERT/UPDATE/DELETE TABLE) · conn.commit()
  4. 금지 축약어 — 지역변수 `net` 단독 할당 (dict 키 *_net 은 예외)
  4b. 금지 축약어 — `oper_*`/`rev_*` 식별자·dict 키 (NAMING.md ❌ oper/rev — op_*/revenue_* 사용.
      prev_* 는 \b 경계로 미검출. 레거시 web/static·web/templates·scripts·docs 제외; 2026-07-03)
  5. UI 라벨 금칙어 — frontend .tsx/.ts 사용자노출 조어(design/UX.md 자기설명 라벨·조어금지)
  6. py `Any` 타입힌트 때우기 금지 — 게이트 게이밍 방지 (제네릭 래퍼는 ANY_ALLOWLIST / `# any-ok: 사유`)
  7. TS `any` 때우기 금지 — frontend .ts/.tsx (`// any-ok: 사유` 예외; 2026-07-20 harnes 역이식)
  ㉒ py 헤더 경로 주석 일치 — 1행 `# <경로>.py` 가 실경로와 불일치 금지 (docs/·scripts/ 제외;
      db/queries→reads 이사 잔재 33건 실태 — refactor_audit)

P7 확장 게이트(전부 활성 — 래칫 원칙, 정본 관례 dev/CONVENTIONS.md):
  static_check_gates.py: ① get_db 커넥션 내 가공 ② settings 외 os.getenv ③ web await없는 async
        ⑤ get_db import 단일경로 ⑥ 전역 SSL 패치 위치 ⑦ routes 에러 JSONResponse
        ⑧ frontend hex 리터럴(HEX_ALLOWLIST 파일 단위 — 다크/canvas 잔존분) ⑨ 비admin raw fetch
  static_check_md.py: ④A MD 경로 참조 실존(md_ref_allowlist.txt 예외) ④B DEVGUIDE 배치표↔batch_runner
        ④C DEVGUIDE .env↔settings.py  — 산문(의미 서술) 드리프트는 월 1회 /md-audit 스킬이 담당
  static_check_tests.py: ⑫ 수집/계산 모듈 ↔ 행동 테스트 짝(static_check_tests_baseline.txt 래칫 동결)
  static_check_schema.py: ⑭ DDL 저장 타입 잘림 — REAL 금지·NUMERIC 소수 스케일 근거 주석
        (static_check_schema_baseline.txt 래칫 동결)
  static_check_prompt.py: ⑯ LLM 프롬프트 본문↔헤더 버전 동시 갱신 — 생성 시점 프롬프트가 DB 에
        남지 않아 첫 줄 V<major>.<minor> 가 유일한 판정 근거다 (origin/main 대비, 얕은 클론은 생략)
  static_check_krx.py: ⑰ KRX 호출 간격 단일 정본 — pykrx 배치의 `CALL_DELAY` 숫자 재정의·
        `time.sleep` 리터럴 금지. 값이 흩어지면 한 파일만 되돌아가도 IP 차단 방어가 뚫린다
  static_check_complete_date.py: ⑱ 기준일 완전성 — 읽기 경로(db/reads·repository·web)의
        bare MAX(date)/get_latest_date/get_date_range 금지. 부분 수집일이 기준일로 노출되는
        것을 완전일 헬퍼 경유로 강제 (SQL_ALLOWLIST·CALL_ALLOWLIST 래칫)
  static_check_batches.py: ⑲ 배치 직접 SELECT 금지(B13 — 조회는 db/reads 경유) · ㉓ admin 배치
        경로 _BATCH_SCRIPTS 단일(B24). 모듈 내 BASELINE 래칫 — refactor_audit PR 이 소거
  static_check_llm.py: ⑳ LLM 클라이언트 단일 정본(B18) — utils/ 밖 Gemini URL·claude CLI 탐지·
        코드펜스 파싱 재구현 금지 (BASELINE 래칫)
  static_check_region.py: ㉑ region 국내+해외 합산 정본(F16) — frontend 이중 region fetch 는
        utils/regionMerge 경유. 필터 UI 는 FILTER_ALLOWLIST (BASELINE 래칫)
  static_check_api_types.py: ⑮ API 응답 타입의 배열 필드 옵셔널 — 프론트 번들만 먼저 배포된 창에
        undefined 로 도착해 소비처가 런타임 크래시(화면 백지)하는 것을 타입으로 막는다.
        선언부만 보고 소비처는 tsc 에 맡긴다 (static_check_api_array_baseline.txt 래칫 동결)
  static_check_dup.py: ㉔ 단일 정본 리터럴 — peers 로스터 재나열(ROSTER_ALLOWLIST 고정)·
        코스피/코스닥 3항·gnews 접두 분기·KR 블록 라벨 짝(KR_BLOCK_LABEL↔GROUP_ORDER)
        ㉕ web 파라미터 가드 정본 — 인라인 min(max( 클램프·market 검증 3항·admin llm_prompts
        쓰기 직접 호출 금지 (refactor_audit 재발 방지, 2026-08-04)

사용: python static_check.py                (전 게이트 — 위반 있으면 exit 1, Stop 훅 동일)
      python static_check.py --file <경로>  (단일 파일 — PostToolUse 작성시점 훅 check_file_rules.py 경유)
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import static_check_api_types as api_types_gate
import static_check_batches as batches_gate
import static_check_dup as dup_gate
import static_check_complete_date as complete_date_gate
import static_check_gates as gates
import static_check_krx as krx_gate
import static_check_llm as llm_gate
import static_check_md as md
import static_check_md_style as md_style
import static_check_prompt as prompt_gate
import static_check_region as region_gate
import static_check_schema as schema_gate
import static_check_tests as tests_gate

ROOT = Path(__file__).resolve().parent
MAX_LINES = 400
WRITE_SQL = re.compile(
    r"\b(CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|INSERT\s+INTO|UPDATE\s+\w|DELETE\s+FROM)\b",
    re.IGNORECASE,
)
COMMIT = re.compile(r"\.commit\s*\(")
NET_ASSIGN = re.compile(r"^\s*net\s*=")
OPER_REV = re.compile(r"\b(oper|rev)_\w")
ANY_HINT = re.compile(r"[:\[,]\s*Any\b|->\s*Any\b")
TS_ANY = re.compile(r":\s*any\b|\bas\s+any\b|<\s*any\b")

# py Any 허용 파일 — 제네릭 래퍼(coerce·데코레이터·SSE)만 (2026-07-20 게이트 도입 시점 실사).
# 신규 코드는 파일 등재 대신 `# any-ok: 사유` 인라인 예외를 쓴다.
ANY_ALLOWLIST = (
    "db/reads/etf_common.py",
    "batches/equity/pykrx_setup.py",
    "utils/ttl_cache.py",
    "web/admin/_sse.py",
)

# UI 라벨 금칙어 — 사용자에게 노출되는 조어/내부용어(design/UX.md "자기설명 라벨·조어 금지").
# ⚠️ DB컬럼 snake_case(bas_dt·fi_net 등)는 코드 식별자로도 쓰여 자동 광역검사 시 오탐 폭발 →
#    여기엔 '오직 UI 라벨로만 등장하는 한국어 조어'만 등재(코드 식별자와 충돌 없음).
#    리뷰에서 새 조어 발견 시 이 리스트에 그 문자열 그대로 추가하면 다음부터 자동 차단된다.
#    (검사 불가능한 신규 조어는 design 스킬 + 리뷰가 1차 방어 — MD 참조.)
UI_DENYLIST = [
    "순신고가",                                       # → "신고가 − 신저가 누적"(2026-06-29)
    "흡수력", "선점기회", "검증된수요", "단독미투",   # design/UX.md ❌ 마케팅 조어
    # 내부어 — 만든 사람만 아는 말이라 화면에서 걷어냈다(2026-08-04 사용자 지적 "관리자도 사용자다").
    # 무엇으로 바꿔 쓰는지는 docs/tasks/archive/2026-08-04-admin-readability/plan.md 용어표가 정본이다.
    "백필", "미분석 (NULL)", "무결성", "파이프라인",
    "batch_log", "미매핑", "(LIKE)", "낙/비",
]

# 줄 끝 주석(`code;  // 설명`) — 화면 밖이라 UI 금칙어 검사에서 제외한다. `://`(URL)는 주석이 아니다.
TRAILING_COMMENT = re.compile(r"(?<!:)//.*$")


def tracked_py_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True
    )
    # 작업트리에서 삭제됐지만 인덱스에 남은 파일(git status D)은 제외 — 읽기 크래시 방지
    return [
        ROOT / line for line in out.stdout.splitlines()
        if line.strip() and (ROOT / line).exists()
    ]


def tracked_ui_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.tsx", "*.ts"], cwd=ROOT, capture_output=True, text=True
    )
    return [
        ROOT / line for line in out.stdout.splitlines()
        if line.strip().startswith("frontend/src/") and (ROOT / line).exists()
    ]


def check_line_limit(files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in files:
        n = len(f.read_text(encoding="utf-8").splitlines())
        if n > MAX_LINES:
            # as_posix() — 형제 검사 전부가 POSIX 표기다. Windows 역슬래시가 섞이면
            # 위반 경로를 키로 쓰는 소비처(allowlist·baseline 대조)가 조용히 빗나간다.
            bad.append(f"{f.relative_to(ROOT).as_posix()}: {n}줄 (>{MAX_LINES})")
    return bad


_HEADER_PATH = re.compile(r"^#\s+([\w./-]+\.py)\b")


def check_header_path_comment(files: list[Path]) -> list[str]:
    """게이트 ㉒: 1행 `# <경로>.py` 헤더 주석이 실경로와 다르면 위반 (디렉토리 이사 잔재 방지)."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(("docs/", "scripts/")):
            continue
        first = f.read_text(encoding="utf-8").split("\n", 1)[0]
        m = _HEADER_PATH.match(first)
        if m and "/" in m.group(1) and m.group(1) != rel:
            bad.append(f"{rel}: 헤더 주석 '{m.group(1)}' ≠ 실경로 — 주석을 실경로로 갱신")
    return bad


def _nested_defs(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in node.body:
                for sub in ast.walk(child):
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        found.append(f"{node.name} > {sub.name}")
    return found


def check_closures(files: list[Path]) -> list[str]:
    """중첩 def(클로저) 금지 — CLAUDE.md 실수패턴7. 일회성 스크립트(scripts/·docs/)만 제외."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(("scripts/", "docs/")):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            bad.append(f"{rel}: 파싱 실패 {exc}")
            continue
        for pair in _nested_defs(tree):
            bad.append(f"{rel}: 중첩 def {pair}")
    return bad


def check_reads_writes(files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if not rel.startswith("db/reads/"):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if WRITE_SQL.search(line):
                bad.append(f"{rel}:{i}: 쓰기 SQL — {stripped[:60]}")
            if COMMIT.search(line):
                bad.append(f"{rel}:{i}: conn.commit() — {stripped[:60]}")
    return bad


def check_net_abbrev(files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if NET_ASSIGN.match(line):
                bad.append(f"{rel}:{i}: 축약어 변수 net — {line.strip()[:60]}")
    return bad


def check_oper_rev_abbrev(files: list[Path]) -> list[str]:
    """oper_*/rev_* 축약 식별자·키 금지 — NAMING.md. prev_* 는 단어 경계로 자동 제외."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(("scripts/", "docs/")):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if OPER_REV.search(line):
                bad.append(f"{rel}:{i}: 축약어 oper_/rev_ — {stripped[:60]}")
    return bad


def check_ui_jargon(files: list[Path]) -> list[str]:
    """frontend .tsx/.ts 사용자노출 텍스트에 UI 금칙어(조어) 등장 — 주석 줄은 제외(메타 언급 허용)."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            # 주석(금칙어 메타 언급) 제외 — `{/* … */}` JSX 주석도 화면에 안 나온다.
            if stripped.startswith(("//", "*", "/*", "{/*")):
                continue
            # 줄 끝 주석도 화면 밖이다 — `code;  // 설명` 의 설명부는 검사 대상이 아니다.
            # `://`(URL)는 주석이 아니므로 남긴다. 잘라낸 뒤 검사해 오탐을 막는다.
            code = TRAILING_COMMENT.sub("", line)
            for term in UI_DENYLIST:
                if term in code:
                    bad.append(f"{rel}:{i}: UI 금칙어 '{term}' — {stripped[:50]}")
    return bad


def check_py_any(files: list[Path]) -> list[str]:
    """`Any` 타입힌트 때우기 금지 — 타입힌트 게이트 게이밍 방지 (CLAUDE.md 일관성 게이트)."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(("scripts/", "docs/", "tests/", "static_check")) or rel in ANY_ALLOWLIST:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "any-ok" in line or line.lstrip().startswith("#"):
                continue
            if ANY_HINT.search(line):
                bad.append(f"{rel}:{i}: Any 타입힌트 → 구체 타입 (불가피하면 `# any-ok: 사유`)")
    return bad


def check_ts_any(files: list[Path]) -> list[str]:
    """TS `any` 때우기 금지 — tsc strict 도 통과시키는 명시적 any 차단."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "any-ok" in line or line.lstrip().startswith(("//", "*", "/*")):
                continue
            if TS_ANY.search(line):
                bad.append(f"{rel}:{i}: TS any → 구체 타입 (불가피하면 `// any-ok: 사유`)")
    return bad


def _print_style_reports(reports: list[str]) -> None:
    """⑬ 리포트 항목 — 오탐 여지가 있어 total 에 합산하지 않는다(강제 아님)."""
    for report in reports:
        print(f"[REPORT] {report}")


def _print_sections(sections: list[tuple[str, list[str]]]) -> int:
    total = 0
    for title, violations in sections:
        if violations:
            total += len(violations)
            print(f"\n[FAIL] {title} — {len(violations)}건")
            for v in violations:
                print(f"   - {v}")
        else:
            print(f"[OK]   {title}")
    return total


def _build_sections(
    files: list[Path], ui_files: list[Path], include_md: bool, md_files: list[Path]
) -> list[tuple[str, list[str]]]:
    sections = [
        ("400줄 초과", check_line_limit(files)),
        ("중첩 def(클로저) 전 레이어", check_closures(files)),
        ("db/reads 쓰기 SQL/commit", check_reads_writes(files)),
        ("축약어 net 변수", check_net_abbrev(files)),
        ("축약어 oper_/rev_", check_oper_rev_abbrev(files + ui_files)),
        ("UI 라벨 금칙어", check_ui_jargon(ui_files)),
        ("⑩py Any 타입힌트", check_py_any(files)),
        ("⑪frontend TS any", check_ts_any(ui_files)),
        # P7 활성 게이트 (static_check_gates.py)
        ("①get_db 커넥션 내 가공(B4)", gates.check_get_db_processing(files)),
        ("②settings 외 os.getenv(B5)", gates.check_env_access(files)),
        ("③web await없는 async def(B3)", gates.check_web_async_no_await(files)),
        ("⑤get_db import 단일경로(B1)", gates.check_get_db_import_path(files)),
        ("⑥전역 SSL 패치 위치(B6)", gates.check_ssl_bypass_location(files)),
        ("⑦routes 에러 JSONResponse(B2)", gates.check_routes_error_jsonresponse(files)),
        ("⑨frontend 비admin raw fetch(F1)", gates.check_frontend_raw_fetch(ui_files)),
        ("⑧frontend hex 리터럴(F2)", gates.check_frontend_hex(ui_files)),
        ("⑫수집/계산 모듈 행동 테스트 짝(B20)", tests_gate.check_module_test_pairing(files)),
        ("⑭DDL 저장 타입 잘림(B21)", schema_gate.check_ddl_lossy_types(files)),
        ("⑮API 응답 배열 필드 옵셔널(F3)", api_types_gate.check_api_array_optional(ui_files)),
        ("⑰KRX 호출 간격 단일 정본(B22)", krx_gate.check_krx_call_pacing(files)),
        ("⑱기준일 완전성(B23)", complete_date_gate.check_bare_latest_date(files)),
        ("⑲배치 직접 SELECT 금지(B13)", batches_gate.check_batches_direct_select(files)),
        ("⑳LLM 클라이언트 단일 정본(B18)", llm_gate.check_llm_single_client(files)),
        ("㉑region 합산 정본 경유(F16)", region_gate.check_region_merge_source(ui_files)),
        ("㉒py 헤더 경로 주석 일치", check_header_path_comment(files)),
        ("㉓admin 배치 경로 레지스트리(B24)", batches_gate.check_admin_batch_paths(files)),
        ("㉔단일 정본 리터럴(로스터·라벨·분기)", dup_gate.check_single_source_literals(files, ui_files)),
        ("㉕web 파라미터 가드 정본(clamp·market·프롬프트CRUD)",
         dup_gate.check_web_param_guards(files) + dup_gate.check_admin_prompt_crud(files)),
    ]
    if md_files:
        hard, soft = md_style.check_md_style(md_files)
        sections.append(("⑬ MD 작성 규칙(dev/MD_STANDARD.md)", hard))
        _print_style_reports(soft)
    if include_md:
        # 2026-07-17 P4·P6 완료 커밋에서 활성 전환 (래칫 — 게이트 없는 정리는 재발한다)
        sections += [
            ("④A MD 경로 참조 실존", md.check_md_path_refs()),
            ("④B 배치 스케줄(DEVGUIDE↔batch_runner)", md.check_batch_schedule()),
            ("④C .env 키(DEVGUIDE↔settings)", md.check_env_keys()),
            ("④D 고아 MD(허브 도달 불가)", md.check_md_orphans()),
            ("④E 하네스 지도 대조(HARNESS↔실물)", md.check_harness_map()),
            ("⑯프롬프트 본문↔헤더 버전", prompt_gate.check_prompt_version_bump()),
        ]
    return sections


def tracked_md_files() -> list[Path]:
    """게이트 ⑬ 대상 — 추적 중인 .md 중 스타일 검사 스코프에 드는 것."""
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True)
    return [ROOT / rel for rel in out.stdout.split()
            if md_style.style_target(rel) and (ROOT / rel).is_file()]


def _single_file_lists(raw_path: str) -> tuple[list[Path], list[Path], bool, list[Path]]:
    """--file 모드: 대상 파일 하나를 (py, ui, md전역검사여부, md스타일대상)으로 분류."""
    p = Path(raw_path).resolve()
    try:
        rel = p.relative_to(ROOT).as_posix()
    except ValueError:
        return [], [], False, []
    if not p.exists() or rel.startswith(("harness/", "idea/", "web/static/", "web/templates/")):
        return [], [], False, []
    if p.suffix == ".py":
        return [p], [], False, []
    if p.suffix in (".ts", ".tsx") and rel.startswith("frontend/src/"):
        return [], [p], False, []
    if p.suffix == ".md":
        # ④A~E 는 전역 교차검사라 정본 MD 편집 시에만 재실행. ⑬ 스타일은 그 파일만.
        style = [p] if md_style.style_target(rel) else []
        return [], [], not rel.startswith((".claude/", "docs/")), style
    return [], [], False, []


def main() -> int:
    # Windows cp949 콘솔에서 위반 라인(유니코드 포함) 출력 크래시 방지
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(errors="replace")
    if len(sys.argv) >= 3 and sys.argv[1] == "--file":
        files, ui_files, include_md, md_files = _single_file_lists(sys.argv[2])
        if not files and not ui_files and not include_md and not md_files:
            return 0
    else:
        files, ui_files, include_md = tracked_py_files(), tracked_ui_files(), True
        md_files = tracked_md_files()
    total = _print_sections(_build_sections(files, ui_files, include_md, md_files))

    if total:
        print(f"\n총 {total}건 위반 (활성 게이트).")
        return 1
    print("\n활성 게이트 모두 통과.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

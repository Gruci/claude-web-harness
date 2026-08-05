"""kernel/gates/core.py — 언어·파일 단위 코어 게이트.

레이어 구조를 모르는 검사만 모았다. 어느 프로젝트에서든 같은 뜻이라, 프로파일이 주는 것은
어휘(금칙어·축약어)와 면제 목록뿐이고 판정 로직은 그대로 쓴다.

  1  파일 400줄 초과 — 단일 책임을 잃은 파일. 상한이지 목표가 아니다
  2  중첩 def(클로저) — 테스트 불가능한 숨은 로직
  3  읽기 레이어의 쓰기 SQL·commit — 읽기 레이어의 부작용
  4  축약어 단독 변수 · 4b 축약 접두 식별자
  5  UI 라벨 금칙어 — 사용자에게 노출되는 조어
  ⑩  py Any 타입힌트 · ⑪ TS any — 타입으로 게이트 때우기
  ㉒  py 헤더 경로 주석 일치 — 파일 이사 후 남은 잘못된 경로 주석
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from kernel.context import ROOT

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

READ_LAYER = "db/reads/"

# py Any 허용 파일 — 제네릭 래퍼(coerce·데코레이터·SSE)만.
# 신규 코드는 파일 등재 대신 `# any-ok: 사유` 인라인 예외를 쓴다.
ANY_ALLOWLIST = (
    "db/reads/etf_common.py",
    "batches/equity/pykrx_setup.py",
    "utils/ttl_cache.py",
    "web/admin/_sse.py",
)

# UI 라벨 금칙어 — 사용자에게 노출되는 조어·내부용어.
# ⚠️ DB컬럼 snake_case 는 코드 식별자로도 쓰여 자동 광역검사 시 오탐 폭발 →
#    '오직 UI 라벨로만 등장하는 한국어 조어'만 등재한다(코드 식별자와 충돌 없음).
UI_DENYLIST = [
    "순신고가",
    "흡수력", "선점기회", "검증된수요", "단독미투",
    "백필", "미분석 (NULL)", "무결성", "파이프라인",
    "batch_log", "미매핑", "(LIKE)", "낙/비",
]

# 줄 끝 주석(`code;  // 설명`) — 화면 밖이라 UI 금칙어 검사에서 제외한다. `://`(URL)는 주석이 아니다.
TRAILING_COMMENT = re.compile(r"(?<!:)//.*$")

SCRATCH_PREFIXES = ("scripts/", "docs/")

_HEADER_PATH = re.compile(r"^#\s+([\w./-]+\.py)\b")


def check_line_limit(files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in files:
        n = len(f.read_text(encoding="utf-8").splitlines())
        if n > MAX_LINES:
            # as_posix() — 형제 검사 전부가 POSIX 표기다. Windows 역슬래시가 섞이면
            # 위반 경로를 키로 쓰는 소비처(allowlist·baseline 대조)가 조용히 빗나간다.
            bad.append(f"{f.relative_to(ROOT).as_posix()}: {n}줄 (>{MAX_LINES})")
    return bad


def check_header_path_comment(files: list[Path]) -> list[str]:
    """게이트 ㉒: 1행 `# <경로>.py` 헤더 주석이 실경로와 다르면 위반 (디렉토리 이사 잔재 방지)."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(SCRATCH_PREFIXES):
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
    """중첩 def(클로저) 금지. 일회성 스크립트만 제외."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(SCRATCH_PREFIXES):
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
        if not rel.startswith(READ_LAYER):
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
    """축약 식별자·키 금지. prev_* 는 단어 경계로 자동 제외."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(SCRATCH_PREFIXES):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if OPER_REV.search(line):
                bad.append(f"{rel}:{i}: 축약어 oper_/rev_ — {stripped[:60]}")
    return bad


def check_ui_jargon(files: list[Path]) -> list[str]:
    """프론트 사용자노출 텍스트에 UI 금칙어(조어) 등장 — 주석 줄은 제외(메타 언급 허용)."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            # 주석(금칙어 메타 언급) 제외 — `{/* … */}` JSX 주석도 화면에 안 나온다.
            if stripped.startswith(("//", "*", "/*", "{/*")):
                continue
            # 줄 끝 주석도 화면 밖이다. `://`(URL)는 주석이 아니므로 남긴다.
            code = TRAILING_COMMENT.sub("", line)
            for term in UI_DENYLIST:
                if term in code:
                    bad.append(f"{rel}:{i}: UI 금칙어 '{term}' — {stripped[:50]}")
    return bad


def check_py_any(files: list[Path]) -> list[str]:
    """`Any` 타입힌트 때우기 금지 — 타입힌트 게이트 게이밍 방지."""
    bad: list[str] = []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(SCRATCH_PREFIXES + ("tests/", "kernel/")) or rel in ANY_ALLOWLIST:
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

"""kernel/gates/core.py — 언어·파일 단위 코어 게이트.

레이어 구조를 모르는 검사만 모았다. 프로젝트에서 받는 것은 어휘(금칙어·축약어)와 면제 목록뿐이고
판정 로직은 어느 프로젝트에서든 같다.

  파일 길이 상한   단일 책임을 잃은 파일. 상한이지 목표가 아니다
  중첩 def         테스트할 수 없는 숨은 로직
  읽기 레이어 쓰기 읽기 전용 레이어의 부작용
  축약 이름·접두   내부 코드가 이름으로 새는 것
  UI 라벨 금칙어   사용자에게 노출되는 조어
  Any / any        타입으로 게이트 때우기
  헤더 경로 주석   파일 이사 후 남은 잘못된 경로 주석
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from kernel import profile
from kernel.context import ROOT, _rel

MAX_LINES = 400

WRITE_SQL = re.compile(
    r"\b(CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|INSERT\s+INTO|UPDATE\s+\w|DELETE\s+FROM)\b",
    re.IGNORECASE,
)
COMMIT = re.compile(r"\.commit\s*\(")
ANY_HINT = re.compile(r"[:\[,]\s*Any\b|->\s*Any\b")
TS_ANY = re.compile(r":\s*any\b|\bas\s+any\b|<\s*any\b")

# 줄 끝 주석(`code;  // 설명`) — 화면 밖이라 UI 금칙어 검사에서 제외한다. `://`(URL)는 주석이 아니다.
TRAILING_COMMENT = re.compile(r"(?<!:)//.*$")

_HEADER_PATH = re.compile(r"^#\s+([\w./-]+\.py)\b")


def _alt(words: tuple[str, ...]) -> str:
    return "|".join(re.escape(w) for w in words)


def _abbrev_name_re() -> re.Pattern[str] | None:
    names = profile.VOCAB["abbrev_names"]
    return re.compile(rf"^\s*({_alt(names)})\s*=") if names else None


def _abbrev_prefix_re() -> re.Pattern[str] | None:
    prefixes = profile.VOCAB["abbrev_prefixes"]
    return re.compile(rf"\b({_alt(prefixes)})\w") if prefixes else None


def _is_scratch(rel: str) -> bool:
    scratch = profile.scratch()
    return bool(scratch) and rel.startswith(scratch)


def check_line_limit(files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in files:
        n = len(f.read_text(encoding="utf-8").splitlines())
        if n > MAX_LINES:
            # as_posix() — 형제 검사 전부가 POSIX 표기다. Windows 역슬래시가 섞이면
            # 위반 경로를 키로 쓰는 소비처(allowlist·baseline 대조)가 조용히 빗나간다.
            bad.append(f"{_rel(f)}: {n}줄 (>{MAX_LINES})")
    return bad


def check_header_path_comment(files: list[Path]) -> list[str]:
    """1행 `# <경로>.py` 헤더 주석이 실경로와 다르면 위반 (디렉토리 이사 잔재 방지)."""
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        if _is_scratch(rel):
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
        rel = _rel(f)
        if _is_scratch(rel):
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
    """읽기 전용 레이어에 쓰기 SQL·commit 이 있으면 위반."""
    read_layer = profile.layer("read")
    if not read_layer:
        return []
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith(read_layer):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if WRITE_SQL.search(line):
                bad.append(f"{rel}:{i}: 쓰기 SQL — {stripped[:60]}")
            if COMMIT.search(line):
                bad.append(f"{rel}:{i}: commit() — {stripped[:60]}")
    return bad


def check_abbrev_names(files: list[Path]) -> list[str]:
    """금지 축약 이름의 단독 대입."""
    pattern = _abbrev_name_re()
    if pattern is None:
        return []
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            m = pattern.match(line)
            if m:
                bad.append(f"{rel}:{i}: 축약어 변수 {m.group(1)} — {line.strip()[:60]}")
    return bad


def check_abbrev_prefixes(files: list[Path]) -> list[str]:
    """금지 축약 접두를 쓴 식별자·키. 단어 경계라 `prev_` 같은 우연 일치는 걸리지 않는다."""
    pattern = _abbrev_prefix_re()
    if pattern is None:
        return []
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        if _is_scratch(rel):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            m = pattern.search(line)
            if m:
                bad.append(f"{rel}:{i}: 축약 접두 {m.group(1)} — {stripped[:60]}")
    return bad


def check_ui_jargon(files: list[Path]) -> list[str]:
    """프론트 사용자노출 텍스트에 금칙어 등장 — 주석 줄은 제외(메타 언급 허용)."""
    denylist = profile.VOCAB["ui_denylist"]
    if not denylist:
        return []
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            # 주석(금칙어 메타 언급) 제외 — `{/* … */}` JSX 주석도 화면에 안 나온다.
            if stripped.startswith(("//", "*", "/*", "{/*")):
                continue
            # 줄 끝 주석도 화면 밖이다. `://`(URL)는 주석이 아니므로 남긴다.
            code = TRAILING_COMMENT.sub("", line)
            for term in denylist:
                if term in code:
                    bad.append(f"{rel}:{i}: UI 금칙어 '{term}' — {stripped[:50]}")
    return bad


def check_py_any(files: list[Path]) -> list[str]:
    """`Any` 타입힌트 때우기 금지 — 타입 게이트 게이밍 방지."""
    allow = tuple(profile.ALLOWLIST["py_any"])
    tests = profile.layer("tests")
    # 커널 자신은 늘 제외 — 게이트 설명 문자열이 자기 패턴에 걸린다.
    exempt = profile.scratch() + ("kernel/",) + ((tests,) if tests else ())
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        if rel.startswith(exempt) or rel in allow:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "any-ok" in line or line.lstrip().startswith("#"):
                continue
            if ANY_HINT.search(line):
                bad.append(f"{rel}:{i}: Any 타입힌트 → 구체 타입 (불가피하면 `# any-ok: 사유`)")
    return bad


def check_ts_any(files: list[Path]) -> list[str]:
    """TS `any` 때우기 금지 — 타입체커 strict 도 통과시키는 명시적 any 차단."""
    bad: list[str] = []
    for f in files:
        rel = _rel(f)
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "any-ok" in line or line.lstrip().startswith(("//", "*", "/*")):
                continue
            if TS_ANY.search(line):
                bad.append(f"{rel}:{i}: TS any → 구체 타입 (불가피하면 `// any-ok: 사유`)")
    return bad

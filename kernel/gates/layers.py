"""kernel/gates/layers.py — 레이어 관례 게이트.

"읽기 레이어는 커넥션을 쥔 채 가공하지 않는다" 같은 규칙의 **형태**만 여기 있다. 그 레이어가
어디이고 커넥션 헬퍼 이름이 무엇인지는 전부 프로파일이 정한다. 선언이 없으면 판정하지 않고,
러너가 그 섹션을 [SKIP] 으로 찍는다.

  읽기 레이어 쓰기      읽기 전용 레이어의 부작용
  커넥션 블록 내 가공   커넥션을 쥔 채 집계 — 점유 시간이 늘어난다
  설정 밖 환경변수      환경변수를 읽는 지점이 흩어지는 것
  await 없는 async      비동기인 척하는 동기 핸들러
  접근자 import 경로    같은 헬퍼를 두 경로로 부르는 것
  전역 SSL 패치 위치    검증 우회가 아무 데서나 켜지는 것
  라우트 에러 응답      에러 응답 형식이 라우트마다 다른 것
  컬럼 식별자 보간      바인딩 불가 자리의 f-string — 새면 미인증 SQLi
  쓰기 레이어 round     적재 정밀도 절삭 — 반올림은 표시 레이어 소관
  배치 직접 SELECT      조회가 배치마다 흩어지는 것

화면 레이어 규칙은 frontend.py 다 — 파일 400줄 상한 앞에서 기능 단위로 갈랐다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from kernel import profile
from kernel.context import READ_ENC, _rel


def _under(rel: str, layer_name: str) -> bool:
    prefix = profile.layer(layer_name)
    return bool(prefix) and rel.startswith(prefix)


def _parse(f: Path) -> ast.AST | None:
    try:
        return ast.parse(f.read_text(encoding=READ_ENC))
    except SyntaxError:
        return None


# ── 읽기 레이어의 쓰기 SQL·commit ─────────────────────────────────────────────

WRITE_SQL = re.compile(
    r"\b(CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|INSERT\s+INTO|UPDATE\s+\w|DELETE\s+FROM)\b",
    re.IGNORECASE,
)
COMMIT = re.compile(r"\.commit\s*\(")


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
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if WRITE_SQL.search(line):
                bad.append(f"{rel}:{i}: 쓰기 SQL — {stripped[:60]}")
            if COMMIT.search(line):
                bad.append(f"{rel}:{i}: commit() — {stripped[:60]}")
    return bad


# ── 커넥션 블록 내 가공 ────────────────────────────────────────────────────────
#
# 허용: 커넥션 블록 안은 fetch 만 — execute().fetchall() 과 그 단순 대입, 파라미터 조립.
# 위반: 블록 안 중첩 루프(For/While 안의 For/While) = 커넥션 점유 중 집계.
# 이것이 in-connection 가공의 유일하게 확실한 AST 신호다. comprehension 은 SQL 조립(정상)과
# fetch 결과 가공(위반)이 AST 로 구분되지 않아 검출하지 않는다 — 게이트는 확실한 위반만 잡는다.


def _is_accessor_with(node: ast.With, accessor: str) -> bool:
    for item in node.items:
        expr = item.context_expr
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) \
                and expr.func.id == accessor:
            return True
    return False


def _has_nested_loop(body: list[ast.stmt]) -> bool:
    for stmt in body:
        for sub in ast.walk(stmt):
            if isinstance(sub, (ast.For, ast.While)):
                for inner in ast.walk(sub):
                    if inner is not sub and isinstance(inner, (ast.For, ast.While)):
                        return True
    return False


def check_connection_processing(py_files: list[Path]) -> list[str]:
    accessor = profile.symbol("db_accessor")
    if not accessor:
        return []
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not _under(rel, "db"):
            continue
        tree = _parse(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.With) and _is_accessor_with(node, accessor) \
                    and _has_nested_loop(node.body):
                bad.append(f"{rel}:{node.lineno}: 커넥션 블록 내 중첩 루프 집계 — "
                           f"fetch 후 블록 밖에서 가공하라")
    return bad


# ── 설정 밖 환경변수 ───────────────────────────────────────────────────────────


def check_env_access(py_files: list[Path]) -> list[str]:
    """설정 모듈 밖에서 환경변수를 읽는 것. 읽는 방법은 언어마다 다르므로 패턴은 언어팩이 준다."""
    settings = profile.FILES.get("settings")
    pattern = profile.pattern("env_read")
    if not settings or not pattern:
        return []
    env_re = re.compile(pattern)
    comment = profile.pattern("comment") or "#"
    allow = tuple(profile.ALLOWLIST["env_access"])
    tests = profile.layer("tests")
    exempt = profile.scratch() + ("kernel/",) + ((tests,) if tests else ())
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if rel == settings or rel.startswith(exempt) or rel in allow:
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(comment):
                continue
            if env_re.search(line):
                bad.append(f"{rel}:{i}: {settings} 밖에서 환경변수 조회 — {stripped[:60]}")
    return bad


# ── await 없는 async ───────────────────────────────────────────────────────────
#
# 핸들러는 동기 def 가 기본이고, async 는 본문에 실제 await 가 있을 때만이다.
# 제외: async generator(yield 보유 — 스트리밍 핸들러는 def 로 못 바꾼다).


def _async_has_await(node: ast.AsyncFunctionDef) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Await, ast.AsyncFor, ast.AsyncWith)):
            return True
    return False


def _is_async_generator(node: ast.AsyncFunctionDef) -> bool:
    for sub in ast.walk(node):
        # 중첩 함수 내부 yield 는 제외 — 이 함수 자신 스코프의 yield 만
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub is not node:
            continue
        if isinstance(sub, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _returns_stream(node: ast.AsyncFunctionDef) -> bool:
    ann = node.returns
    name = ""
    if isinstance(ann, ast.Name):
        name = ann.id
    elif isinstance(ann, ast.Attribute):
        name = ann.attr
    return name.endswith("StreamingResponse") or name == "EventSourceResponse"


def check_web_async_no_await(py_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not _under(rel, "web"):
            continue
        tree = _parse(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            if _async_has_await(node) or _is_async_generator(node) or _returns_stream(node):
                continue
            bad.append(f"{rel}:{node.lineno}: await 없는 async def '{node.name}' — 동기 def 로")
    return bad


# ── 접근자 import 단일 경로 ────────────────────────────────────────────────────


def check_accessor_import_path(py_files: list[Path]) -> list[str]:
    """커넥션 헬퍼를 정본 모듈에서만 import 하는지. 재수출 경유는 호출 경로를 갈라놓는다."""
    accessor = profile.symbol("db_accessor")
    canonical = profile.symbol("db_accessor_module")
    if not accessor or not canonical:
        return []
    import_re = re.compile(rf"\bimport\b.*\b{re.escape(accessor)}\b")
    canonical_re = re.compile(rf"from\s+\.*{re.escape(canonical)}\s+import")
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not (_under(rel, "read") or _under(rel, "write")):
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or not import_re.search(line):
                continue
            if not canonical_re.search(line) and "from ." not in line:
                bad.append(f"{rel}:{i}: {accessor} 를 {canonical} 밖에서 import — {stripped[:50]}")
    return bad


# ── 전역 SSL 패치 위치 ─────────────────────────────────────────────────────────


def check_ssl_bypass_location(py_files: list[Path]) -> list[str]:
    """전역 SSL 패치는 배치·스크립트 진입점에서만. 상시 import 되는 모듈에서 켜면 전역 전파된다."""
    bypass = profile.symbol("ssl_bypass")
    if not bypass:
        return []
    call_re = re.compile(rf"\b{re.escape(bypass)}\s*\(")
    home = profile.FILES.get("ssl_util")
    batch = profile.layer("batch")
    allowed = profile.scratch() + ("kernel/",) + ((batch,) if batch else ())
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if rel.startswith(allowed) or rel == home:
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if call_re.search(line):
                bad.append(f"{rel}:{i}: 전역 SSL 패치를 진입점 밖에서 호출 — {stripped[:50]}")
    return bad


# ── 라우트 에러 응답 형식 ──────────────────────────────────────────────────────


def check_routes_error_response(py_files: list[Path]) -> list[str]:
    """에러는 예외로 올린다. 성공 응답용 래퍼(상태코드 없음·2xx)는 위반이 아니다."""
    wrapper = profile.symbol("error_response")
    if not wrapper:
        return []
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not _under(rel, "routes"):
            continue
        tree = _parse(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name != wrapper:
                continue
            for kw in node.value.keywords:
                if kw.arg == "status_code" and isinstance(kw.value, ast.Constant) \
                        and isinstance(kw.value.value, int) and kw.value.value >= 400:
                    bad.append(f"{rel}:{node.lineno}: 에러를 {wrapper}(status "
                               f"{kw.value.value}) 로 반환 — 예외로 올려라")
    return bad


# ── 읽기 레이어의 컬럼 식별자 raw 보간 ─────────────────────────────────────────
#
# 파라미터 바인딩으로 못 묶는 식별자 자리라, 유저 입력 column/columns 가 f-string 으로
# 새면 미인증 SQLi 다(원류 보안감사 Critical). 화이트리스트 헬퍼(quote_col 류) 경유를
# 강제하고, 헬퍼 자신의 정의 파일은 ALLOWLIST["sql_ident"] 로 뺀다.

_COL_INTERP = re.compile(r'"\{column\}"')
_COL_JOIN = re.compile(r'\.join\(\s*f[\'"]"\{\w+\}".*for\s+\w+\s+in\s+columns')


def check_reads_col_interpolation(py_files: list[Path]) -> list[str]:
    reads = profile.layer("read")
    if not reads:
        return []
    allow = tuple(profile.ALLOWLIST["sql_ident"])
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not rel.startswith(reads) or rel in allow:
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _COL_INTERP.search(line) or _COL_JOIN.search(line):
                bad.append(f"{rel}:{i}: 컬럼 식별자 raw 보간 — 바인딩 불가 자리라 새면 SQLi 다. "
                           f"화이트리스트 헬퍼(quote_col 류) 경유, 헬퍼 정의 파일은 "
                           f"ALLOWLIST['sql_ident'] 등재 — {stripped[:60]}")
    return bad


# ── 쓰기 레이어의 round() 절삭 ─────────────────────────────────────────────────

_ROUND_RE = re.compile(r"\bround\s*\(")


def check_writes_round(py_files: list[Path]) -> list[str]:
    """적재 직전 round() — 저장은 원 정밀도, 반올림은 표시 레이어 소관이다.

    DDL 타입의 정밀도 잘림은 ddl_types 게이트가 막는다 — 이 규칙이 그 나머지 절반이다.
    """
    writes = profile.layer("write")
    if not writes:
        return []
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not rel.startswith(writes):
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _ROUND_RE.search(line):
                bad.append(f"{rel}:{i}: 적재 값 round() 절삭 — 저장은 원 정밀도, 반올림은 "
                           f"표시 레이어에서 — {stripped[:60]}")
    return bad


# ── 배치 레이어의 직접 SELECT ──────────────────────────────────────────────────

_SELECT_BODY = re.compile(r'(?i)\bSELECT\s+[\w"*,\s.]+\bFROM\b|"""\s*WITH\s+\w+\s+AS\b')


def check_batch_direct_select(py_files: list[Path]) -> list[str]:
    """배치 안 직접 SELECT — 조회가 배치마다 흩어지지 않게 읽기 레이어를 경유시킨다."""
    batch = profile.layer("batch")
    if not batch:
        return []
    read = profile.layer("read")
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not rel.startswith(batch):
            continue
        text = f.read_text(encoding=READ_ENC)
        if ".execute(" in text and _SELECT_BODY.search(text):
            bad.append(f"{rel}: 배치 안 직접 SELECT — 조회는 {read or '읽기 레이어'} 경유")
    return bad

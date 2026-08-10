"""kernel/gates/layers.py — 레이어 관례 게이트.

"읽기 레이어는 커넥션을 쥔 채 가공하지 않는다" 같은 규칙의 **형태**만 여기 있다. 그 레이어가
어디이고 커넥션 헬퍼 이름이 무엇인지는 전부 프로파일이 정한다. 선언이 없으면 판정하지 않고,
러너가 그 섹션을 [SKIP] 으로 찍는다.

  커넥션 블록 내 가공   커넥션을 쥔 채 집계 — 점유 시간이 늘어난다
  설정 밖 환경변수      환경변수를 읽는 지점이 흩어지는 것
  await 없는 async      비동기인 척하는 동기 핸들러
  접근자 import 경로    같은 헬퍼를 두 경로로 부르는 것
  전역 SSL 패치 위치    검증 우회가 아무 데서나 켜지는 것
  라우트 에러 응답      에러 응답 형식이 라우트마다 다른 것
  프론트 raw fetch      캐시·에러 처리 없는 직접 호출
  프론트 hex 리터럴     색 하드코딩 — 토큰·팔레트 우회
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from kernel import profile
from kernel.context import READ_ENC, _rel

_FETCH_RE = re.compile(r"\bfetch\s*\(|\baxios\b")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_RGB_HSL_RE = re.compile(r"\brgba?\s*\(|\bhsla?\s*\(")   # hex 게이트 우회 경로를 같이 막는다
_ENV_RE = re.compile(r"\bos\.(getenv|environ)\b")

# max-width·min-width 는 반응형의 상한·하한이라 정상이다. 뒤돌아보기로 그것만 제외한다.
_FIXED_WIDTH_RE = re.compile(r"(?<![-\w])width\s*:\s*['\"]?\d{3,}px")
_VIEWPORT_VW_RE = re.compile(r"\b100vw\b")
_BROWSER_API_RE = re.compile(r"\b(localStorage|sessionStorage|document\.|window\.)")

_JS_COMMENT = ("//", "*", "/*", "{/*")


def _under(rel: str, layer_name: str) -> bool:
    prefix = profile.layer(layer_name)
    return bool(prefix) and rel.startswith(prefix)


def _parse(f: Path) -> ast.AST | None:
    try:
        return ast.parse(f.read_text(encoding=READ_ENC))
    except SyntaxError:
        return None


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


# ── 프론트 ─────────────────────────────────────────────────────────────────────


def _is_admin_ui(rel: str) -> bool:
    admin = profile.layer("ui_admin")
    return bool(admin) and (rel.startswith(admin) or "/admin/" in rel)


def check_frontend_raw_fetch(ui_files: list[Path]) -> list[str]:
    """공용 래퍼를 거치지 않는 직접 호출. 쓰기·비2xx 시맨틱이 필요하면 프로파일에 사유와 함께 등재."""
    allow = tuple(profile.ALLOWLIST["ui_fetch"]) + tuple(profile.ALLOWLIST["ui_fetch_wrappers"])
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if _is_admin_ui(rel) or rel in allow:
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue
            if _FETCH_RE.search(line):
                bad.append(f"{rel}:{i}: 공용 래퍼를 거치지 않는 fetch() — {stripped[:50]}")
    return bad


def check_frontend_hex(ui_files: list[Path]) -> list[str]:
    """색 하드코딩. 토큰 정본이 선언돼 있으면 메시지가 그 파일을 가리킨다."""
    allow = tuple(profile.ALLOWLIST["ui_hex"])
    tokens = profile.layer_raw("ui_tokens")
    where = f"{tokens} 또는 CSS 변수" if tokens else "토큰 정본 또는 CSS 변수"
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if _is_admin_ui(rel) or rel in allow or (tokens and rel == tokens):
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue
            for m in _HEX_RE.finditer(line):
                bad.append(f"{rel}:{i}: hex 리터럴 {m.group(0)} — {where} 로")
            if _RGB_HSL_RE.search(line):
                bad.append(f"{rel}:{i}: rgb()·hsl() 색 리터럴 — {where} 로")
    return bad


def check_frontend_responsive(ui_files: list[Path]) -> list[str]:
    """폰을 깨뜨리는 두 원인. 만든 뒤 고치면 재작업이고 저장 시점에 막으면 그냥 작성이다.

    고정 px 폭은 좁은 화면에서 가로 스크롤을 만들고, `100vw` 는 스크롤바 폭만큼 넘쳐서
    세로 스크롤이 있는 페이지면 반드시 가로로도 넘친다.
    """
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if _is_admin_ui(rel):
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if "px-ok" in line or stripped.startswith(_JS_COMMENT):
                continue
            if _FIXED_WIDTH_RE.search(line):
                bad.append(f"{rel}:{i}: 고정 px 폭 — max-width·%·minmax·clamp 로 "
                           f"(불가피하면 `// px-ok: 사유`)")
            if _VIEWPORT_VW_RE.search(line):
                bad.append(f"{rel}:{i}: 100vw 는 스크롤바 폭만큼 가로 오버플로 — 100% 로")
    return bad


def check_frontend_browser_api(ui_files: list[Path]) -> list[str]:
    """브라우저 API 직접 호출. 래퍼 정본이 선언돼 있을 때만 판정한다.

    래퍼 하나를 거치게 해두면 나중에 앱으로 옮길 때 교체 대상이 그 파일 하나로 끝난다.
    선언이 없으면 "어디로 가라"고 말할 수 없으므로 이 게이트는 [SKIP] 이다.
    """
    allow = tuple(profile.ALLOWLIST["ui_platform"])
    if not allow:
        return []
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if _is_admin_ui(rel) or rel in allow:
            continue
        for i, line in enumerate(f.read_text(encoding=READ_ENC).splitlines(), 1):
            stripped = line.strip()
            if "web-ok" in line or stripped.startswith(_JS_COMMENT):
                continue
            if _BROWSER_API_RE.search(line):
                bad.append(f"{rel}:{i}: 브라우저 API 직접 호출 — {allow[0]} 래퍼 경유 "
                           f"(불가피하면 `// web-ok: 사유`)")
    return bad

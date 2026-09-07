"""kernel/gates/frontend.py — 화면 레이어 관례 게이트.

layers.py 의 프론트 절을 파일 400줄 상한 앞에서 기능 단위로 분리했다. 서버 레이어 규칙은
layers.py, 화면 규칙은 여기다.

  프론트 raw fetch      캐시·에러 처리 없는 직접 호출
  프론트 hex 리터럴     색 하드코딩 — 토큰·팔레트 우회
  고정 폭·100vw         폰을 깨뜨리는 두 원인
  브라우저 API 직접     래퍼 없는 플랫폼 의존 — 이식 시 교체 지점이 흩어진다
  해시 네비 단일 기전   이벤트를 안 내는 History API 혼용 — 주소만 바뀌고 화면이 안 따라온다
"""

from __future__ import annotations

import re
from pathlib import Path

from kernel import profile
from kernel.context import READ_ENC, _rel

_FETCH_RE = re.compile(r"\bfetch\s*\(|\baxios\b")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_RGB_HSL_RE = re.compile(r"\brgba?\s*\(|\bhsla?\s*\(")   # hex 게이트 우회 경로를 같이 막는다
# max-width·min-width 는 반응형의 상한·하한이라 정상이다. 뒤돌아보기로 그것만 제외한다.
_FIXED_WIDTH_RE = re.compile(r"(?<![-\w])width\s*:\s*['\"]?\d{3,}px")
_VIEWPORT_VW_RE = re.compile(r"\b100vw\b")
_BROWSER_API_RE = re.compile(r"\b(localStorage|sessionStorage|document\.|window\.)")
_PUSH_STATE_RE = re.compile(r"\bhistory\.pushState\s*\(")
_POPSTATE_RE = re.compile(r"addEventListener\(\s*['\"]popstate['\"]")

_JS_COMMENT = ("//", "*", "/*", "{/*")


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


def check_frontend_hash_nav(ui_files: list[Path]) -> list[str]:
    """한 라우트 안 깊이 이동은 `location.hash` 대입 하나로 — 이벤트를 안 내는 API 혼용 금지.

    세 API 가 내보내는 이벤트가 서로 다르다: hash 대입은 hashchange 를 내고, 뒤/앞 버튼은
    hashchange 와 popstate 를 둘 다 내며, pushState·replaceState 는 아무것도 안 낸다.
    섞어 쓰면 주소만 바뀌고 화면이 안 따라오는데 그 상태가 화면상 정상으로 보인다 —
    검사만이 발견 수단이다.
    """
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        text = f.read_text(encoding=READ_ENC)
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(_JS_COMMENT):
                continue
            if _PUSH_STATE_RE.search(line):
                bad.append(f"{rel}:{i}: history.pushState — 깊이 한 칸 추가는 `location.hash = …` "
                           f"대입이다. pushState 는 hashchange 를 안 내 복원 리스너가 안 깨어난다")
            if _POPSTATE_RE.search(line):
                bad.append(f"{rel}:{i}: popstate 리스너 — 해시 복원은 hashchange 단일이다. "
                           f"popstate 는 같은 문서 해시 대입에 안 뜬다")
        if "hashchange" in text and "replaceState" in text and "HashChangeEvent" not in text:
            bad.append(f"{rel}: hashchange 복원 + replaceState 정정 조합 — replaceState 는 이벤트를 "
                       f"안 내므로 `window.dispatchEvent(new HashChangeEvent('hashchange'))` 로 깨운다")
    return bad

"""kernel/profile.py — 프로젝트가 커널에 알려주는 것 전부.

커널은 이 모듈을 통해서만 프로젝트를 안다. 실물은 `<프로젝트 루트>/harness_profile.py` 이고,
없으면 전부 기본값(대체로 비어 있음)이라 레이어를 요구하는 게이트는 [SKIP] 이 된다.

**비어 있으면 조용히 통과하는 게 아니라 [SKIP] 으로 찍힌다.** 이 구분이 이 파일의 존재 이유다 —
이전 하네스는 레이어 이름이 안 맞아 대상이 0개인데도 [OK] 로 통과해, 지켜주지 않는 게이트를
지켜준다고 믿게 만들었다.

스키마 정의와 각 항목의 뜻은 `profiles/_template.py` 가 정본이다.
"""

from __future__ import annotations

import importlib.util
from typing import Any

from kernel.context import ROOT

PROFILE_FILE = "harness_profile.py"

_LAYER_KEYS = (
    "read", "write", "db", "web", "routes", "ui", "ui_admin", "ui_tokens",
    "tests", "schema", "shared", "batch",
)
_FILE_KEYS = ("settings", "ssl_util")
_SYMBOL_KEYS = ("db_accessor", "db_accessor_module", "ssl_bypass", "error_response")
_VOCAB_KEYS = ("ui_denylist", "abbrev_prefixes", "abbrev_names")
_ALLOWLIST_KEYS = ("py_any", "ui_hex", "ui_fetch", "ui_fetch_wrappers", "env_access",
                   "ui_platform")
_MD_KEYS = ("doc_exclude", "ref_exclude", "style_exclude", "date_exempt")


def _load() -> Any:
    path = ROOT / PROFILE_FILE
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("harness_profile", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MOD = _load()


def _mapping(name: str, keys: tuple[str, ...], empty: object) -> dict[str, Any]:
    given = getattr(_MOD, name, None) or {} if _MOD else {}
    return {key: given.get(key) if empty is None else given.get(key, empty) for key in keys}


STAGE: str = getattr(_MOD, "STAGE", "greenfield") if _MOD else "greenfield"
LOADED: bool = _MOD is not None

# 하네스 레포 자신의 프로파일인가. clone 해 간 프로젝트에서 이게 참이면 아직 설정 전이다 —
# 설치 스크립트가 프리셋으로 덮어쓴다.
IS_HARNESS_SELF: bool = bool(getattr(_MOD, "HARNESS_SELF", False)) if _MOD else False

LAYERS = _mapping("LAYERS", _LAYER_KEYS, None)
FILES = _mapping("FILES", _FILE_KEYS, None)
SYMBOLS = _mapping("SYMBOLS", _SYMBOL_KEYS, None)
VOCAB = _mapping("VOCAB", _VOCAB_KEYS, ())
ALLOWLIST = _mapping("ALLOWLIST", _ALLOWLIST_KEYS, ())
MD = _mapping("MD", _MD_KEYS, ())

SCOPE = {
    "exclude_all": tuple((getattr(_MOD, "SCOPE", None) or {}).get("exclude_all", ())) if _MOD else (),
    "exclude_scratch": tuple((getattr(_MOD, "SCOPE", None) or {}).get("exclude_scratch", ())) if _MOD else (),
}
HUBS: tuple[str, ...] = tuple(getattr(_MOD, "HUBS", ())) if _MOD else ()
HUB_DOMAIN_MD_IMPLICIT: bool = getattr(_MOD, "HUB_DOMAIN_MD_IMPLICIT", True) if _MOD else True
DOC_SYNC: list[dict[str, Any]] = list(getattr(_MOD, "DOC_SYNC", [])) if _MOD else []
BEHAVIOR_TESTED_ROOTS: tuple[str, ...] = (
    tuple(getattr(_MOD, "BEHAVIOR_TESTED_ROOTS", ())) if _MOD else ()
)
LOCAL_GATES: tuple[str, ...] = tuple(getattr(_MOD, "LOCAL_GATES", ())) if _MOD else ()
HARNESS_MAP: str = getattr(_MOD, "HARNESS_MAP", "HARNESS.md") if _MOD else "HARNESS.md"
ROOT_FILES: tuple[str, ...] = tuple(getattr(_MOD, "ROOT_FILES", ())) if _MOD else ()

# ── 언어 ───────────────────────────────────────────────────────────────────────
#
# 게이트가 볼 파일 확장자와, 구문 분석·언어 관용구에 의존하는 검사의 가용 여부.
# SYNTAX 가 "python" 이 아니면 그 계열 검사 9종은 [OK] 가 아니라 [SKIP] 이 된다 —
# 파이썬 정규식이 다른 언어에서 안 걸리는 것을 "위반 없음"으로 보고하면 그게 무음 통과다.
SOURCE_EXT: tuple[str, ...] = tuple(getattr(_MOD, "SOURCE_EXT", ("*.py",))) if _MOD else ("*.py",)
UI_EXT: tuple[str, ...] = (
    tuple(getattr(_MOD, "UI_EXT", ("*.tsx", "*.ts"))) if _MOD else ("*.tsx", "*.ts")
)
SYNTAX: str | None = getattr(_MOD, "SYNTAX", "python") if _MOD else "python"


def syntax_ready() -> bool:
    """파이썬 구문 분석·관용구에 의존하는 검사를 돌릴 수 있는가."""
    return SYNTAX == "python"


def need_syntax() -> str:
    where = SYNTAX or "미선언"
    return f"서버 언어가 {where} 라 파이썬 구문·관용구 검사를 못 함"
LEGACY_PATHS: tuple[tuple[str, "str | None"], ...] = (
    tuple(getattr(_MOD, "LEGACY_PATHS", ())) if _MOD else ()
)
LESSONS_DOC: str | None = getattr(_MOD, "LESSONS_DOC", None) if _MOD else None
AGENT_MODEL_POLICY: dict[str, tuple[str, str]] = (
    dict(getattr(_MOD, "AGENT_MODEL_POLICY", {})) if _MOD else {}
)
# 월간 감사류의 발동 임계치 항목별 덮어쓰기. 기본값은 kernel/maintenance.py 가 갖는다.
MAINTENANCE: dict[str, dict[str, int]] = (
    dict(getattr(_MOD, "MAINTENANCE", {})) if _MOD else {}
)


def layer(name: str) -> str | None:
    """레이어 경로 접두. 선언이 없으면 None — 그 게이트는 [SKIP] 이다."""
    value = LAYERS.get(name)
    if not value:
        return None
    return value if value.endswith("/") else value + "/"


def layer_raw(name: str) -> str | None:
    """접두 슬래시를 붙이지 않은 원문. 파일 하나를 가리키는 레이어(스키마 모듈 등)에 쓴다."""
    return LAYERS.get(name) or None


def symbol(name: str) -> str | None:
    return SYMBOLS.get(name) or None


def scratch() -> tuple[str, ...]:
    return SCOPE["exclude_scratch"]

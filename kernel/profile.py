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
_ALLOWLIST_KEYS = ("py_any", "ui_hex", "ui_fetch", "ui_fetch_wrappers", "env_access")
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

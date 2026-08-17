"""profiles/api_fastapi.py — 화면 없는 API 서비스 프리셋 (FastAPI · PostgreSQL).

`harness_install.py --preset api_fastapi` 가 이걸 `harness_profile.py` 로 복사한다.
스키마와 각 항목의 뜻은 `profiles/_template.py` 가 정본이다.

`web_fastapi_react` 에서 프론트만 뺀 것이다. 화면 관련 게이트 7종은 `[SKIP]` 으로 꺼지고,
꺼졌다는 사실이 매 실행마다 화면에 나온다 — 나중에 화면을 붙이면 `ui` 레이어만 채우면 켜진다.
"""

from __future__ import annotations

PRESET_SUMMARY = "화면 없이 API 만 — FastAPI · PostgreSQL"
PRESET_FITS = "다른 서비스나 앱이 호출할 API 만 만들 때. 화면은 나중에 붙여도 되고 안 붙여도 된다"

STAGE = "greenfield"

# 서버는 있고 화면이 없다 — 화면 검사 7종이 [SKIP] 이 아니라 [N/A] 로 찍힌다.
ARCH = "backend_only"


LAYERS: dict[str, str | None] = {
    "read":      "db/reads",
    "write":     "db/writes",
    "db":        "db",
    "web":       "web",
    "routes":    "web/routes",
    "ui":        None,        # 화면 없음 — UI 게이트 전량 [SKIP]
    "ui_admin":  None,
    "ui_tokens": None,
    "tests":     "tests",
    "schema":    "db/schema",
    "shared":    "utils",
    "batch":     "batches",
}

FILES: dict[str, str | None] = {
    "settings": "settings.py",
    "ssl_util": "utils/ssl_utils.py",
}

SYMBOLS: dict[str, str | None] = {
    "db_accessor":        "get_db",
    "db_accessor_module": "db.connection",
    "ssl_bypass":         "bypass_ssl_verification",
    "error_response":     "JSONResponse",
}


HARNESS_ASSETS = ("tests/fixtures/", "tests/golden/", "tests/build_fixture.py",
                  "tests/fixture_files.py", "tests/run_golden.py", "PLAN.md")

SCOPE: dict[str, tuple[str, ...]] = {
    "exclude_all":     ("docs/",) + HARNESS_ASSETS,
    "exclude_scratch": ("scripts/",),
}


HUBS: tuple[str, ...] = ("CLAUDE.md", "PROJECT.md", "DEVGUIDE.md", "HARNESS.md", "README.md")
HUB_DOMAIN_MD_IMPLICIT = True
HARNESS_MAP = "HARNESS.md"

MD: dict[str, tuple[str, ...]] = {
    "doc_exclude":   (".claude/", ".agents/", ".codex/", "docs/") + HARNESS_ASSETS,
    "ref_exclude":   ("docs/",),
    "style_exclude": (".claude/", ".agents/", ".codex/", "EDITING.md",
                      "README.md", "README.en.md") + HARNESS_ASSETS,
    "date_exempt":   ("dev/LESSONS.md",),
}


VOCAB: dict[str, tuple[str, ...]] = {
    "ui_denylist":     (),
    "abbrev_prefixes": (),
    "abbrev_names":    (),
}

ALLOWLIST: dict[str, tuple[str, ...]] = {
    "py_any":            (),
    "ui_hex":            (),
    "ui_fetch":          (),
    "ui_fetch_wrappers": (),
    "env_access":        (),
    "ui_platform":       (),
}

LEGACY_PATHS: tuple[tuple[str, "str | None"], ...] = ()
ROOT_FILES: tuple[str, ...] = ("settings.py",)


DOC_SYNC: list[dict[str, object]] = [
    {"doc": "DEVGUIDE.md", "code": "settings.py", "kind": "env_keys",
     "section": "## .env 키 목록", "allow": ()},
]

BEHAVIOR_TESTED_ROOTS: tuple[str, ...] = ()

LESSONS_DOC: str | None = "dev/LESSONS.md"

AGENT_MODEL_POLICY: dict[str, tuple[str, str]] = {
    "executor":         ("fable", "high"),
    "backend":          ("opus", "high"),
    "qa":               ("sonnet", "medium"),
    "product-reviewer": ("opus", "high"),
}

LOCAL_GATES: tuple[str, ...] = ()

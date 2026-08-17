"""profiles/web_fastapi_react.py — 웹 서비스 프리셋 (FastAPI · PostgreSQL · React).

`harness_install.py --preset web_fastapi_react` 가 이걸 `harness_profile.py` 로 복사한다.
스키마와 각 항목의 뜻은 `profiles/_template.py` 가 정본이다 — 여기는 그 형식에 **한 스택의
관례를 미리 채워둔 것**이고, 그래서 새 프로젝트가 첫날부터 게이트를 켠 채로 출발한다.

폴더 이름이 다르면 바꾸면 된다. 배치 게이트가 선언과 실물의 어긋남을 잡으므로, 이름을 바꾸고
안 고친 채로 게이트가 무음 통과하는 경로는 없다.
"""

from __future__ import annotations

# `--list` 와 온보딩 인터뷰가 읽는다. 스택 이름이 아니라 **무엇을 만들 때 고르는지**를 쓴다.
PRESET_SUMMARY = "화면과 서버가 다 있는 웹 서비스 — FastAPI · PostgreSQL · React"
PRESET_FITS = "로그인·대시보드·관리 화면처럼 사람이 브라우저로 쓰는 것을 만들 때. 가장 흔한 선택이다"

# 새 프로젝트는 MD 가 코드보다 먼저 나온다. 뼈대가 서면 "growing" → "mature" 로 올린다.
STAGE = "greenfield"

# 화면+서버 풀스택 — 전 게이트가 성립한다. kernel/archs/web_layered.py
ARCH = "web_layered"


LAYERS: dict[str, str | None] = {
    "read":      "db/reads",
    "write":     "db/writes",
    "db":        "db",
    "web":       "web",
    "routes":    "web/routes",
    "ui":        "frontend/src",
    "ui_admin":  None,
    "ui_tokens": "frontend/src/constants/colors.ts",
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


# clone 으로 딸려온 하네스 자기 자산은 이 프로젝트의 코드가 아니다. 빼지 않으면 새 프로젝트가
# 자기 것도 아닌 위반을 동결 목록에 안고 출발한다 — "신규는 처음부터 전부 통과"가 깨진다.
HARNESS_ASSETS = ("tests/fixtures/", "tests/golden/", "tests/build_fixture.py",
                  "tests/fixture_files.py", "tests/run_golden.py")

SCOPE: dict[str, tuple[str, ...]] = {
    "exclude_all":     ("docs/", "web/static/") + HARNESS_ASSETS,
    "exclude_scratch": ("scripts/",),
}


HUBS: tuple[str, ...] = ("CLAUDE.md", "PROJECT.md", "DEVGUIDE.md", "DESIGN_GUIDE.md",
                         "HARNESS.md", "README.md")
HUB_DOMAIN_MD_IMPLICIT = True
HARNESS_MAP = "HARNESS.md"

MD: dict[str, tuple[str, ...]] = {
    "doc_exclude":   (".claude/", ".agents/", ".codex/", "docs/") + HARNESS_ASSETS,
    "ref_exclude":   ("docs/",),
    "style_exclude": (".claude/", ".agents/", ".codex/", "EDITING.md",
                      "README.md", "README.en.md") + HARNESS_ASSETS,
    "date_exempt":   ("dev/LESSONS.md",),
}


# 프로젝트가 굴러가며 채운다. 리뷰에서 새 조어를 발견하면 그 문자열 그대로 넣는다.
VOCAB: dict[str, tuple[str, ...]] = {
    "ui_denylist":     (),
    "abbrev_prefixes": (),
    "abbrev_names":    (),
}


# 래칫: 비어서 출발하는 게 정상이다. 래퍼 자신만 미리 등재한다 — 검사 대상이 아니라서다.
ALLOWLIST: dict[str, tuple[str, ...]] = {
    "py_any":            (),
    "ui_hex":            (),
    "ui_fetch":          (),
    "ui_fetch_wrappers": ("frontend/src/hooks/useApi.ts",),
    "env_access":        (),
    "ui_platform":       ("frontend/src/utils/platform.ts",),
}

ROOT_FILES: tuple[str, ...] = ("settings.py", "batch_runner.py")


DOC_SYNC: list[dict[str, object]] = [
    {"doc": "DEVGUIDE.md", "code": "settings.py", "kind": "env_keys",
     "section": "## .env 키 목록", "allow": ()},
]


BEHAVIOR_TESTED_ROOTS: tuple[str, ...] = ()

LESSONS_DOC: str | None = "dev/LESSONS.md"

# 판단은 위로, 볼륨은 아래로. 에이전트를 추가하면 여기 등재해야 드리프트가 잡힌다.
AGENT_MODEL_POLICY: dict[str, tuple[str, str]] = {
    "executor":         ("fable", "high"),
    "orchestrator":     ("fable", "high"),
    "backend":          ("opus", "high"),
    "frontend":         ("opus", "high"),
    "qa":               ("sonnet", "medium"),
    "product-reviewer": ("opus", "high"),
}

LOCAL_GATES: tuple[str, ...] = ()

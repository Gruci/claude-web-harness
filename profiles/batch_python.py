"""profiles/batch_python.py — 수집·자동화 스크립트 프리셋 (Python · DB 적재).

`harness_install.py --preset batch_python` 이 이걸 `harness_profile.py` 로 복사한다.
스키마와 각 항목의 뜻은 `profiles/_template.py` 가 정본이다.

서비스가 아니라 **정기적으로 도는 일**을 만들 때다. 외부에서 데이터를 받아와 가공하고
어딘가에 넣는 모양이 반복된다. 이 프리셋이 켜는 것 중 값이 큰 두 개:

  행동 테스트 짝   수집·계산 모듈이 조용히 깨지면 아무도 모른다. 데이터 일이라 특히 그렇다
  DDL 저장 타입    소스 정밀도를 못 담는 컬럼. 넣을 때가 아니라 나중에 발견된다

웹이 없으므로 화면 게이트와 라우트 게이트는 `[SKIP]` 이다.
"""

from __future__ import annotations

PRESET_SUMMARY = "정기적으로 도는 수집·가공 스크립트 — Python · DB 적재"
PRESET_FITS = "크롤러·배치·리포트 생성처럼 사람이 화면으로 쓰는 게 아니라 시간표대로 도는 것을 만들 때"

STAGE = "greenfield"

# 웹도 화면도 없다 — 화면·웹 검사 9종이 [SKIP] 이 아니라 [N/A] 로 찍힌다.
ARCH = "headless"


LAYERS: dict[str, str | None] = {
    "read":      "db/reads",
    "write":     "db/writes",
    "db":        "db",
    "web":       None,        # 서버 없음
    "routes":    None,
    "ui":        None,        # 화면 없음
    "ui_admin":  None,
    "ui_tokens": None,
    "tests":     "tests",
    "schema":    "db/schema",
    "shared":    "utils",
    "batch":     "batches",   # 진입점. 전역 SSL 패치가 허용되는 유일한 곳
}

FILES: dict[str, str | None] = {
    "settings": "settings.py",
    "ssl_util": "utils/ssl_utils.py",
}

SYMBOLS: dict[str, str | None] = {
    "db_accessor":        "get_db",
    "db_accessor_module": "db.connection",
    "ssl_bypass":         "bypass_ssl_verification",
    "error_response":     None,   # 라우트가 없다
}


HARNESS_ASSETS = ("tests/fixtures/", "tests/golden/", "tests/build_fixture.py",
                  "tests/fixture_files.py", "tests/run_golden.py", "PLAN.md", "docs/site/")

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
ROOT_FILES: tuple[str, ...] = ("settings.py", "batch_runner.py")


DOC_SYNC: list[dict[str, object]] = [
    {"doc": "DEVGUIDE.md", "code": "settings.py", "kind": "env_keys",
     "section": "## .env 키 목록", "allow": ()},
]

# 도메인 패키지가 생기면 여기 루트를 적는다 — 그 아래 수집·계산 모듈이 테스트 짝을 요구받는다.
BEHAVIOR_TESTED_ROOTS: tuple[str, ...] = ()

LESSONS_DOC: str | None = "dev/LESSONS.md"

AGENT_MODEL_POLICY: dict[str, tuple[str, str]] = {
    "executor": ("fable", "high"),
    "backend":  ("opus", "high"),
    "qa":       ("sonnet", "medium"),
}

LOCAL_GATES: tuple[str, ...] = ()

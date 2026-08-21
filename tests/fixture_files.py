"""tests/fixture_files.py — 시험용 미니 프로젝트의 파일 내용 정본.

게이트마다 위반을 **정확히 1건씩** 심은 가짜 프로젝트의 실물이다. 여기는 데이터만 있고
쓰는 일은 `build_fixture.py` 가 한다 — 위반 사례가 늘수록 이 파일만 길어지게 갈라뒀다.

새 게이트를 만들면 여기에 그 게이트가 잡을 파일을 하나 추가하고 정답지를 다시 뜬다.
추가하지 않으면 그 게이트는 골든이 안 덮는 죽은 게이트가 된다.
"""

from __future__ import annotations

GITIGNORE = "static_check*.py\nkernel/\nharness_profile.py\n__pycache__/\n"


FILES: dict[str, str] = {}

# MD 픽스처는 fixture_md.py 가 정본이다 — 이 파일은 소스(py·ts) 픽스처만 담는다.
from fixture_md import FILES as _MD_FILES  # noqa: E402

FILES.update(_MD_FILES)

# ── 루트 파이썬 ────────────────────────────────────────────────────────────────

FILES["settings.py"] = '''"""픽스처: 환경변수 로드 정본."""
import os

ALPHA_KEY = os.getenv("ALPHA_KEY")
'''

FILES["batch_runner.py"] = '''"""픽스처: 배치 스케줄 상수."""

BATCH_HOUR = 5
'''


# ── db 레이어 ──────────────────────────────────────────────────────────────────

FILES["db/reads/bad_write.py"] = '''"""픽스처: 읽기 레이어의 쓰기 SQL."""


def wipe(conn):
    conn.execute("DELETE FROM cache")
'''

FILES["db/reads/core_import.py"] = '''"""픽스처: 커넥션 헬퍼를 core 경유로 import."""
from db.core import get_db


def rows():
    return get_db()
'''

FILES["db/conn_loop.py"] = '''"""픽스처: 커넥션 블록 안에서 중첩 루프로 집계."""


def agg():
    with get_db() as conn:
        for row in conn.execute("SELECT 1").fetchall():
            for cell in row:
                print(cell)
'''

FILES["db/schema/tables.py"] = '''"""픽스처: 저장 타입이 소스 정밀도를 못 담는 DDL."""

DDL = """
CREATE TABLE metric (
    amount REAL,
    label TEXT
)
"""
'''


# ── web 레이어 ─────────────────────────────────────────────────────────────────

FILES["web/routes/errors.py"] = '''"""픽스처: 라우트의 에러 응답 형식."""


def fail():
    return JSONResponse({"detail": "no"}, status_code=404)
'''

FILES["web/handlers.py"] = '''"""픽스처: await 없는 async 핸들러."""


async def ping():
    return {"ok": True}
'''

FILES["web/routes/orphan.py"] = '''"""픽스처: 소비 화면이 없는 라우트와 있는 라우트."""


@router.get("/api/used")
def used() -> dict:
    return {"ok": True}


@router.get("/api/nobody-consumes-this")
def orphan() -> dict:
    return {"ok": True}
'''

FILES["utils/stale_const.py"] = '''"""픽스처: 개명에서 소비처를 놓친 모듈 상수."""
PAGE_SIZE = 50


def bounded(offset: int) -> dict:
    return {"limit": DEFAULT_LIMIT, "offset": offset, "page": PAGE_SIZE}
'''

FILES["utils/money_a.py"] = '''"""픽스처: 정본 재구현 — 이름만 갈린 같은 본문(짝은 money_b)."""


def signed_won(value: int) -> str:
    sign = "+" if value > 0 else "-"
    magnitude = abs(value)
    return f"{sign}{magnitude:,}"
'''

FILES["utils/money_b.py"] = '''"""픽스처: 정본 재구현 — 이름만 갈린 같은 본문(짝은 money_a)."""


def won_signed(value: int) -> str:
    sign = "+" if value > 0 else "-"
    magnitude = abs(value)
    return f"{sign}{magnitude:,}"
'''

FILES["web/patch.py"] = '''"""픽스처: 전역 SSL 패치를 진입점 밖에서 호출."""
from utils.ssl_utils import bypass_ssl_verification

bypass_ssl_verification()
'''


# ── utils ──────────────────────────────────────────────────────────────────────

FILES["utils/env.py"] = '''"""픽스처: 설정 모듈 밖에서 환경변수 조회."""
import os

TOKEN = os.getenv("TOKEN")
'''

FILES["utils/abbrev.py"] = '''"""픽스처: 금지 축약어 2종."""

net = 0
oper_income = 1
'''

FILES["utils/anyhint.py"] = '''"""픽스처: 타입힌트 때우기."""
from typing import Any


def passthrough(value: Any) -> Any:
    return value
'''

FILES["utils/closure.py"] = '''"""픽스처: 중첩 def."""


def outer():
    def inner():
        return 1
    return inner()
'''

FILES["utils/moved.py"] = '''# utils/old_name.py
"""픽스처: 파일 이사 후 남은 헤더 경로 주석."""

VALUE = 1
'''

FILES["utils/ssl_utils.py"] = '''"""픽스처: 전역 SSL 패치 정본(호출 위치 예외)."""


def bypass_ssl_verification():
    return None
'''


# ── 도메인 · 프론트 · 테스트 ───────────────────────────────────────────────────

FILES["kofia/collect.py"] = '''"""픽스처: 대응 행동 테스트가 없는 수집 모듈."""


def collect():
    return []
'''

FILES["frontend/src/Label.tsx"] = '''export const title = "순신고가";
'''

FILES["frontend/src/Consumer.tsx"] = '''import { useApi } from "./useApi";

export const Panel = () => useApi("/api/used");
'''

FILES["frontend/src/anyts.ts"] = '''export const value: any = 1;
'''

FILES["frontend/src/RawFetch.tsx"] = '''export async function load() {
  return fetch("/api/board");
}
'''

FILES["frontend/src/Hex.tsx"] = '''export const accent = "#ff0000";
'''

FILES["frontend/src/types/api.ts"] = '''export interface Board {
  items: string[];
}
'''

FILES["frontend/src/Fixed.tsx"] = '''export const panel = { width: "480px" };
'''

FILES["frontend/src/Storage.tsx"] = '''export const saved = localStorage.getItem("draft");
'''

# 브라우저 API 래퍼 정본 — 자기 자신은 검사 대상이 아니다(프로파일 ui_platform 등재)
FILES["frontend/src/platform.ts"] = '''export const read = (key: string) => window.localStorage.getItem(key);
'''

# 시크릿 — AWS 공개 문서의 예시 키 형태. 이 빌더 자신이 게이트에 걸리지 않도록
# 리터럴을 쪼개 조립한다. 생성된 픽스처 파일에는 온전한 형태로 들어간다.
FILES["batches/leak.py"] = '''"""픽스처: 실키 형태의 토큰 하드코딩."""

ACCESS_KEY = "{0}"
'''.format("AKIA" + "IOSFODNN7EXAMPLE")

FILES["tests/unit/test_placeholder.py"] = '''"""픽스처: 짝 검사가 매칭에 실패하는지 확인용 테스트."""


def test_placeholder():
    assert True
'''

# 배열 옵셔널 게이트는 baseline 파일이 없으면 통째로 꺼진다 — 빈 파일로 켜둔다.
FILES["api_array_baseline.txt"] = "# 픽스처: 동결분 없음\n"

# 커널이 프로젝트에 대해 아는 것 전부. 픽스처는 게이트를 전부 켜도록 다 채운다.
FILES["harness_profile.py"] = '''"""픽스처 프로젝트 프로파일 — 게이트 전량을 켠다."""

STAGE = "mature"

ARCH = "web_layered"      # 화면+서버 풀스택 — 아무것도 N/A 로 돌리지 않는다

LAYERS = {
    "read": "db/reads", "write": "db/writes", "db": "db",
    "web": "web", "routes": "web/routes",
    "ui": "frontend/src", "ui_admin": "frontend/src/admin", "ui_tokens": None,
    "tests": "tests", "schema": "db/schema", "shared": "utils", "batch": "batches",
}
FILES = {"settings": "settings.py", "ssl_util": "utils/ssl_utils.py"}
SYMBOLS = {
    "db_accessor": "get_db", "db_accessor_module": "db.connection",
    "ssl_bypass": "bypass_ssl_verification", "error_response": "JSONResponse",
}
SCOPE = {"exclude_all": (), "exclude_scratch": ("scripts/", "docs/")}
HUBS = ("CLAUDE.md", "AGENTS.md", "DEVGUIDE.md", "DESIGN_GUIDE.md", "README.md", "HARNESS.md")
VOCAB = {
    "ui_denylist": ("순신고가",),
    "abbrev_prefixes": ("oper_", "rev_"),
    "abbrev_names": ("net",),
}
ALLOWLIST = {"py_any": (), "ui_hex": (), "ui_fetch": (), "ui_fetch_wrappers": (),
             "env_access": (), "ui_platform": ("frontend/src/platform.ts",)}
ROOT_FILES = ("settings.py", "batch_runner.py")
LESSONS_DOC = "dev/LESSONS.md"
AGENT_MODEL_POLICY = {"auditor": ("opus", "high")}
MD = {
    "doc_exclude": (".claude/", "docs/"),
    "ref_exclude": ("docs/", "idea/", "memory/"),
    "style_exclude": (),
    "date_exempt": ("dev/LESSONS.md",),
}
DOC_SYNC = [
    {"doc": "DEVGUIDE.md", "code": "batch_runner.py", "kind": "int_consts", "marker": "_HOUR"},
    {"doc": "DEVGUIDE.md", "code": "settings.py", "kind": "env_keys",
     "section": "## .env 키 목록", "allow": ()},
]
BEHAVIOR_TESTED_ROOTS = ("kofia/",)
LOCAL_GATES = ()
'''

FILES[".gitignore"] = GITIGNORE


"""tests/build_fixture.py — 시험용 미니 프로젝트를 만든다.

게이트마다 위반을 **정확히 1건씩** 심은 가짜 프로젝트다. 이걸 검사기에 물려 나온 출력을
정답지(tests/golden/full.txt)로 동결해두면, 리팩터 후 결과가 달라진 그 줄이 곧 망가진 게이트다.

재생성: python -X utf8 tests/build_fixture.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

DEST = Path(__file__).resolve().parent / "fixtures" / "miniproj"

# 검사기 자신은 픽스처의 추적 대상에서 뺀다. 안 그러면 검사기 줄 수가 바뀔 때마다
# 정답지가 흔들려, 게이트 로직이 깨진 것과 구분이 안 된다.
GITIGNORE = "static_check*.py\nkernel/\nharness_profile.py\n__pycache__/\n"

ROLE = "> 담는 것: {0}. 담지 않는 것: 그 밖의 것(→ `CLAUDE.md`). 읽는 시점: {1}."

FILES: dict[str, str] = {}


# ── MD ─────────────────────────────────────────────────────────────────────────

FILES["CLAUDE.md"] = f"""# CLAUDE.md

{ROLE.format("픽스처 프로젝트의 작업별 라우팅", "세션 시작")}

| 작업 | 읽을 것 |
|------|---------|
| 백엔드 | `DEVGUIDE.md` |
| 디자인 | `DESIGN_GUIDE.md` |
| 하네스 | `HARNESS.md` |
| 코덱스 | `AGENTS.md` |
"""

# ⑬b 한 줄에 설명 붙은 나열 7개 · ⑬c 괄호 3중 중첩
FILES["README.md"] = f"""# README

{ROLE.format("픽스처가 무엇인지", "픽스처를 고칠 때")}

진입점은 `CLAUDE.md` 다.

수집 단계는 외부 원본을 그대로 받아오고 · 정규화 단계는 결측치를 기본값으로 메우고 · 집계 단계는 월별 기준으로 묶어내고 · 검증 단계는 합계를 원본과 대조하고 · 적재 단계는 트랜잭션으로 밀어넣고 · 알림 단계는 실패 건만 따로 보고하고 · 정리 단계는 임시파일을 전부 지운다

호출 순서는 (수집 (정규화 (집계))) 순이다.
"""

# ④A 실존하지 않는 경로 참조
FILES["AGENTS.md"] = f"""# AGENTS.md

{ROLE.format("코덱스 진입점", "코덱스로 작업할 때")}

읽기 레이어의 정본은 `db/reads/gone.py` 다.
"""

# ⑬a 코드펜스 트리 덤프
FILES["DESIGN_GUIDE.md"] = f"""# DESIGN_GUIDE

{ROLE.format("디자인 허브", "UI 를 만질 때")}

```
frontend/
├── src/
│   ├── Label.tsx
│   ├── RawFetch.tsx
│   └── types/
└── package.json
```
"""

# ④B 배치표 시각 불일치 · ④C .env 키 양방향 불일치 · ⑬e 날짜 태그 6개
FILES["DEVGUIDE.md"] = f"""# DEVGUIDE

{ROLE.format("백엔드 허브", "파이썬을 만질 때")}

## 배치 스케줄

| 배치 | 시각 |
|------|------|
| 일별 (BATCH_HOUR) | 03:00 |

정본 상수는 `batch_runner.py` 에 있다.

## 변경 이력

2026-01-02 · 2026-02-03 · 2026-03-04 · 2026-04-05 · 2026-05-06 · 2026-06-07

## .env 키 목록

- BETA_KEY — 픽스처용 키
"""

# ④E 지도 누락 — 스킬 'runbook' 을 일부러 안 적는다
FILES["HARNESS.md"] = f"""# HARNESS

{ROLE.format("훅·에이전트·스킬 지도", "하네스를 고칠 때")}

| 종류 | 이름 |
|------|------|
| 훅 | probe_hook.py |
| 에이전트 | auditor |

이름을 백틱 없이 적는다 — 지도 대조(④E)는 문자열 등장만 보고, 백틱을 두르면 경로 실존(④A)이
아직 만들지 않은 훅 파일을 잡는다.
"""

# ④D 고아 MD(허브에서 도달 불가) · ⑬d 머리 역할 계약 누락
FILES["notes/GUIDE.md"] = """# GUIDE

어디에서도 링크되지 않는 문서다.
"""

FILES[".claude/agents/auditor.md"] = f"""---
name: auditor
description: 픽스처용 에이전트.
model: sonnet
effort: medium
---

# auditor

{ROLE.format("픽스처 에이전트 정의", "위임받을 때")}
"""

FILES[".claude/skills/runbook/SKILL.md"] = f"""---
name: runbook
description: 픽스처용 스킬.
---

# runbook

{ROLE.format("픽스처 스킬 절차", "호출될 때")}
"""

FILES[".claude/settings.json"] = """{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "python .claude/hooks/probe_hook.py" }
        ]
      }
    ]
  }
}
"""


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

FILES["tests/unit/test_placeholder.py"] = '''"""픽스처: 짝 검사가 매칭에 실패하는지 확인용 테스트."""


def test_placeholder():
    assert True
'''

# 배열 옵셔널 게이트는 baseline 파일이 없으면 통째로 꺼진다 — 빈 파일로 켜둔다.
FILES["api_array_baseline.txt"] = "# 픽스처: 동결분 없음\n"

# 커널이 프로젝트에 대해 아는 것 전부. 픽스처는 게이트를 전부 켜도록 다 채운다.
FILES["harness_profile.py"] = '''"""픽스처 프로젝트 프로파일 — 게이트 전량을 켠다."""

STAGE = "mature"

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
ALLOWLIST = {"py_any": (), "ui_hex": (), "ui_fetch": (), "ui_fetch_wrappers": (), "env_access": ()}
MD = {
    "doc_exclude": (".claude/", "docs/"),
    "ref_exclude": ("docs/", "idea/", "memory/"),
    "style_exclude": (),
    "date_exempt": (),
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


def main() -> int:
    if DEST.exists():
        shutil.rmtree(DEST)
    for rel, body in FILES.items():
        path = DEST / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    # 파일 길이 상한 게이트용 — 400줄을 1줄 넘긴다
    long_lines = ['"""픽스처: 단일 책임을 잃은 파일."""', ""]
    long_lines += [f"# 채움 {n:03d}" for n in range(399)]
    (DEST / "utils" / "long_report.py").write_text("\n".join(long_lines) + "\n", encoding="utf-8")

    print(f"픽스처 생성: {DEST}")
    print(f"  파일 {len(FILES) + 1}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())

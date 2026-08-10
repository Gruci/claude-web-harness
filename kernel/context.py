"""kernel/context.py — 프로젝트 루트와 추적 파일 수집.

커널은 `<프로젝트>/kernel/` 에 설치되므로 루트는 이 패키지의 부모다.

대상 수집이 `git ls-files` 인 이유: 추적되지 않는 파일(빌드 산출물·벤더 사본·gitignore 대상)은
프로젝트의 소유가 아니라 게이트의 대상도 아니다. 작업트리에서 지워졌는데 인덱스에만 남은
파일은 읽기 크래시를 내므로 실존 확인으로 걸러낸다.

이 모듈은 프로파일을 모른다 — `kernel/profile.py` 가 여기의 ROOT 를 쓰기 때문이다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# utf-8-sig — BOM 이 붙은 파일도 읽는다. Windows 에서 PowerShell 의 `Set-Content`·`Out-File`
# 이 기본으로 BOM 을 붙이고, 그 BOM 을 그냥 utf-8 로 읽으면 첫 글자가 ﻿ 가 되어
# `ast.parse` 가 SyntaxError 를 낸다. 그러면 게이트가 "파싱 실패"를 보고하거나 조용히 건너뛴다.
# 즉 검사기가 자기 검사 대상을 못 읽는 상태가 되는데, 화면상으론 그냥 통과처럼 보인다.
READ_ENC = "utf-8-sig"


def _rel(f: Path) -> str:
    return f.relative_to(ROOT).as_posix()


def _ls_files(*patterns: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", *patterns], cwd=ROOT, capture_output=True, text=True
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def tracked(*patterns: str, under: str | None = None) -> list[Path]:
    """추적 중인 실존 파일. under 를 주면 그 접두 아래만."""
    return [ROOT / rel for rel in _ls_files(*patterns)
            if (under is None or rel.startswith(under)) and (ROOT / rel).exists()]


# ── 하네스 자신의 발자국 ───────────────────────────────────────────────────────
#
# 커널·프리셋·훅 스크립트는 프로젝트의 앱 코드가 아니다. 코드 게이트의 대상으로 넣으면
# 하네스를 설치했다는 이유만으로 위반이 생기고, 사람은 그걸 게이트의 오탐으로 배운다.
# MD 는 뺀 대상이 아니다 — 하네스가 자기 문서를 안 지키면 그건 진짜 위반이다.

HARNESS_OWN_PREFIXES = ("kernel/", "profiles/", ".claude/")
HARNESS_OWN_FILES = ("harness_install.py", "setup_global_permissions.py", "harness_profile.py")


def is_harness_own(rel: str) -> bool:
    return rel.startswith(HARNESS_OWN_PREFIXES) or rel in HARNESS_OWN_FILES


def app_code(*patterns: str, under: str | None = None) -> list[Path]:
    """게이트 대상 소스 — 추적 파일에서 하네스 자신의 발자국을 뺀 것."""
    return [f for f in tracked(*patterns, under=under) if not is_harness_own(_rel(f))]

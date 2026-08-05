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

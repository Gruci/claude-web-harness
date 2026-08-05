"""kernel/context.py — 프로젝트 루트와 검사 대상 파일 수집.

커널 모듈 전부가 여기서 ROOT 와 파일 목록을 받는다. 커널은 `<프로젝트>/kernel/` 에 설치되므로
루트는 이 패키지의 부모다 — 검사기가 루트에 평면 배치돼 있던 이전 구조와 같은 의미다.

대상 수집이 `git ls-files` 인 이유: 추적되지 않는 파일(빌드 산출물·벤더 사본·gitignore 대상)은
프로젝트의 소유가 아니라 게이트의 대상도 아니다. 작업트리에서 지워졌는데 인덱스에만 남은
파일은 읽기 크래시를 내므로 실존 확인으로 걸러낸다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UI_PREFIX = "frontend/src/"


def _rel(f: Path) -> str:
    return f.relative_to(ROOT).as_posix()


def _ls_files(*patterns: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", *patterns], cwd=ROOT, capture_output=True, text=True
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def tracked_py_files() -> list[Path]:
    return [ROOT / rel for rel in _ls_files("*.py") if (ROOT / rel).exists()]


def tracked_ui_files() -> list[Path]:
    return [ROOT / rel for rel in _ls_files("*.tsx", "*.ts")
            if rel.startswith(UI_PREFIX) and (ROOT / rel).exists()]

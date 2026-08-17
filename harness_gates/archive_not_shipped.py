"""harness_gates/archive_not_shipped.py — 배포본에 작업 archive 를 싣지 않는다.

이 레포의 master 는 새 프로젝트가 clone 해 가는 배포본이다. `docs/tasks/archive/` 는
하네스 자신을 개발하며 나온 research·plan·mockup 산출물이라, 실어 보내면 새 프로젝트가
남의 작업 기록을 안고 출발한다. 로컬에는 남기되 git 추적만 막는다.

clone 해 간 프로젝트에는 이 규칙이 없다 — 자기 archive 는 자기 레포에 커밋하는 게 맞고,
그래서 이 게이트는 커널이 아니라 여기 산다. 커널은 남의 프로젝트 규칙을 이고 가지 않는다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from kernel.context import ROOT

TITLE = "작업 archive 배포 금지"
ARCHIVE_PREFIX = "docs/tasks/archive/"


def tracked_archive_files() -> list[str]:
    """git 이 추적 중인 archive 하위 파일. git 실패 시 빈 목록 — 판정 불가는 통과다."""
    done = subprocess.run(
        ["git", "ls-files", "--cached", ARCHIVE_PREFIX],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if done.returncode != 0:
        return []
    return [line for line in done.stdout.splitlines() if line.strip()]


def run(py_files: list[Path], ui_files: list[Path]) -> list[tuple[str, list[str]]]:
    """전역 판정이라 파일 목록을 쓰지 않는다 — 커밋 표면 전체를 본다."""
    del py_files, ui_files
    return [(TITLE, [f"{rel}: 배포본에 작업 archive 가 실려 있다 — "
                     f"`git rm --cached {rel}` 로 추적만 풀어라. 로컬 파일은 남는다"
                     for rel in tracked_archive_files()])]

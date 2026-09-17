"""과업 보드(`workboard/`)의 데이터 계층 — 두 에이전트가 같은 판정을 쓰는 단일 정본.

보드는 레포 루트의 `workboard/` 다(README.md 만 추적, 과업 파일은 gitignore). 자리가
`.claude/` 밑이 아닌 이유는 에이전트 중립이다 — Claude 훅과 Codex 진입점(`kernel/hook.py`)이
같은 보드를 읽어야 하고, 한쪽 전용 폴더 밑이면 다른 쪽이 남의 경계를 드나들게 된다.

판정을 훅마다 재구현하지 않는다 — 겹침 대조가 Claude 쪽에만 있으면 Codex 세션이 남의 과업을
조용히 덮는다(검사 34 가 중복 구현 자체도 막는다). 머지 추론(`is_merged`·`is_dead`)은 Claude
Stop 훅 전용으로 여기 두지 않는다 — Codex 배선엔 그 판정을 나를 경고 채널 계약이 없다.

함수가 보드 경로를 인자로 받는 이유는 테스트 계약이다 — 훅이 자기 `BOARD_DIR` 전역을 쥐고
몽키패치로 갈아끼운다.
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

from kernel.context import ROOT

BRANCH_PATTERN = re.compile(r"\b((?:feat|fix|perf|chore|docs|refactor)/[A-Za-z0-9._/-]+)")


def board_dir() -> Path:
    """공유 체크아웃의 `workboard/`. git 조회 실패 시 자기 트리로 폴백한다.

    이 파일은 worktree 마다 복제되므로 `ROOT / "workboard"` 로 잡으면 보드가 세션 수만큼
    갈라진다 — 보드를 git 밖으로 꺼낸 이유(같은 머신의 파일시스템이 공유 채널이다) 자체가
    무너진다. `git rev-parse --git-common-dir` 은 worktree 안에서도 **메인 `.git`** 을
    가리키고, 그 부모가 공유 체크아웃 루트다.

    폴백이 안전한 방향인 이유: 보드를 못 찾으면 '열린 과업 없음'으로 읽혀 잔존 검사가 돌고
    겹침 경고가 안 뜬다 — 둘 다 세션을 막지 않는다(경고·통과 계열).
    """
    try:
        done = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=str(ROOT),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=5)
    except Exception:
        return ROOT / "workboard"
    if done.returncode != 0 or not done.stdout.strip():
        return ROOT / "workboard"
    # 메인 체크아웃에서는 `.git` 처럼 상대경로가 온다 — 실행 cwd(ROOT) 기준으로 푼다.
    found = Path(done.stdout.strip())
    if not found.is_absolute():
        found = ROOT / found
    return found.resolve().parent / "workboard"


def active_rows(board: Path) -> list[str]:
    """진행 중 과업 행 — **파일 하나가 한 행**이다(`workboard/<수정범위>.md`).

    한 파일을 한 줄로 이어 붙이는 이유는 소비처 계약이다 — `#sid:` substring 과 `branch_of()`
    가 전부라, 줄바꿈을 살릴 이유가 없고 살리면 행 개수가 파일 수와 어긋난다.
    """
    if not board.is_dir():
        return []
    rows: list[str] = []
    for path in sorted(board.glob("*.md")):
        if path.name == "README.md":
            continue                      # 서식 설명이지 과업이 아니다
        try:
            rows.append(" | ".join(path.read_text(encoding="utf-8").split()))
        except OSError:
            continue                      # 읽기 실패한 한 파일이 판정 전체를 죽이지 않는다
    return rows


def branch_of(row: str) -> str | None:
    """행의 브랜치명 — `과업:` 뒤를 먼저 보고, 없으면 행 전체에서 찾는다.

    ⚠️ 전체 검색만 하면 `손대는 곳` 의 경로를 브랜치로 오인한다 — `docs/tasks/*` 는 브랜치
    접두(`docs/`)와 형태가 같다. 구 표 서식에서 '첫 칸만' 보던 것과 같은 방어이고, 축만
    위치에서 필드 이름으로 옮겼다(파일 서식엔 칸 개념이 없다).
    """
    after = row.split("과업:", 1)
    found = BRANCH_PATTERN.search(after[1] if len(after) > 1 else row)
    return found.group(1) if found else None


def touch_globs(text: str) -> list[str]:
    """`손대는 곳:` 아래의 글로브 목록. 다음 필드(`- 이름:`)를 만나면 끝난다."""
    globs: list[str] = []
    collecting = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- 손대는 곳:"):
            collecting = True
            continue
        if collecting:
            # 두 칸 들여쓴 `- <glob>` 만 항목이다. 들여쓰기 없는 `- x:` 는 다음 필드다.
            if line.startswith("  - "):
                globs.append(stripped[2:].strip())
                continue
            if stripped.startswith("- "):
                break
    return globs


def overlaps(target: Path, sid8: str, board: Path, root: Path) -> list[str]:
    """내 것이 아닌 과업의 글로브에 걸리는가 — 걸리면 `범위 (글로브)` 목록.

    ⚠️ `root` 는 **호출자의 worktree 루트**다(보드와 다른 자리). 편집 대상을 상대경로로 바꿔
    글로브와 맞대는 용도라, 공유 체크아웃으로 잡으면 worktree 안 파일이 전부 `relative_to`
    에서 벗어나 경고가 통째로 죽는다.
    """
    try:
        rel = target.resolve().relative_to(root).as_posix()
    except (ValueError, OSError):
        return []                         # 레포 밖 파일(스크래치패드 등)은 대상이 아니다
    hits: list[str] = []
    for path in sorted(board.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if sid8 and f"#sid:{sid8}" in text:
            continue                      # 내 과업
        for pattern in touch_globs(text):
            if fnmatch.fnmatch(rel, pattern) or rel.startswith(pattern.rstrip("*")):
                hits.append(f"{path.stem} ({pattern})")
                break
    return hits

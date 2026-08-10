"""kernel/linters.py — 그 언어의 표준 도구에 위임한다.

커널이 Go 의 구문 트리를 다시 파싱할 이유가 없다. Go 에는 `go vet` 과 `staticcheck` 가
있고 Rust 에는 `clippy` 가 있다. 우리가 만든 어설픈 정규식보다 그쪽이 정확하다.

하네스가 대신 하는 일은 **위임과 정직한 보고**다.

  도구가 있다   → 돌리고 출력을 위반으로 읽는다
  도구가 없다   → [TOOL] 로 찍고 설치 명령을 준다. 통과로 처리하지 않는다

마지막 줄이 핵심이다. 도구 부재를 조용히 넘기면 "검사했는데 깨끗함"과 "검사 자체를 못 함"이
구분되지 않는다 — 이 하네스가 없애려는 상태 그대로다.

언어팩의 `LINTERS` 가 선언 정본이다:

    LINTERS = [
        {"slug": "vet", "cmd": ["go", "vet", "./..."], "parse": "gcc",
         "install": "go 툴체인에 포함"},
    ]
"""

from __future__ import annotations

import re
import shutil
import subprocess

from kernel import profile
from kernel.context import ROOT

TIMEOUT_SECONDS = 90

# `path:line:col: message` 와 `path:line: message` — 대부분의 도구가 이 모양으로 낸다.
_GCC_LINE = re.compile(r"^(?P<path>[^\s:][^:]*):(?P<line>\d+):(?:(?P<col>\d+):)?\s*(?P<msg>.+)$")


def _parse_gcc(output: str, slug: str) -> list[str]:
    found: list[str] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "warning: ", "note: ")):
            continue
        match = _GCC_LINE.match(line)
        if not match:
            continue
        path = match.group("path").replace("\\", "/").lstrip("./")
        found.append(f"{path}:{match.group('line')}: {match.group('msg').strip()} ({slug})")
    return found


PARSERS = {"gcc": _parse_gcc}


def _entry_name(entry: dict) -> str:
    return str(entry.get("slug") or (entry.get("cmd") or ["도구"])[0])


def missing_tool(entry: dict) -> str:
    """실행 파일이 없으면 그 이름. 있으면 빈 문자열."""
    cmd = entry.get("cmd") or []
    return "" if (cmd and shutil.which(cmd[0])) else (cmd[0] if cmd else "cmd 미선언")


def run_one(entry: dict) -> tuple[list[str], str]:
    """한 도구를 돌린다. 반환은 (위반 목록, 건너뛴 사유). 사유가 있으면 [TOOL]."""
    slug = _entry_name(entry)
    absent = missing_tool(entry)
    if absent:
        hint = entry.get("install") or ""
        tail = f" — 설치: {hint}" if hint else ""
        return [], f"{absent} 미설치{tail}"
    try:
        done = subprocess.run(entry["cmd"], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return [f"{slug}: {TIMEOUT_SECONDS}초 내 응답 없음 — 검사 불능"], ""
    except OSError as exc:
        return [f"{slug}: 실행 실패 {exc.__class__.__name__}"], ""

    parser = PARSERS.get(str(entry.get("parse", "gcc")), _parse_gcc)
    return parser((done.stdout or "") + "\n" + (done.stderr or ""), slug), ""


def sections() -> list[tuple[str, str, list[str], str]]:
    """언어팩이 선언한 도구 전부. 반환은 (slug, 제목, 위반, 건너뛴 사유)."""
    found: list[tuple[str, str, list[str], str]] = []
    for entry in profile.LINTERS:
        if not isinstance(entry, dict):
            continue
        slug = _entry_name(entry)
        title = f"정적 분석({slug})"
        violations, skipped = run_one(entry)
        found.append((f"lint:{slug}", title, violations, skipped))
    return found

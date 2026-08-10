"""harness_gates/edit_surface.py — 면제·제외 목록은 줄어들기만 한다.

게이트를 무르게 만드는 최단 경로는 게이트를 고치는 게 아니라 면제 목록에 한 줄 더하는
것이다. 회고의 판정이 사람 몫인 동안에도 그 문은 닫아둬야, 나중에 자동화할 여지가 생긴다.
적합도 함수 없이 제안과 수용을 자동화하면 루프는 가장 싼 통과 경로로 수렴하고, 그 경로가
바로 여기다.

이 레포에서만 참인 규칙이라 커널이 아니라 여기 산다 — 커널은 남의 프로젝트 규칙을 이고
가지 않는다. 동결본은 `harness_surface.txt` 이고 기존 래칫 셋과 같은 모양이다.
"""

from __future__ import annotations

from pathlib import Path

from kernel import profile
from kernel.context import READ_ENC, ROOT

SURFACE_FILE = ROOT / "harness_surface.txt"
TITLE = "편집 표면 래칫(면제·제외 목록)"
SCOPE_KEY = 'SCOPE["exclude_all"]'


def current() -> set[tuple[str, str]]:
    """프로파일이 지금 선언한 면제·제외 전량."""
    found = {(f"ALLOWLIST[{key}]", value)
             for key, values in profile.ALLOWLIST.items() for value in values}
    return found | {(SCOPE_KEY, value) for value in profile.SCOPE["exclude_all"]}


def frozen() -> set[tuple[str, str]]:
    """동결본. 형식은 `<표면 키>\\t<값>` 이고 주석과 빈 줄은 건너뛴다."""
    entries: set[tuple[str, str]] = set()
    for line in SURFACE_FILE.read_text(encoding=READ_ENC).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _tab, value = line.partition("\t")
        if value.strip():
            entries.add((key.strip(), value.strip()))
    return entries


def run(py_files: list[Path], ui_files: list[Path]) -> list[tuple[str, list[str]]]:
    """전역 판정이라 파일 목록을 쓰지 않는다 — 편집 하나마다 표면 전체를 다시 본다."""
    del py_files, ui_files
    if not SURFACE_FILE.exists():
        return [(TITLE, [f"{SURFACE_FILE.name} 없음 — 표면을 동결하지 않으면 면제가 늘어도 "
                         f"아무도 모른다. 현재 선언을 그대로 적어 만들어라"])]
    added = sorted(current() - frozen())
    return [(TITLE, [f"{SURFACE_FILE.name}: {key} 에 '{value}' 가 늘었다 — 게이트를 무르게 "
                     f"만드는 변경이다. 면제 말고 코드를 고칠 수 없는지 먼저 보고, 그래도 "
                     f"필요하면 사유를 dev/REJECTED.md 에 남긴 뒤 동결본에 행을 더하라"
                     for key, value in added])]

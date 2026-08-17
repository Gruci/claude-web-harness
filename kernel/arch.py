"""kernel/arch.py — 아키텍처팩 로더.

아키텍처 하나를 늘리는 비용을 **데이터 파일 하나**로 만든다. `kernel/lang.py` 와 같은
골격이고, 선언은 하나뿐이다.

  NOT_APPLICABLE   이 아키텍처에서는 규칙 자체가 성립하지 않는 게이트와 그 사유

언어팩과 나뉘는 선: 언어팩은 "검사기가 그 언어를 이해하는 방법"이고, 아키텍처팩은
"이 프로젝트 형태에 어떤 레이어가 존재하는가"다. 화면 없는 서비스의 UI 게이트가
[SKIP](설정을 안 채움)이 아니라 [N/A](채울 것이 없음)로 찍히게 하는 것이 존재 이유다.

실물은 `kernel/archs/<이름>.py` 이고, 프로파일의 `ARCH` 가 어느 것을 쓸지 정한다.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from kernel.context import ROOT

SHIPPED_DIR = Path(__file__).resolve().parent / "archs"
PROJECT_DIR = "profiles/arch"

DEFAULTS: dict[str, Any] = {"NOT_APPLICABLE": {}}


def pack_path(name: str) -> Path | None:
    """이 아키텍처팩의 실물. 프로젝트 것이 커널 것을 이긴다."""
    for candidate in (ROOT / PROJECT_DIR / f"{name}.py", SHIPPED_DIR / f"{name}.py"):
        if candidate.is_file():
            return candidate
    return None


def available() -> list[str]:
    names: set[str] = set()
    for directory in (SHIPPED_DIR, ROOT / PROJECT_DIR):
        if directory.is_dir():
            names |= {p.stem for p in directory.glob("*.py") if not p.stem.startswith("_")}
    return sorted(names)


def load(name: str | None) -> dict[str, Any]:
    """아키텍처팩을 읽는다. 이름이 없거나 못 찾거나 깨졌으면 기본값(전 게이트 성립)."""
    pack: dict[str, Any] = {"NOT_APPLICABLE": {}}
    if not name:
        return pack
    path = pack_path(name)
    if path is None:
        return pack
    spec = importlib.util.spec_from_file_location(f"_arch_{name}", path)
    if spec is None or spec.loader is None:
        return pack
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return pack                     # 깨진 팩은 기본값으로 — 러너를 크래시시키지 않는다
    given = getattr(module, "NOT_APPLICABLE", None)
    if given:
        pack["NOT_APPLICABLE"] = dict(given)
    return pack

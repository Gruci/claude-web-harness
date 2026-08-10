"""kernel/lang.py — 언어팩 로더.

언어 하나를 늘리는 비용을 **데이터 파일 하나**로 만드는 것이 이 모듈의 목적이다.
커널에는 파서가 없다. 언어별로 다른 것은 넷뿐이고 전부 선언이다.

  EXT              이 언어의 소스 확장자
  PATTERNS         관용구 정규식 — 환경변수 읽기·임의 타입·주석 접두 등
  NOT_APPLICABLE   이 언어에서는 규칙 자체가 성립하지 않는 게이트와 그 사유
  LINTERS          이 언어의 표준 도구. 우리가 다시 만들지 않고 위임한다

`NOT_APPLICABLE` 이 따로 있는 이유: "못 함"과 "해당 없음"은 다르다. Go 에 타입힌트
게이트가 안 도는 건 손실이 아니라 언어가 이미 보장하기 때문이고, 커넥션 블록 게이트가
안 도는 건 진짜 손실이다. 둘을 같은 `[SKIP]` 으로 뭉뚱그리면 무엇을 잃었는지 알 수 없다.

실물은 `profiles/lang/<이름>.py` 이고, 프로파일의 `LANG` 이 어느 것을 쓸지 정한다.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from kernel.context import ROOT

# 커널이 싣고 다니는 팩이 기본이고, 프로젝트가 같은 이름으로 덮어쓸 수 있다.
# 커널 쪽에 두는 이유: 언어팩은 프로젝트 설정이 아니라 **검사기가 그 언어를 이해하는 방법**이라
# 검사기와 함께 이동해야 한다. 프로파일만 있는 곳에 두면 검사기를 복사해도 안 따라온다.
SHIPPED_DIR = Path(__file__).resolve().parent / "langs"
PROJECT_DIR = "profiles/lang"

# 언어팩이 없거나 선언을 빠뜨렸을 때의 기본값. 파이썬 기준이다.
DEFAULTS: dict[str, Any] = {
    "EXT": ("*.py",),
    "SYNTAX": "python",
    "PATTERNS": {
        "env_read": r"\bos\.(getenv|environ)\b",
        "any_type": r"[:\[,]\s*Any\b|->\s*Any\b",
        "any_escape": "any-ok",
        "comment": "#",
        "import_stmt": r"\bimport\b",
    },
    "NOT_APPLICABLE": {},
    "LINTERS": (),
}


def pack_path(name: str) -> Path | None:
    """이 언어팩의 실물. 프로젝트 것이 커널 것을 이긴다."""
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
    """언어팩을 읽어 기본값 위에 얹는다. 이름이 없거나 못 찾으면 기본값(파이썬)."""
    pack = dict(DEFAULTS)
    pack["PATTERNS"] = dict(DEFAULTS["PATTERNS"])
    if not name:
        return pack
    path = pack_path(name)
    if path is None:
        return pack
    spec = importlib.util.spec_from_file_location(f"_lang_{name}", path)
    if spec is None or spec.loader is None:
        return pack
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return pack                     # 깨진 언어팩은 기본값으로 — 조용히 죽지는 않는다
    for key in ("EXT", "SYNTAX", "NOT_APPLICABLE", "LINTERS"):
        if hasattr(module, key):
            pack[key] = getattr(module, key)
    given = getattr(module, "PATTERNS", None)
    if given:
        pack["PATTERNS"].update(given)   # 선언한 것만 덮고 나머지는 기본값 유지
    return pack

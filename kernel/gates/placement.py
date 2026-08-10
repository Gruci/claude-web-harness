"""kernel/gates/placement.py — 앱 코드가 어디에 놓이는가.

이 게이트가 없으면 나머지 레이어 게이트가 **조용히 죽는다.** 레이어 게이트는 경로 접두로
대상을 고르므로, 첫 실코드가 선언 안 된 폴더에 지어지는 순간 대상 0건이 되어 위반 0으로
통과한다. 배치를 먼저 고정해야 나머지 게이트의 가정이 성립한다.

커널은 레이어의 **이름을 모른다** — 프로파일의 `LAYERS` 에 선언된 값이 곧 허용 경로다.
하나도 선언돼 있지 않으면 판정 근거가 없으므로 이 게이트는 [SKIP] 이다.

도메인 패키지는 등재하지 않는다. 레이어가 아니면서 소문자 이름이고 `.py` 를 가진 최상위
디렉토리가 곧 도메인 패키지다 — 등재 행위를 없애야 등재 누락도 없다. 대신 모양이 계약이 된다:
`__init__.py` 와 동명 대문자 MD.
"""

from __future__ import annotations

import re
from pathlib import Path

from kernel import profile
from kernel.context import ROOT, _rel

DOMAIN_PACKAGE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

# 커널 자신의 발자국 — 프로젝트 앱 코드가 아니므로 배치 규칙의 대상이 아니다.
SELF_FILES = ("harness_profile.py", "harness_install.py")
SELF_PREFIXES = ("kernel/", "profiles/", "harness_gates/", ".claude/")


def layer_prefixes() -> tuple[str, ...]:
    """프로파일에 선언된 레이어 경로 전부. 비어 있으면 이 게이트는 판정할 수 없다."""
    found = {profile.layer(name) for name in profile.LAYERS}
    return tuple(sorted(p for p in found if p))


def domain_prefixes() -> tuple[str, ...]:
    """레이어가 아니면서 `.py` 를 가진 소문자 최상위 디렉토리 = 도메인 패키지."""
    known = {p.rstrip("/") for p in layer_prefixes()}
    known |= {p.rstrip("/") for p in profile.SCOPE["exclude_all"]}
    known |= {p.rstrip("/") for p in SELF_PREFIXES}
    found: list[str] = []
    for child in sorted(ROOT.iterdir()):
        name = child.name
        if not child.is_dir() or name in known or name.startswith((".", "_")):
            continue
        if not DOMAIN_PACKAGE_NAME.match(name):
            continue
        # __pycache__ 안의 .pyc 때문에 MD 전용 디렉토리가 도메인 패키지로 오인되면 안 된다
        if any("__pycache__" not in p.parts for p in child.rglob("*.py")):
            found.append(f"{name}/")
    return tuple(found)


def _is_self(rel: str) -> bool:
    return rel in SELF_FILES or rel.startswith(SELF_PREFIXES)


def _check_domain_shape(domains: tuple[str, ...]) -> list[str]:
    """도메인 패키지 요건. 등재 대신 모양으로 판정하므로 모양이 곧 계약이다.

    `__init__.py` 가 없으면 import 경로가 깨지고, 동명 정본 MD 가 없으면 그 도메인의
    정본이 어디인지 아무도 모른다. 고아 MD 게이트가 그 MD 의 도달성을 잇는다.
    """
    bad: list[str] = []
    for prefix in domains:
        name = prefix.rstrip("/")
        package = ROOT / name
        if not (package / "__init__.py").exists():
            bad.append(f"{prefix}: 도메인 패키지에 __init__.py 없음 — 생성하라")
        doc = package / f"{name.upper()}.md"
        if not doc.exists():
            bad.append(f"{prefix}: 도메인 정본 MD 없음 — {name}/{name.upper()}.md 를 만들고 "
                       f"허브에서 링크하라 (고아 MD 게이트가 도달성을 본다)")
    return bad


def check_file_placement(py_files: list[Path], ui_files: list[Path]) -> list[str]:
    """앱 코드는 선언된 레이어나 도메인 패키지에만 둔다."""
    layers = layer_prefixes()
    if not layers:
        return []
    domains = domain_prefixes()
    allowed = layers + domains
    hint = "·".join(layers)
    root_files = tuple(profile.ROOT_FILES)
    ui = profile.layer("ui")

    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if ui and not rel.startswith(ui):
            bad.append(f"{rel}: 프론트 코드는 {ui} 아래에만 — 바깥에 두면 UI 게이트가 "
                       f"대상 목록에서 통째로 제외한다")
    for f in py_files:
        rel = _rel(f)
        if _is_self(rel):
            continue
        if "/" not in rel:
            if rel not in root_files:
                bad.append(f"{rel}: 루트에 앱 코드 금지 — {hint} 중 하나로 옮기거나 "
                           f"프로파일 ROOT_FILES 에 등재하라")
            continue
        if not rel.startswith(allowed):
            bad.append(f"{rel}: 레이어도 도메인 패키지도 아니다 — {hint} 중 하나로 옮기거나, "
                       f"도메인 패키지 요건을 갖춰라 (소문자 이름·__init__.py·동명 정본 MD)")
    return bad + _check_domain_shape(domains)

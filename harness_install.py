"""harness_install.py — 하네스를 프로젝트에 끼우는 1회 실행.

새 프로젝트든 기존 레포든 이 한 줄이 시작점이다.

  python -X utf8 harness_install.py              프로파일 생성 + 현재 위반 동결 + 검증
  python -X utf8 harness_install.py --preset web 스택 프리셋으로 프로파일 생성
  python -X utf8 harness_install.py --dry-run    무엇이 동결될지만 출력
  python -X utf8 harness_install.py --prune      이미 고쳐진 동결 행 제거(래칫 수확)
  python -X utf8 harness_install.py --list       쓸 수 있는 프리셋 목록

**하는 일 셋.**

1. `harness_profile.py` 가 없으면 프리셋에서 만든다. 커널은 이 파일로만 프로젝트를 안다.
2. 게이트가 요구하는 동결 파일을 만든다. 없으면 그 게이트가 [SKIP] 으로 죽어 있다.
3. 현재 위반을 전부 동결하고 초록불에서 출발한다 — 이후로는 신규 위반만 걸린다(래칫).

3번이 있는 이유: 하네스를 끼운 첫 실행이 수백 건을 뱉으면 사람은 게이트를 통째로 끈다.
그게 하네스가 죽는 실제 경로다. 동결 단위는 (게이트 slug, 파일)이다 — 줄번호로 잡으면
코드가 한 줄만 밀려도 동결이 풀린다. 동결은 "이 파일은 이 게이트에서 봐준다"는 뜻이지
"규칙이 없다"가 아니다. 그 파일을 다음에 손볼 때 고치고 행을 지우는 게 정상 경로다.

`harness_baseline.txt` 는 커밋한다 — 세션·머신이 바뀌어도 동결 상태가 공유돼야
"줄어들기만 한다"는 래칫이 성립한다.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from kernel import profile, runner
from kernel.context import ROOT
from kernel.gates import api_types, placement

PRESET_DIR = ROOT / "profiles"
DEFAULT_PRESET = "_template"

BASELINE_HEADER = """# harness_baseline.txt — 하네스 설치 시점에 이미 있던 위반의 동결 목록.
#
# 형식: <게이트 slug>\\t<파일 경로>
# 래칫: 이 파일은 줄어들기만 해야 한다. 파일을 고쳤으면 해당 행을 지운다.
#       (`python -X utf8 harness_install.py --prune` 이 고쳐진 행을 자동으로 걷어낸다.)
# 신규 파일은 여기 없으므로 처음부터 전 게이트를 통과해야 한다 — 그게 이 설계의 목적이다.
"""

# 존재해야 게이트가 켜지는 동결 파일. 없으면 해당 게이트가 [SKIP] 이다.
GATE_BASELINES: tuple[tuple[Path, str], ...] = (
    (api_types.BASELINE, "# 설치 시점 동결분 없음 — 필수 배열 필드가 새로 늘면 걸린다\n"),
)


# 목록에 보여줄 순서. 흔한 것부터, 빈 서식은 마지막. 여기 없는 프리셋은 뒤에 이름순으로 붙는다.
PRESET_ORDER = ("web_fastapi_react", "api_fastapi", "batch_python", DEFAULT_PRESET)


def profile_modules() -> list[str]:
    """`--preset` 으로 지정 가능한 전부. 남의 프로젝트 프로파일도 포함된다."""
    return sorted(p.stem for p in PRESET_DIR.glob("*.py") if p.stem != "__init__")


def check_install_location() -> str:
    """하네스가 세션 루트에 있는가. 어긋나면 그 사유를 돌려준다(정상이면 빈 문자열).

    훅 command 는 `.claude/hooks/...` 상대경로다. 세션이 시작되는 곳과 하네스가 있는 곳이
    다르면 훅이 통째로 안 걸리는데, **그 상태는 화면에 아무것도 안 뜬다.** [SKIP] 조차
    없다 — 검사기가 아예 안 불리기 때문이다. 하네스가 죽는 방식 중 제일 조용한 경로다.

    판정은 git 최상위와 대조한다. 레포 루트가 곧 세션 루트라는 보장은 없지만, 하네스가
    레포 안쪽 하위 폴더에 들어앉은 경우는 확실히 잘못이고 그게 실제로 나온 사고다.
    """
    done = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        return ""                       # git 밖이면 다른 검사가 이미 잡는다
    top = Path(done.stdout.strip()).resolve()
    if top == ROOT:
        return ""
    try:
        nested = ROOT.relative_to(top).as_posix()
    except ValueError:
        return ""                       # 레포 밖 — 판단 근거 없음
    return nested


def report_install_location() -> bool:
    """설치 위치가 잘못됐으면 고치는 법을 출력한다. 반환은 '계속 진행해도 되는가'."""
    nested = check_install_location()
    if not nested:
        return True
    print("[설치 위치] 하네스가 레포 루트가 아니라 하위 폴더에 있다.\n")
    print(f"   레포 루트 : {ROOT.parents[len(Path(nested).parts) - 1]}")
    print(f"   하네스    : {ROOT}   (= {nested}/)")
    print("\n   이 상태로는 훅이 하나도 안 걸린다. `.claude/settings.json` 의 훅 명령이")
    print("   `.claude/hooks/...` 상대경로라, 세션이 시작되는 레포 루트에 `.claude/` 가")
    print("   없으면 전부 실패한다. 그리고 그 실패는 화면에 아무것도 안 남긴다.")
    print("\n   고치는 법 — 하네스 내용물을 레포 루트로 올린다:")
    print(f"       cd {ROOT.parent}")
    print(f"       git mv {nested}/* {nested}/.[!.]* .  2>/dev/null || "
          f"(mv {nested}/* {nested}/.[!.]* . )")
    print(f"       rmdir {nested}")
    print("       python -X utf8 harness_install.py")
    print("\n   레포를 새로 시작하는 경우라면 clone 자체를 프로젝트 폴더로 하는 게 낫다:")
    print("       git clone <url> my-project && cd my-project && rm -rf .git && git init")
    return False


def print_language_report() -> None:
    """이 프로젝트의 언어 설정과, 그 언어팩이 요구하는 도구의 설치 여부.

    도구가 없으면 그 검사는 안 도는데, 설치 전에는 그 사실이 설치 화면에 안 나온다.
    온보딩이 이걸 보고 "무엇이 지금 안 지켜지는지"를 사용자에게 말해줘야 한다.
    """
    from kernel import lang, linters

    print(f"쓸 수 있는 언어팩: {' '.join(lang.available())}\n")
    print(f"현재 설정 — LANG={profile.LANG!r} SYNTAX={profile.SYNTAX!r}")
    print(f"   서버 소스: {' '.join(profile.SOURCE_EXT)}")
    print(f"   화면 소스: {' '.join(profile.UI_EXT)}")

    if profile.NOT_APPLICABLE:
        print("\n이 언어에서 해당 없는 검사 (손실 아님):")
        for slug, why in sorted(profile.NOT_APPLICABLE.items()):
            print(f"   {slug:<16} {why}")

    if not profile.LINTERS:
        print("\n위임할 외부 도구 없음.")
        return
    print("\n외부 도구:")
    for entry in profile.LINTERS:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("slug") or "?")
        absent = linters.missing_tool(entry)
        if absent:
            print(f"   [없음] {name:<14} {absent} 미설치 — {entry.get('install', '설치 방법 미기재')}")
        else:
            print(f"   [있음] {name:<14} {' '.join(entry.get('cmd', []))}")
    print("\n없는 도구는 해당 검사가 [TOOL] 로 꺼진 채 돈다. 통과로 처리되지는 않는다.")


def presets() -> list[str]:
    """새 프로젝트에 권할 수 있는 것만. `PRESET_SUMMARY` 선언이 곧 프리셋 선언이다.

    선언을 요구하는 이유: `profiles/` 에는 특정 프로젝트의 실물 프로파일도 섞여 산다.
    그걸 새 프로젝트에 권하면 남의 레이어 이름과 어휘를 물려받는다.
    """
    declared = [name for name in profile_modules() if _preset_meta(name)[0]]
    ranked = [name for name in PRESET_ORDER if name in declared]
    return ranked + [name for name in declared if name not in ranked]


def _preset_meta(name: str) -> tuple[str, str]:
    """프리셋의 (한 줄 요약, 언제 고르는지). 없으면 빈 문자열."""
    spec = importlib.util.spec_from_file_location(f"_preset_{name}", PRESET_DIR / f"{name}.py")
    if spec is None or spec.loader is None:
        return "", ""
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return "", ""
    return getattr(module, "PRESET_SUMMARY", ""), getattr(module, "PRESET_FITS", "")


def print_presets() -> None:
    """사람이 고를 수 있게 요약과 함께 나열한다.

    이름만 나열하면 `web_fastapi_react` 와 `api_fastapi` 중 무엇이 자기 경우인지 모른다.
    스택 이름을 아는 사람만 고를 수 있는 목록은 목록이 아니다.
    """
    print("쓸 수 있는 프리셋:\n")
    for name in presets():
        summary, fits = _preset_meta(name)
        print(f"  {name}")
        if summary:
            print(f"      {summary}")
        if fits:
            print(f"      → {fits}")
        print()
    print("고르기 어려우면 claude 를 켜고 \"하네스 깔아줘\" 라고 하라 — 물어보고 골라준다.")


def install_profile(preset: str) -> bool:
    """프로파일 실물이 없으면 프리셋에서 만든다. 반환은 '새로 만들었는가'.

    하네스 레포를 clone 해 온 경우 하네스 **자신의** 프로파일이 딸려 온다. 그건 이 프로젝트의
    설정이 아니라 하네스가 자기를 검사하려고 둔 파일이고, 레이어가 전부 비어 있어 그대로 두면
    게이트가 통째로 꺼진 채 초록불이 뜬다. 그래서 자기 프로파일은 '없음'으로 취급해 덮어쓴다.
    """
    target = ROOT / profile.PROFILE_FILE
    if target.exists() and not getattr(profile, "IS_HARNESS_SELF", False):
        print(f"[프로파일] {profile.PROFILE_FILE} 이미 있음 — 건드리지 않는다")
        return False
    if target.exists():
        print(f"[프로파일] 딸려온 하네스 자기 프로파일을 이 프로젝트의 것으로 교체한다")
    source = PRESET_DIR / f"{preset}.py"
    if not source.exists():
        print(f"[프로파일] 프리셋 '{preset}' 없음. 쓸 수 있는 것: {' '.join(presets())}")
        print("   --list 로 각각이 어떤 경우인지 볼 수 있다.")
        return False
    shutil.copy2(source, target)
    print(f"[프로파일] {profile.PROFILE_FILE} 생성 (프리셋 {preset})")
    print("   → 레이어 이름을 실물에 맞추고, 아는 것부터 채워라. "
          "빈 항목은 조용히 통과하지 않고 [SKIP] 으로 찍힌다.")
    return True


def install_gate_baselines() -> None:
    for path, header in GATE_BASELINES:
        if path.exists():
            continue
        path.write_text(header, encoding="utf-8")
        print(f"[동결 파일] {path.name} 생성 — 이게 없으면 해당 게이트가 [SKIP] 이다")


def report_unlisted_layers() -> None:
    """앱 코드가 들었는데 레이어로 선언되지 않은 최상위 폴더를 알린다.

    레이어 이름은 프로젝트가 정한다. 그래서 설치 시점에 선언과 실물이 어긋나 있으면 여기서
    한 번 짚어줘야 한다 — 안 그러면 배치 게이트가 첫 편집에서야 막는다.
    """
    declared = placement.layer_prefixes()
    if not declared:
        print("\n[레이어 확인] 선언된 레이어가 하나도 없다 — 레이어를 요구하는 게이트는 전부 [SKIP] 이다.")
        return
    known = {p.rstrip("/") for p in declared}
    known |= {p.rstrip("/") for p in placement.SELF_PREFIXES}
    known |= {p.rstrip("/") for p in profile.SCOPE["exclude_all"]}
    unlisted = [child.name for child in sorted(ROOT.iterdir())
                if child.is_dir() and child.name not in known
                and not child.name.startswith((".", "_"))
                and any("__pycache__" not in p.parts for p in child.rglob("*.py"))]
    if not unlisted:
        return
    print("\n[레이어 확인] 아래 폴더에 앱 코드가 있는데 레이어로 선언돼 있지 않다:")
    for name in unlisted:
        print(f"   {name}/")
    print(f"   현재 선언: {' '.join(declared)}")
    print("   → 프로파일의 LAYERS 를 실물에 맞추거나, 파일을 선언된 폴더로 옮겨라.")
    print("   도메인 패키지로 둘 거면 그대로 둔다 (__init__.py 와 동명 정본 MD 를 요구한다).")


def _write_baseline(pairs: list[tuple[str, str]]) -> None:
    body = "".join(f"{slug}\t{path}\n" for slug, path in pairs)
    runner.BASELINE_FILE.write_text(BASELINE_HEADER + body, encoding="utf-8")


def _report(pairs: list[tuple[str, str]], label: str) -> None:
    by_gate: dict[str, int] = {}
    for slug, _path in pairs:
        by_gate[slug] = by_gate.get(slug, 0) + 1
    print(f"\n{label} — {len(pairs)}건 (게이트 {len(by_gate)}종)")
    for slug in sorted(by_gate, key=lambda s: (-by_gate[s], s)):
        print(f"   {by_gate[slug]:>4}  {slug}")


def _prune() -> int:
    frozen = runner.load_baseline()
    still_broken = set(runner.collect_all_violations()) & frozen
    removed = sorted(frozen - still_broken)
    _write_baseline(sorted(still_broken))
    _report(removed, "[PRUNE] 고쳐져서 해제된 동결")
    print(f"남은 동결 {len(still_broken)}건.")
    return 0


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = set(argv)

    if "--list" in args:
        print_presets()
        return 0

    if "--doctor" in args:
        print_language_report()
        return 0

    # 무엇보다 먼저. 위치가 틀리면 나머지를 다 해도 훅이 하나도 안 걸린다.
    if not report_install_location():
        return 2

    preset = DEFAULT_PRESET
    if "--preset" in argv:
        index = argv.index("--preset") + 1
        if index >= len(argv):
            print("--preset 뒤에 이름이 없다. --list 로 목록을 봐라")
            return 2
        preset = argv[index]

    if "--prune" not in args and "--dry-run" not in args:
        created = install_profile(preset)
        install_gate_baselines()
        if created:
            print("\n프로파일을 방금 만들었다. 레이어를 채운 뒤 이 스크립트를 한 번 더 돌려라 — "
                  "지금 동결하면 채우기 전 상태가 얼어붙는다.")
            return 0

    report_unlisted_layers()

    if "--prune" in args:
        return _prune()

    current = runner.collect_all_violations()
    if "--dry-run" in args:
        _report(current, "[DRY RUN] 동결 대상")
        return 0

    _report(current, "[INSTALL] 동결")
    _write_baseline(current)

    # 동결이 실제로 먹었는지 확인 — 남으면 파일에 귀속되지 않는 전역 위반이라 사람이 봐야 한다.
    print("\n검증 실행:")
    code = runner.main([])
    if code == 0:
        print("\n설치 완료 — 초록불에서 출발한다. 이제부터 신규 위반만 걸린다.")
        print("harness_baseline.txt 를 커밋하라 — 동결은 세션 간 공유돼야 래칫이 성립한다.")
    else:
        print("\n남은 위반은 파일에 귀속되지 않는 전역 검사다 — 동결 키가 없어 직접 고쳐야 한다.")
        print("대개 문서 쪽이다: 하네스 지도 등재·허브 링크·문서↔코드 대조.")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

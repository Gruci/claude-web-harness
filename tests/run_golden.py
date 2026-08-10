"""tests/run_golden.py — 픽스처를 검사기에 물려 정답지와 대조한다.

검사기는 `git ls-files` 로 대상을 모으므로 픽스처가 git 레포여야 한다. 중첩 레포를 만들지
않으려고 매번 임시 디렉토리에 복사해 거기서 돌린다.

  python -X utf8 tests/run_golden.py            대조 — 다르면 diff 출력 후 exit 1
  python -X utf8 tests/run_golden.py --update   현재 출력을 정답지로 저장
  python -X utf8 tests/run_golden.py --checker <디렉토리>   검사기 위치 지정(기본 kernel/)

`--checker src` 를 주면 리팩터 전 동결 스냅샷으로 돌려 결과를 비교할 수 있다.
"""

from __future__ import annotations

import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
FIXTURE = HERE / "fixtures" / "miniproj"
GOLDEN = HERE / "golden" / "full.txt"
# 프로파일을 뺀 채로 돌린 결과 — "하네스만 얹은 새 프로젝트 첫날"이 이 모습이다.
GOLDEN_BARE = HERE / "golden" / "bare.txt"
# 서버 언어가 파이썬이 아닌 레포. 언어 무관 검사는 돌고, 구문·관용구 검사는 [SKIP] 이어야 한다.
FIXTURE_GO = HERE / "fixtures" / "goproj"
GOLDEN_GO = HERE / "golden" / "go.txt"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=cwd, check=True,
                   capture_output=True, text=True)


def capture(checker_dir: Path, bare: bool = False, fixture: Path | None = None) -> str:
    """픽스처+검사기를 임시 레포에 세우고 전체 검사 출력을 받는다.

    bare=True 면 프로파일을 지운다 — 프로젝트를 모르는 상태에서 게이트가 어떻게 처신하는지가
    새 프로젝트 첫날의 모습이고, 그게 이 하네스의 존재 이유라 정답지로 함께 동결한다.
    """
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "proj"
        shutil.copytree(fixture or FIXTURE, work)
        if bare:
            (work / "harness_profile.py").unlink(missing_ok=True)

        # 검사기가 평면 배치(static_check*.py)인지 패키지(kernel/)인지에 따라 진입점이 다르다.
        if (checker_dir / "runner.py").exists():
            shutil.copytree(checker_dir, work / "kernel",
                            ignore=shutil.ignore_patterns("__pycache__"))
            command = [sys.executable, "-X", "utf8", "-m", "kernel.runner"]
        else:
            for src in sorted(checker_dir.glob("static_check*.py")):
                shutil.copy2(src, work / src.name)
            command = [sys.executable, "-X", "utf8", "static_check.py"]

        _git(work, "init", "-q")
        _git(work, "add", "-A")

        done = subprocess.run(
            command, cwd=work, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        body = done.stdout
        if done.stderr.strip():
            body += "\n--- stderr ---\n" + done.stderr
        return f"exit={done.returncode}\n{body}"


def main(argv: list[str]) -> int:
    checker_dir = REPO / "kernel"
    if "--checker" in argv:
        checker_dir = Path(argv[argv.index("--checker") + 1]).resolve()
    if not FIXTURE.exists():
        print("픽스처가 없다 — 먼저 tests/build_fixture.py 를 돌려라", file=sys.stderr)
        return 2

    bare, go = "--bare" in argv, "--go" in argv
    if go:
        golden, fixture, label = GOLDEN_GO, FIXTURE_GO, "Go 프로젝트"
    elif bare:
        golden, fixture, label = GOLDEN_BARE, FIXTURE, "프로파일 없음"
    else:
        golden, fixture, label = GOLDEN, FIXTURE, "전 게이트"
    actual = capture(checker_dir, bare=bare, fixture=fixture)

    if "--update" in argv:
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(actual, encoding="utf-8")
        counts = {tag: sum(1 for ln in actual.splitlines() if ln.startswith(f"[{tag}]"))
                  for tag in ("FAIL", "OK", "SKIP", "REPORT")}
        print(f"정답지 저장: {golden}  ({label})")
        print("  " + " · ".join(f"[{tag}] {n}" for tag, n in counts.items()))
        return 0

    if not golden.exists():
        print("정답지가 없다 — --update 로 먼저 떠라", file=sys.stderr)
        return 2

    expected = golden.read_text(encoding="utf-8")
    if actual == expected:
        print(f"정답지 일치 ({checker_dir.name} · {label})")
        return 0

    print("정답지와 다르다 — 아래가 바뀐 줄이다:\n", file=sys.stderr)
    for line in difflib.unified_diff(
        expected.splitlines(), actual.splitlines(),
        fromfile="golden", tofile="actual", lineterm="",
    ):
        print(line, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""tests/run_golden.py — 픽스처를 검사기에 물려 정답지와 대조한다.

검사기는 `git ls-files` 로 대상을 모으므로 픽스처가 git 레포여야 한다. 중첩 레포를 만들지
않으려고 매번 임시 디렉토리에 복사해 거기서 돌린다.

  python -X utf8 tests/run_golden.py            대조 — 다르면 diff 출력 후 exit 1
  python -X utf8 tests/run_golden.py --update   현재 출력을 정답지로 저장
  python -X utf8 tests/run_golden.py --checker <디렉토리>   검사기 위치 지정(기본 src/)
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


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=cwd, check=True,
                   capture_output=True, text=True)


def capture(checker_dir: Path) -> str:
    """픽스처+검사기를 임시 레포에 세우고 전체 검사 출력을 받는다."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "proj"
        shutil.copytree(FIXTURE, work)
        for src in sorted(checker_dir.glob("static_check*.py")):
            shutil.copy2(src, work / src.name)

        _git(work, "init", "-q")
        _git(work, "add", "-A")

        done = subprocess.run(
            [sys.executable, "-X", "utf8", "static_check.py"],
            cwd=work, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        body = done.stdout
        if done.stderr.strip():
            body += "\n--- stderr ---\n" + done.stderr
        return f"exit={done.returncode}\n{body}"


def main(argv: list[str]) -> int:
    checker_dir = REPO / "src"
    if "--checker" in argv:
        checker_dir = Path(argv[argv.index("--checker") + 1]).resolve()
    if not FIXTURE.exists():
        print("픽스처가 없다 — 먼저 tests/build_fixture.py 를 돌려라", file=sys.stderr)
        return 2

    actual = capture(checker_dir)

    if "--update" in argv:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(actual, encoding="utf-8")
        fails = sum(1 for ln in actual.splitlines() if ln.startswith("[FAIL]"))
        reports = sum(1 for ln in actual.splitlines() if ln.startswith("[REPORT]"))
        oks = sum(1 for ln in actual.splitlines() if ln.startswith("[OK]"))
        print(f"정답지 저장: {GOLDEN}")
        print(f"  [FAIL] {fails}개 섹션 · [OK] {oks}개 · [REPORT] {reports}줄")
        return 0

    if not GOLDEN.exists():
        print("정답지가 없다 — --update 로 먼저 떠라", file=sys.stderr)
        return 2

    expected = GOLDEN.read_text(encoding="utf-8")
    if actual == expected:
        print(f"정답지 일치 ({checker_dir.name})")
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

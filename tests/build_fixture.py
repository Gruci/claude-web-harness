"""tests/build_fixture.py — 시험용 미니 프로젝트를 만든다.

게이트마다 위반을 **정확히 1건씩** 심은 가짜 프로젝트다. 이걸 검사기에 물려 나온 출력을
정답지(`tests/golden/full.txt`)로 동결해두면, 리팩터 후 결과가 달라진 그 줄이 곧 망가진
게이트다. 파일 내용의 정본은 `tests/fixture_files.py` 이고 여기는 쓰는 일만 한다.

재생성: python -X utf8 tests/build_fixture.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixture_files import FILES          # noqa: E402  (경로 삽입 후에만 import 가능)

DEST = Path(__file__).resolve().parent / "fixtures" / "miniproj"

# 파일 길이 상한 게이트용 — 상한을 정확히 1줄 넘긴다
LONG_FILE = DEST / "utils" / "long_report.py"
LONG_FILL = 399


def write_long_file() -> None:
    lines = ['"""픽스처: 단일 책임을 잃은 파일."""', ""]
    lines += [f"# 채움 {n:03d}" for n in range(LONG_FILL)]
    LONG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if DEST.exists():
        shutil.rmtree(DEST)
    for rel, body in FILES.items():
        path = DEST / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    write_long_file()

    print(f"픽스처 생성: {DEST}")
    print(f"  파일 {len(FILES) + 1}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())

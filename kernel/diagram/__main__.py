"""python -X utf8 -m kernel.diagram <명령> — 다이어그램 엔진 CLI.

  validate <타입> <정본.json>                 진단만. 수정 루프에서 반복한다
  deliver  <타입> <정본.json> [출력.html]     최종 렌더 + 영수증
  compare  <base.json> <head.json> <출력.html>  architecture 델타
  doctor                                       node·엔진 상태

exit 는 엔진 결과를 따른다 — 0 통과, 1 진단, 2 인자 오류·도구 없음.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from kernel import diagram

USAGE = __doc__ or ""


def _report(receipt: dict[str, object]) -> int:
    if receipt.get("tool_missing"):
        print(f"[TOOL] {receipt['tool_missing']} 없음 — 렌더·진단 불가. node 를 설치하고 다시 돌려라.")
        return 2
    validation = receipt.get("validation")
    if isinstance(validation, dict):
        print(f"검증 {validation.get('checksPassed')}/{validation.get('checkCount')} "
              f"{validation.get('compositionProfile')} · 오류 {validation.get('errors')} · "
              f"경고 {validation.get('warnings')}")
    for line in diagram.diagnostics_lines(receipt):
        print(f"   - {line}")
    if receipt.get("ok"):
        print("[OK] 엔진 통과")
        return 0
    print("[FAIL] 엔진 진단 — subject · evidence · supportedFixes 만 고치고 다시 돌려라")
    return 1


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    command, rest = argv[0], argv[1:]
    if command == "doctor":
        status = diagram.doctor()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["ok"] else 2
    if command == "validate" and len(rest) == 2 and rest[0] in diagram.TYPES:
        return _report(diagram.validate(rest[0], Path(rest[1]).resolve()))
    if command == "deliver" and len(rest) in (2, 3) and rest[0] in diagram.TYPES:
        output = Path(rest[2]).resolve() if len(rest) == 3 else None
        receipt = diagram.deliver(rest[0], Path(rest[1]).resolve(), output)
        code = _report(receipt.get("engine", receipt) if receipt.get("ok") else receipt)
        if code == 0:
            print(f"영수증: {diagram.receipt_path(Path(rest[1]).resolve()).name} · revision {receipt.get('revision')}")
        return code
    if command == "compare" and len(rest) == 3:
        return _report(diagram.compare(Path(rest[0]).resolve(), Path(rest[1]).resolve(),
                                       Path(rest[2]).resolve()))
    print(f"인자 오류: {' '.join(argv)}\n{USAGE}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""static_check_krx.py — 게이트 ⑰ KRX 호출 간격 단일 정본 (static_check.py 가 sections 에 편입).

KRX 는 자동화 대량 조회를 탐지해 IP 를 1일 차단한다(2026-08-03 실차단). 방어 수단이 호출 간격
하나뿐인데, 그 값이 배치마다 흩어져 있으면 한 파일만 되돌아가도 방어가 뚫린다. 그래서 값을
`settings.KRX_CALL_DELAY` 로 모으고 이 게이트가 그 상태를 잠근다(CLAUDE.md 래칫 원칙).

금지: pykrx 사용 파일에서 `CALL_DELAY = <숫자>` 재정의, `time.sleep(<숫자>)` 리터럴.
허용: `settings.KRX_CALL_DELAY` 경유. 재시도 백오프(`time.sleep(2 ** attempt)`)는 식이라 통과한다.
"""

from __future__ import annotations

import re
from pathlib import Path

from kernel.context import ROOT

_CONST_LITERAL = re.compile(r"^\s*CALL_DELAY\s*=\s*[\d.]+")
_SLEEP_LITERAL = re.compile(r"\btime\.sleep\(\s*[\d.]+\s*\)")


def check_krx_call_pacing(py_files: list[Path]) -> list[str]:
    """pykrx 사용 배치의 호출 간격이 settings.KRX_CALL_DELAY 단일 정본인지."""
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if not rel.startswith("batches/"):
            continue
        text = f.read_text(encoding="utf-8")
        if "pykrx" not in text:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if _CONST_LITERAL.match(line):
                bad.append(f"{rel}:{i}: CALL_DELAY 숫자 재정의 → "
                           f"`from settings import KRX_CALL_DELAY as CALL_DELAY`")
            elif _SLEEP_LITERAL.search(line):
                bad.append(f"{rel}:{i}: time.sleep 리터럴 → KRX_CALL_DELAY 사용 "
                           f"— {line.strip()[:50]}")
    return bad

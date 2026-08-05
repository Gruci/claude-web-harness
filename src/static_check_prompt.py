"""static_check 확장 게이트 ⑯ — LLM 프롬프트 본문 변경 시 헤더 버전 동시 갱신.

생성 시점 프롬프트는 DB 에 남지 않는다(`market_briefing/MARKET_BRIEFING.md` 골든셋 절).
`llm_prompts` 는 현재본만 들고 있고 브리핑 행에 프롬프트 버전 컬럼이 없어서, 어떤 보고서가
어느 지침으로 생성됐는지 판정할 근거가 **첫 줄 `V<major>.<minor>` 문자열 하나뿐**이다.
버전을 안 올리고 본문만 고치면 그 유일한 근거가 거짓이 된다 — 2026-08-03 에 실제로
"수정했는데 왜 그대로냐"를 판정하지 못해 배치 로그·`analyzed_at` 까지 뒤져야 했다.

이 규칙은 2026-07-31 에 산문(MD 문장)으로 먼저 들어왔다가 지켜지지 않았다. 검사 가능한
규칙을 산문으로 단속하는 것 자체가 실패 메커니즘이라(CLAUDE.md 일관성 게이트 ①) 게이트로 옮긴다.

판정: 작업트리 본문이 `origin/main` 과 다른데 버전 문자열이 같으면 위반.
`origin/main` 을 못 읽으면(얕은 클론·원격 없음) 검사를 건너뛴다 — CI 는 `fetch-depth: 0` 이라
실제로 돌고, 로컬은 최초 클론 직후에만 비게 된다.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_REF = "origin/main"

# 버전 헤더를 가진 프롬프트 — 형제 프롬프트(notice_extract·report_analysis)는 헤더가 없어 대상 아님.
VERSIONED_PROMPTS = ("market_briefing/prompts/market_briefing.md",)

VERSION = re.compile(r"\bV(\d+)\.(\d+)\b")


def _base_content(rel: str) -> str | None:
    """origin/main 시점 파일 내용. 원격 ref·파일이 없으면 None(=검사 생략)."""
    out = subprocess.run(
        ["git", "show", f"{BASE_REF}:{rel}"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    return out.stdout if out.returncode == 0 else None


def _version(text: str) -> str | None:
    """첫 줄의 V<major>.<minor>. 헤더에 없으면 None."""
    first = text.splitlines()[0] if text else ""
    found = VERSION.search(first)
    return found.group(0) if found else None


def check_prompt_version_bump() -> list[str]:
    """게이트 ⑯: 프롬프트 본문이 바뀌었는데 헤더 버전이 그대로면 위반."""
    bad: list[str] = []
    for rel in VERSIONED_PROMPTS:
        path = ROOT / rel
        if not path.exists():
            bad.append(f"{rel} — 대상 프롬프트 파일 없음(경로 변경 시 VERSIONED_PROMPTS 갱신)")
            continue
        current = path.read_text(encoding="utf-8")
        base = _base_content(rel)
        if base is None or current == base:
            continue
        now, before = _version(current), _version(base)
        if now is None:
            bad.append(f"{rel}:1 — 첫 줄에 버전 표기(V<major>.<minor>)가 없다")
        elif now == before:
            bad.append(
                f"{rel}:1 — 본문이 {BASE_REF} 와 다른데 버전이 {now} 그대로다. "
                f"지침·어휘·출력 스키마 변경은 minor, 역할·독자·구조 재정의는 major 를 올린다"
            )
    return bad

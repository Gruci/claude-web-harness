"""static_check_llm.py — 게이트 ⑳ LLM 클라이언트 단일 정본 (static_check.py 가 sections 에 편입).

B18: LLM 호출은 utils/claude_cli.call_claude · utils/gemini_client.call_gemini 단일이다.
재시도 백오프·펜스 파싱까지 도메인 패키지가 재구현하면 마이그레이션 누락이 생긴다
(refactor_audit — news/analyzer.py 가 B18 등재 후에도 Gemini 골격을 통째로 들고 있었다).

금지(utils/ 밖): Gemini REST URL 리터럴, claude CLI 탐지(shutil.which("claude")),
코드펜스 파싱(.split("```")) 재구현, JSON 골격(json.loads(strip_fence(...)) 인라인 —
call_claude_json 이 정본(refactor_audit PR-5 가 3벌 소거).
BASELINE 은 리팩토링 PR 이 소거할 기존 위반의 동결분 — 줄어들기만 한다(래칫).
"""

from __future__ import annotations

import re
from pathlib import Path

from kernel.context import ROOT

_PATTERNS = (
    (re.compile(r"generativelanguage\.googleapis\.com"),
     "Gemini URL 리터럴 → utils/gemini_client.call_gemini 사용(B18)"),
    (re.compile(r'which\(\s*["\']claude["\']'),
     'claude CLI 직접 탐지 → utils/claude_cli 사용(B18)'),
    (re.compile(r'\.split\(\s*["\']```["\']'),
     "코드펜스 파싱 재구현 → utils/claude_cli.strip_fence 사용"),
    (re.compile(r"json\.loads\(\s*strip_fence\("),
     "LLM JSON 골격 재구현 → utils/claude_cli.call_claude_json 사용"),
)

# 기존 위반 동결 — PR-3 이 news/analyzer 를 소거해 현재 공집합(래칫: 추가 금지)
BASELINE: tuple[str, ...] = ()


def check_llm_single_client(py_files: list[Path]) -> list[str]:
    """게이트 ⑳: utils/ 밖 LLM 호출·파싱 재구현 금지(B18)."""
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if (rel.startswith(("utils/", "scripts/", "docs/", "tests/"))
                or rel.startswith("kernel/") or rel in BASELINE):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for pat, msg in _PATTERNS:
                if pat.search(line):
                    bad.append(f"{rel}:{i}: {msg}")
    return bad

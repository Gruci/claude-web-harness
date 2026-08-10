"""profiles/lang/python.py — 파이썬 언어팩.

커널이 파이썬으로 돌기 때문에 `ast` 를 그냥 쓸 수 있다. 그래서 구문 분석 게이트 5종이
전부 켜지고, 해당 없음으로 빠지는 것도 없다. 다른 언어팩의 기준선 역할을 한다.
"""

from __future__ import annotations

EXT = ("*.py",)
SYNTAX = "python"

PATTERNS = {
    "env_read":    r"\bos\.(getenv|environ)\b",
    "any_type":    r"[:\[,]\s*Any\b|->\s*Any\b",
    "any_escape":  "any-ok",
    "comment":     "#",
    "import_stmt": r"\bimport\b",
}

NOT_APPLICABLE: dict[str, str] = {}

LINTERS = [
    {"slug": "ruff", "cmd": ["ruff", "check", "--output-format=concise", "."],
     "parse": "gcc", "install": "pip install ruff"},
]

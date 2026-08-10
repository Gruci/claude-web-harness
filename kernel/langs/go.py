"""profiles/lang/go.py — Go 언어팩.

구문 분석이 필요한 게이트는 `go vet` 과 `staticcheck` 에 위임한다. 우리가 Go AST 를
다시 파싱할 이유가 없다 — 그쪽이 정확하고, 이미 그 생태계의 표준이다.

`NOT_APPLICABLE` 이 셋인 것이 이 팩의 요점이다. Go 에서 타입힌트 게이트가 안 도는 건
손실이 아니라 **언어가 이미 보장**하기 때문이다. 손실과 비손실을 구분해야 무엇을 잃었는지
알 수 있다.
"""

from __future__ import annotations

EXT = ("*.go",)
SYNTAX = "go"

PATTERNS = {
    "env_read":    r"\bos\.(Getenv|LookupEnv|Environ)\b",
    "any_type":    r"\binterface\s*\{\s*\}|(?<![\w.])\bany\b",
    "any_escape":  "any-ok",
    "comment":     "//",
    "import_stmt": r"^\s*import\b|^\s*\"[\w./-]+\"",
}

# 규칙 자체가 이 언어에서 성립하지 않는 것들. "못 함"이 아니라 "해당 없음"이다.
NOT_APPLICABLE = {
    "type_hints": "언어가 타입을 강제하므로 누락이 불가능",
    "web_async":  "async/await 개념이 없음 (goroutine 은 다른 모델)",
    "closures":   "클로저가 관용구라 금지가 부적절",
}

LINTERS = [
    {"slug": "vet", "cmd": ["go", "vet", "./..."],
     "parse": "gcc", "install": "Go 툴체인에 포함"},
    {"slug": "staticcheck", "cmd": ["staticcheck", "./..."],
     "parse": "gcc", "install": "go install honnef.co/go/tools/cmd/staticcheck@latest"},
]

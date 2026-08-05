"""static_check_complete_date.py — 게이트 ⑱ 기준일 완전성 (static_check.py 가 sections 에 편입).

kofia_data 는 config 단위로 적재돼 배치가 중간에 죽으면 부분 수집일(일부 config 만 있는 날)이
생긴다. 그 날짜를 bare MAX(date) 로 잡으면 미완성 데이터가 기준일로 사용자에게 노출된다
(2026-08-03 사이드바 기준일 실사고 — DB.md ⛔ 산문만으로는 재발을 못 막아 게이트化).
정본 resolve 는 `get_latest_complete_date`(standalone) / `resolve_complete_date`(커넥션 위).

검사 스코프(읽기 경로만): `db/reads/` · `db/repository.py` · `web/`. 수집측(batches/·db/writes/)은
자기 config 의 마지막 적재일 조회가 정당해 제외.
  (a) SQL 문자열에 MAX(date) + kofia_data 가 있는데 config_name 이 없음 — bare 최신일 쿼리
  (b) `get_latest_date()`/`get_date_range()` 호출 — 완전성 미보장 프리미티브
허용: ALLOWLIST 파일 단위·사유 명시(래칫 — 감소만, 신규 등재는 사유 필수).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from kernel.context import ROOT

# (a) bare MAX(date) SQL 허용 — 프리미티브 정의부만
SQL_ALLOWLIST: dict[str, str] = {
    "db/repository.py": "get_latest_date/get_date_range 정의부 — 호출부는 (b)가 단속",
    "db/reads/forecast.py": "admin 예측 시각화 월 단위(YYYY-MM 절삭) — 일 단위 완전성 무관",
}

# (b) 완전성 미보장 프리미티브 호출 허용
CALL_ALLOWLIST: dict[str, str] = {
    "db/reads/_rankings.py": "fallback 직후 resolve_complete_date 로 캡",
    "web/routes/dashboard.py": "api_meta min_date·빈 DB 폴백 전용 — max 는 get_latest_complete_date 가 정본",
}

_BARE_MAX = re.compile(r"MAX\s*\(\s*date\s*\)", re.IGNORECASE)
_PRIMITIVE_CALL = re.compile(r"\bget_(latest_date|date_range)\s*\(")


def _sql_strings(tree: ast.AST) -> list[tuple[int, str]]:
    """파일 내 문자열 상수 전부 (f-string 은 리터럴 조각 연결) — (시작 줄, 내용)."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append((node.lineno, node.value))
        elif isinstance(node, ast.JoinedStr):
            parts = "".join(
                v.value for v in node.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            )
            found.append((node.lineno, parts))
    return found


def _in_scope(rel: str) -> bool:
    return rel.startswith(("db/reads/", "web/")) or rel == "db/repository.py"


def check_bare_latest_date(py_files: list[Path]) -> list[str]:
    """읽기 경로의 bare 최신일 resolve — 완전일 헬퍼 경유 강제(B23)."""
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if not _in_scope(rel):
            continue
        text = f.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        if rel not in SQL_ALLOWLIST:
            for lineno, s in _sql_strings(tree):
                if _BARE_MAX.search(s) and "kofia_data" in s and "config_name" not in s:
                    bad.append(f"{rel}:{lineno}: bare MAX(date) FROM kofia_data — "
                               f"완전일 헬퍼(get_latest_complete_date/resolve_complete_date) 경유(B23)")
        if rel not in CALL_ALLOWLIST:
            for i, line in enumerate(text.splitlines(), 1):
                # def 줄은 정의부(호출 아님) — repository.py 프리미티브 자신을 오탐하지 않게
                if line.lstrip().startswith(("#", "def ")):
                    continue
                if _PRIMITIVE_CALL.search(line):
                    bad.append(f"{rel}:{i}: 완전성 미보장 프리미티브 호출 — "
                               f"get_latest_complete_date 로(B23) — {line.strip()[:50]}")
    return bad

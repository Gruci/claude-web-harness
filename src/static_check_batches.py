"""static_check_batches.py — 게이트 ⑲ 배치 직접 SELECT 금지 · ㉓ admin 배치 경로 레지스트리 (static_check.py 가 sections 에 편입).

⑲ B13: 배치의 DB 조회는 gap-detection 포함 전부 db/reads/ 경유다. 배치 안 직접 SELECT 는
   정본 모듈(kofia_gaps·equity_gaps) 옆에서 관례가 갈라지는 국지 드리프트로 실재했다
   (refactor_audit — kofia_batch_core NAV 불일치 감지·equity_batch 시장폭 CTE).
㉓ web/admin 의 배치 스크립트 경로는 `_common._BATCH_SCRIPTS` 단일 레지스트리다(B24).
   경로 문자열 재하드코딩은 레지스트리와 조용히 어긋난다.

BASELINE 은 refactor_audit 리팩토링 PR 이 소거할 기존 위반의 동결분 — 줄어들기만 한다(래칫).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent

# 배치 파일 안 SELECT/WITH 로 시작하는 SQL 문자열 + conn.execute 동시 존재 판정
_SQL_SELECT = re.compile(r'(?i)\bSELECT\s+[\w"*,\s.]+\bFROM\b|"""\s*WITH\s+\w+\s+AS\b')
_ADMIN_BATCH_PATH = re.compile(r'["\']batches/|join\([^)]*["\']batches["\']')

# ⑲ 기존 위반 동결 — PR-4 가 db/reads 이관으로 소거해 현재 공집합(래칫: 추가 금지)
SELECT_BASELINE: tuple[str, ...] = ()
# information_schema 스키마 가드 — 도메인 데이터 조회가 아니라 영구 예외
SELECT_ALLOWLIST = ("batches/kofia_precision_backfill.py",)

# ㉓ 기존 위반 동결 — PR-6 이 _BATCH_SCRIPTS 참조 통일로 소거해 현재 공집합(래칫: 추가 금지)
ADMIN_PATH_BASELINE: tuple[str, ...] = ()


def check_batches_direct_select(py_files: list[Path]) -> list[str]:
    """게이트 ⑲: batches/*.py 에서 conn.execute + SELECT SQL 동시 존재 시 위반(B13)."""
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if not rel.startswith("batches/") or rel in SELECT_BASELINE + SELECT_ALLOWLIST:
            continue
        text = f.read_text(encoding="utf-8")
        if "conn.execute(" in text and _SQL_SELECT.search(text):
            bad.append(f"{rel}: 배치 안 직접 SELECT — 조회는 db/reads/ 경유(B13, "
                       f"exemplar: db/reads/equity_gaps.py)")
    return bad


def check_admin_batch_paths(py_files: list[Path]) -> list[str]:
    """게이트 ㉓: web/admin 에서 배치 스크립트 경로 리터럴 금지 — _BATCH_SCRIPTS 단일(B24)."""
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if (not rel.startswith("web/admin/") or rel == "web/admin/_common.py"
                or rel in ADMIN_PATH_BASELINE):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if _ADMIN_BATCH_PATH.search(line):
                bad.append(f"{rel}:{i}: 배치 경로 리터럴 — _common._BATCH_SCRIPTS 참조(B24)")
    return bad

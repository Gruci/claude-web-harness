"""static_check 확장 게이트 ⑫ — 수집/계산 모듈 행동 테스트 짝 검사 (래칫).

형식 게이트(400줄·타입힌트·레이어)는 완성됐으나 행동 버그(naive timestamp·zero→NULL·
silent failure)는 전부 프로덕션에서 발견됐다. 신규 수집/계산 모듈은 "이 로직이 깨지면
실패하는 테스트 1개"를 요구한다.

기존 무테스트 모듈은 static_check_tests_baseline.txt 에 동결 — 이 목록은 줄어들기만
해야 한다(래칫). 매칭은 tests/ 아래 test_*.py 파일명에 모듈 stem 이 포함되는지로 판정.
exemplar: tests/unit/test_institution_sources_parsers.py (실HTML 픽스처 + HTTP만 스텁).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE_FILE = ROOT / "static_check_tests_baseline.txt"

# 수집/계산 도메인 (CLAUDE.md 모듈 소유권 표 기준 — db/·web/·frontend/ 는 스코프 밖)
DOMAIN_PREFIXES = (
    "kofia/", "etf/", "news/", "dart/", "businfo/", "macro/",
    "us_cycle/", "kr_cycle/", "analyst_reports/", "market_briefing/",
    "dept_issues/", "batches/",
)


def _load_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    lines = BASELINE_FILE.read_text(encoding="utf-8").splitlines()
    return {ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")}


def _test_file_stems() -> list[str]:
    """tests/ 아래 test_*.py 파일명(접두·확장자 제거) — 미커밋 신규 테스트도 인정(rglob)."""
    tests_dir = ROOT / "tests"
    if not tests_dir.exists():
        return []
    return [p.stem[len("test_"):] for p in tests_dir.rglob("test_*.py")]


def check_module_test_pairing(py_files: list[Path]) -> list[str]:
    """게이트 ⑫: 수집/계산 .py 모듈에 대응 행동 테스트 부재 시 위반."""
    baseline = _load_baseline()
    test_stems = _test_file_stems()
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if not rel.startswith(DOMAIN_PREFIXES) or f.name == "__init__.py" or rel in baseline:
            continue
        if any(f.stem in stem for stem in test_stems):
            continue
        bad.append(
            f"{rel}: 대응 행동 테스트 없음 — tests/unit/test_{f.stem}.py 작성"
            f"(exemplar: tests/unit/test_institution_sources_parsers.py)"
            f" 또는 사유와 함께 static_check_tests_baseline.txt 등재"
        )
    return bad

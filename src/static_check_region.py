"""static_check_region.py — 게이트 ㉑ region 국내+해외 합산 정본 경유 (static_check.py 가 sections 에 편입).

F16: region='전체' 국내+해외 합산은 utils/regionMerge 단일 정본이다 — 합산은 양쪽이 다
수집된 날짜만이다(한쪽만 수집된 날은 반토막 값이 된다. 2026-08-03 AUM 추이 실사고).
인라인 재구현은 교집합 필터를 빠뜨린 채 퍼졌다(refactor_audit — /market 3파일).

판정: frontend/src 에서 '국내'·'해외' 리터럴과 fetch 호출이 공존하는데 regionMerge
import 가 없으면 위반. 합산이 아닌 파일(지역 필터 UI 등)은 FILTER_ALLOWLIST 에 사유와
함께 등재한다. BASELINE 은 리팩토링 PR 이 소거할 기존 위반 동결분 — 줄어들기만 한다(래칫).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent

# 기존 위반 동결 — plan_refactor_audit PR-9(peers)·후속 재판정이 소거 예정 (PR-1 /market 3파일 소거됨)
BASELINE = (
    "frontend/src/components/market/TypeForecast.tsx",
    "frontend/src/components/overview/market/MarketDetailPanel.tsx",
    "frontend/src/components/overview/market/OverviewMarketTab.tsx",
    "frontend/src/components/peers/aum/assetGridData.ts",
    "frontend/src/pages/self/CatCards.tsx",
    "frontend/src/pages/self/CatPie.tsx",
    "frontend/src/pages/self/TrendChart.tsx",
)
# 합산이 아니라 지역 필터·라벨만 쓰는 파일 — 재판정 후 여기로 옮긴다 (사유 필수)
FILTER_ALLOWLIST: tuple[str, ...] = ()

_FETCH_MARKS = ("fetchApi", "useApi", "fetch(")


def check_region_merge_source(ui_files: list[Path]) -> list[str]:
    """게이트 ㉑: 국내+해외 fetch 파일은 utils/regionMerge 경유(F16)."""
    bad: list[str] = []
    for f in ui_files:
        rel = f.relative_to(ROOT).as_posix()
        if rel in BASELINE + FILTER_ALLOWLIST or rel == "frontend/src/utils/regionMerge.ts":
            continue
        text = f.read_text(encoding="utf-8")
        if "'국내'" not in text or "'해외'" not in text:
            continue
        if not any(m in text for m in _FETCH_MARKS) or "regionMerge" in text:
            continue
        bad.append(f"{rel}: 국내+해외 fetch 에 regionMerge 미경유 — 합산은 "
                   f"utils/regionMerge(F16), 필터 UI 면 FILTER_ALLOWLIST 등재")
    return bad

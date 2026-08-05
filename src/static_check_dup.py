"""static_check_dup.py — 게이트 ㉔ 단일 정본 리터럴 · ㉕ web 파라미터 가드 정본 (static_check.py 가 sections 에 편입).

refactor_audit(2026-08-04, PR#302~#315)가 소거한 복붙 패턴의 재발 방지다. 감사에서 같은
사실이 여러 파일에 리터럴로 흩어져 어긋나던 실태 — 로스터 재선언(C1·C8)·코스피/코스닥
3항연산 8벌(C5)·gnews 라벨 분기 2벌(D12)·clamp/market 인라인 22곳(D1)·프롬프트 CRUD 4벌(D2)·
금융여건 라벨 편측 개명 위험(F6) — 를 각각 결정론 검사로 잠근다.

㉔ 단일 정본 리터럴:
  A. peers 8사 로스터 전체가 리터럴로 등장하는 파일 = ROSTER_ALLOWLIST 고정(래칫 — 추가 금지).
     새 파일이 로스터를 또 늘어놓으면 constants.PEERS8 import + (메타데이터 소관이면) assert 로 잠근다.
  B. frontend `=== 'KOSPI' ? '코스피'` 3항연산 — 정본은 cycleShared.krMarketKo.
  C. frontend `startsWith('gnews:')` 접두 분기 — 정본은 briefing/sourceLabels.sourceLabel.
  D. KR 사이클 블록 라벨 짝 — `us_cycle/kr_macro_series.py` KR_BLOCK_LABEL 이 API 로 내려보내는
     문자열이 정본이고 `KrCycleBoard.tsx` GROUP_ORDER 가 그 문자열로 그룹을 매칭한다.
     한쪽만 개명하면 드라이버 그룹이 조용히 어긋난다("금융여건"→"환율여건" 개명 시 실위험).

㉕ web 파라미터 가드 정본(web/dependencies):
  E. `min(max(` 인라인 클램프 금지 → clamp(v, lo, hi). bound 값은 콜사이트 소관.
  F. `in ("KOSPI", "KOSDAQ") else` 검증 3항 금지 → market_or_none(market).
     (배치의 `for market in ("KOSPI", "KOSDAQ")` 순회는 검증이 아니라 대상 밖.)

allowlist 는 전부 고정 목록이다 — 늘리지 말고 정본을 소비하게 고친다.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent

# A. 로스터 3마커가 모두 등장 = 8사 나열 파일. 정본은 constants.PEERS8(백엔드) —
#    아래는 표시명·색·코드 등 자기 소관 메타데이터 보유처(로드 시 assert 또는 정본 파생)로 고정.
_ROSTER_MARKERS = ("미래에셋자산운용", "한국투자신탁운용", "엔에이치아문디자산운용")
ROSTER_ALLOWLIST = (
    "constants.py",                                     # 정본 PEERS8
    "businfo/config.py",                                # 금감원 코드 차원 (briefing_prompts assert 가 동기 강제)
    "db/writes/news.py",                                # 뉴스 검색어 시드 (로드 시 assert)
    "batches/briefing_prompts.py",                      # KOFIA 축약 표기 (로드 시 assert)
    "db/reads/etf_brand.py",                            # ETF 브랜드↔운용사 매핑
    "frontend/src/constants/colors.ts",                 # 회사 색 정본
    "frontend/src/components/peers/aum/constants.ts",   # 프론트 PEERS8 (표시 순서)
    "frontend/src/admin/forecastTypes.ts",              # 예측 대상 나열(PEER_COMPANIES)
)

_KR_MARKET_TERNARY = re.compile(r"===\s*'KOSPI'\s*\?\s*'코스피'")
_GNEWS_PREFIX = re.compile(r"startsWith\(\s*['\"]gnews:")
_INLINE_CLAMP = re.compile(r"min\(\s*max\(")
_MARKET_TERNARY = re.compile(r'in \(["\']KOSPI["\'], ["\']KOSDAQ["\']\) else')

_BLOCK_LABEL_SRC = "us_cycle/kr_macro_series.py"
_BLOCK_LABEL_CONSUMER = "frontend/src/pages/equity/krCycle/KrCycleBoard.tsx"
# benchmark 는 참고 표시 전용이라 GROUP_ORDER 밖 — 짝 검사는 카드 그룹 3종만.
_BLOCK_KEYS = ("leading", "coincident", "financial")


def check_single_source_literals(py_files: list[Path], ui_files: list[Path]) -> list[str]:
    """게이트 ㉔: 로스터 나열·시장명 3항·gnews 분기·KR 블록 라벨 짝."""
    bad: list[str] = []
    for f in list(py_files) + list(ui_files):
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith("static_check"):   # 검사기 자신의 마커 튜플 제외
            continue
        text = f.read_text(encoding="utf-8")
        if all(m in text for m in _ROSTER_MARKERS) and rel not in ROSTER_ALLOWLIST:
            bad.append(f"{rel}: peers 8사 로스터 재나열 — constants.PEERS8 import(메타데이터면 "
                       f"assert set 동기)로 잠글 것. allowlist 는 고정(래칫)")
    for f in ui_files:
        rel = f.relative_to(ROOT).as_posix()
        text = f.read_text(encoding="utf-8")
        if rel != "frontend/src/pages/equity/cycleShared.ts" and _KR_MARKET_TERNARY.search(text):
            bad.append(f"{rel}: 코스피/코스닥 3항연산 재구현 — cycleShared.krMarketKo 사용")
        if rel != "frontend/src/components/briefing/sourceLabels.ts" and _GNEWS_PREFIX.search(text):
            bad.append(f"{rel}: gnews 접두 분기 재구현 — briefing/sourceLabels.sourceLabel 사용")
    bad += _check_block_label_pair()
    return bad


def _check_block_label_pair() -> list[str]:
    src = ROOT / _BLOCK_LABEL_SRC
    consumer = ROOT / _BLOCK_LABEL_CONSUMER
    if not (src.exists() and consumer.exists()):
        return []
    src_text = src.read_text(encoding="utf-8")
    consumer_text = consumer.read_text(encoding="utf-8")
    bad: list[str] = []
    for key in _BLOCK_KEYS:
        match = re.search(rf'"{key}":\s*"([^"]+)"', src_text)
        if not match:
            bad.append(f"{_BLOCK_LABEL_SRC}: KR_BLOCK_LABEL['{key}'] 파싱 실패 — dict 형식 변경 시 이 게이트도 갱신")
            continue
        if match.group(1) not in consumer_text:
            bad.append(f"{_BLOCK_LABEL_CONSUMER}: KR_BLOCK_LABEL['{key}']='{match.group(1)}' 이 "
                       f"GROUP_ORDER 에 없음 — 라벨은 짝으로 개명(드라이버 그룹 매칭이 문자열)")
    return bad


def check_web_param_guards(py_files: list[Path]) -> list[str]:
    """게이트 ㉕: web/ 인라인 클램프·market 검증 3항 금지 — dependencies 헬퍼 경유."""
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if not rel.startswith("web/") or rel == "web/dependencies.py":
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if _INLINE_CLAMP.search(line):
                bad.append(f"{rel}:{i}: 인라인 min(max( 클램프 — dependencies.clamp(v, lo, hi) 사용")
            if _MARKET_TERNARY.search(line):
                bad.append(f"{rel}:{i}: market 검증 3항 재구현 — dependencies.market_or_none 사용")
    return bad


def check_admin_prompt_crud(py_files: list[Path]) -> list[str]:
    """게이트 ㉕-2: web/admin 의 llm_prompts 쓰기 직접 호출 금지 — prompt_override_* 경유(_common)."""
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if not rel.startswith("web/admin/") or rel == "web/admin/_common.py":
            continue
        text = f.read_text(encoding="utf-8")
        for name in ("upsert_llm_prompt", "delete_llm_prompt"):
            if name in text:
                bad.append(f"{rel}: {name} 직접 호출 — _common.prompt_override_put/delete 경유"
                           f"(응답 키 계약 단일화)")
    return bad

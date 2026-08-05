"""static_check_gates.py — P7 확장 게이트 (static_check.py 가 import 해서 sections 에 편입).

static_check.py 자신도 400줄 게이트 대상이라, P7 에서 추가된 게이트는 이 모듈로 분리한다.
기존 6종 검사(400줄·클로저·reads쓰기·net·oper/rev·UI라벨)는 static_check.py 에 그대로 둔다.

각 게이트는 CLAUDE.md '일관성 게이트' 래칫 원칙의 산물 — 각 정리 Phase 가 만든 상태를 잠가
세션마다 새 Claude 가 드리프트하는 것을 막는다(정본 관례: dev/CONVENTIONS.md).

게이트 목록:
  ① with get_db() 블록 내 가공 (db/ 한정, AST)          — 활성  [CONVENTIONS B4]
  ② settings.py 외 os.getenv/os.environ                  — 활성  [CONVENTIONS B5]
  ③ web/ await 없는 async def                            — 활성  [CONVENTIONS B3]
  ⑤ db/reads·writes get_db import 단일 경로              — 활성  [CONVENTIONS B1]
  ⑥ bypass_ssl_verification 전역패치 호출 위치 제한       — 활성  [CONVENTIONS B6]
  ⑦ web/routes/ 에러 반환 JSONResponse 금지(admin 제외)  — 활성  [CONVENTIONS B2]
  ⑨ frontend 비admin raw fetch()                         — 활성  [CONVENTIONS F1]
  ⑧ frontend hex 리터럴                                   — 비활성(--full, P4 진행 중)
  ④ MD 참조 실존 검사                                     — 비활성(--full) → static_check_md.py 로 분리(400줄)

⑥ 관련 주의: 당초 P7 스펙은 'urllib3.disable_warnings 를 ssl_utils.py 밖 금지'였으나,
   P3 가 확정한 관례(CONVENTIONS B6)는 '인라인 disable_warnings 허용, 전역 패치
   bypass_ssl_verification() 만 batch/스크립트 진입점 밖 호출 금지'다. 인라인 disable_warnings
   는 현재 10곳에서 정상 사용 중(B6 허용)이라 그 금지는 관례와 충돌 → 실제 관례(전역 패치
   호출 위치)를 잠그도록 구현한다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from kernel.context import ROOT, _rel


# ── allowlist 상수 ─────────────────────────────────────────────────────────────

# ② settings.py 외 os.getenv/os.environ 허용 (파일 단위, 사유 명시)
ENV_ALLOWLIST: dict[str, str] = {
    # subprocess 에 넘길 환경을 전체 순회·복제(특정 키 조회가 아님) — settings 응집 대상 아님
    "utils/claude_cli.py": "os.environ 전체 순회로 subprocess env 상속(특정 키 조회 아님)",
    # 게이트 정의 파일 — 규칙명/섹션 문자열로 'os.getenv' 를 메타 언급(실제 호출 아님)
    "kernel/runner.py": "게이트 러너 — 섹션 라벨에 os.getenv 언급",
    "kernel/gates/layers.py": "게이트 검사기 — 규칙 설명 문자열에 os.getenv 언급",
    "kernel/gates/md_graph.py": "게이트 검사기(④) — 규칙 설명 문자열에 os.getenv 언급",
}

# ⑨ frontend 비admin raw fetch — 파일 단위 허용. 사유는 두 갈래뿐이고 "수렴 예정" 항목은 없다:
#   (a) 쓰기(POST) — useApi 는 조회 훅이라 담을 수 없다. useMutation 미도입이 전제.
#   (b) 404=정상(null) 시맨틱 — fetchApi 가 비2xx 를 throw 라 조회 훅으로 표현 불가.
# 2026-07-29 전수 재판정: 조회 3건 중 useCompanyConfig 만 fetchApi 수렴 완료(등재 해제).
FETCH_ALLOWLIST: dict[str, str] = {
    "frontend/src/hooks/useMemberSession.ts": "auth 쓰기(requestCode/verify/logout) — useMutation 미도입",
    "frontend/src/utils/briefingApi.ts": "브리핑 404=정상(null) 공용 래퍼 — fetchApi 는 404 를 throw 라 부적합",
    "frontend/src/pages/News.tsx": "별점 POST fire-and-forget(void fetch) — 쓰기 관례",
    "frontend/src/pages/NewsCompany.tsx": "별점 POST fire-and-forget(void fetch) — 쓰기 관례",
    "frontend/src/components/briefing/useNoticeApplication.ts": "응모 CRM 쓰기 — useMutation 미도입",
    "frontend/src/components/issues/useTaskReorder.ts": "경영 보고 순서 저장 POST — useMutation 미도입",
    # briefingApi 로 합치면 그쪽 catch 가 에러를 삼켜 컴포넌트 isError 분기(로드 실패)가 죽는다 —
    # 404=데이터없음 과 네트워크 실패를 구분해야 해서 자체 fetch 유지(2026-07-29 판정).
    "frontend/src/components/peers/aum/AumBriefing.tsx": "브리핑 404 vs 에러 3-상태 구분 — 공용 래퍼로 대체 불가",
}

# ⑨ fetch 래퍼(공용) — 검사 제외. admin 디렉토리는 경로 규칙으로 제외.
FETCH_WRAPPERS: set[str] = {
    "frontend/src/hooks/useFetchApi.ts",   # fetchApi/useApi 정본 래퍼
}

# ⑧ frontend hex 리터럴 허용 — **파일 단위 명시**(디렉토리 glob 금지: 신규 파일 드리프트 차단).
# 사유는 두 가지뿐: (a) 다크 격리 스코프(.etf-dark 계열) — base.css :root 라이트 토큰과 시맨틱 불일치,
# (b) canvas/Chart.js/SVG 컨텍스트 — CSS var() 미해석. 새 파일은 등재 금지가 원칙 —
# colors.ts 상수/토큰으로 해결 불가함을 확인한 경우에만 사유와 함께 추가 (2026-07-17 P4 전수 치환 잔존분).
HEX_ALLOWLIST: frozenset[str] = frozenset({
    # 다크 pages/equity (사이클·수급 보드)
    "frontend/src/pages/equity/CycleTrendChart.tsx",
    "frontend/src/pages/equity/IndexSection.tsx",
    "frontend/src/pages/equity/KrMarketBreadth.tsx",
    "frontend/src/pages/equity/MacroIndicatorHistory.tsx",
    "frontend/src/pages/equity/MarketFlowSection.tsx",
    "frontend/src/pages/equity/NextStageChip.tsx",
    "frontend/src/pages/equity/SectorFlowMap.tsx",
    "frontend/src/pages/equity/StockDrawer.tsx",
    "frontend/src/pages/equity/UsCotBoard.tsx",
    "frontend/src/pages/equity/cycleShared.ts",
    "frontend/src/pages/equity/krCycle/ConstituentScatter.tsx",
    "frontend/src/pages/equity/krCycle/CycleScorecard.tsx",
    "frontend/src/pages/equity/krCycle/KrCycleBoard.tsx",
    "frontend/src/pages/equity/krCycle/KrSectorDetailBody.tsx",
    "frontend/src/pages/equity/krCycle/KrSectorHistory.tsx",
    "frontend/src/pages/equity/usCycle/BusinessGauge.tsx",
    "frontend/src/pages/equity/usCycle/CycleScatter.tsx",
    "frontend/src/pages/equity/usCycle/IndustryCycleHistory.tsx",
    "frontend/src/pages/equity/usCycle/IndustryDetailBody.tsx",
    "frontend/src/pages/equity/usCycle/IndustryHeatmap.tsx",
    "frontend/src/pages/equity/usCycle/MacroIndicatorDetail.tsx",
    "frontend/src/pages/equity/usCycle/SectorStageBoard.tsx",
    "frontend/src/pages/equity/usCycle/StockMomentumMap.tsx",
    # 다크 .etf-dark (온톨로지·테마·bond)
    "frontend/src/components/bond/BondKpiCard.tsx",
    "frontend/src/components/bond/CurveSection.tsx",
    "frontend/src/components/bond/FundingSection.tsx",
    "frontend/src/components/bond/SpreadSection.tsx",
    "frontend/src/components/bond/constants.ts",
    "frontend/src/components/etfOntology/ChartWrapper.tsx",
    "frontend/src/components/etfOntology/MiniFlowChart.tsx",
    "frontend/src/components/etfOntology/constants.ts",
    "frontend/src/components/etfOntology/panels/CompanyPanel.tsx",
    "frontend/src/components/etfOntology/panels/EtfPanel.tsx",
    "frontend/src/components/etfTheme/ConstituentsPanel.tsx",
    "frontend/src/components/etfTheme/EntryVerdictCard.tsx",
    "frontend/src/components/etfTheme/FlowSeriesPanel.tsx",
    "frontend/src/components/etfTheme/ThemeDetail.tsx",
    "frontend/src/components/overview/etf/StockFilters.tsx",
    "frontend/src/components/overview/etf/StockTab.tsx",
    "frontend/src/components/overview/etf/TreemapChart.tsx",
    "frontend/src/components/overview/etf/pulse/EtfExplorerDrawer.tsx",
    "frontend/src/components/overview/etf/pulse/OpportunitySection.tsx",
    # admin (pages/ 소재라 경로 규칙 밖 — 다크 자체 톤 무변경 정책)
    "frontend/src/pages/Admin.tsx",
    "frontend/src/pages/AdminLogin.tsx",
    # canvas/Chart.js/SVG 컨텍스트 (라이트 본문 포함 — var() 미해석)
    "frontend/src/components/backtest/BriefingTab.tsx",
    "frontend/src/components/backtest/FcCompareChart.tsx",
    "frontend/src/components/backtest/FcDailyChart.tsx",
    "frontend/src/components/backtest/ForecastTab.tsx",
    "frontend/src/components/briefing/BriefingReportTab.tsx",
    "frontend/src/components/common/SectionHead.tsx",
    "frontend/src/components/layout/SidebarLogin.tsx",
    "frontend/src/components/overview/market/CompanyDetailPanel.tsx",
    "frontend/src/components/overview/market/donutOverlay.ts",
    "frontend/src/components/peers/aum/AssetGridChart.tsx",
    "frontend/src/components/peers/aum/timeseriesBuilders.ts",
    "frontend/src/components/peers/biz/BizTimeseries.tsx",
    "frontend/src/components/peers/biz/BusinessModel.tsx",
    "frontend/src/components/peers/biz/HcCharts.tsx",
    "frontend/src/components/peers/biz/IncomeCharts.tsx",
    "frontend/src/components/peers/biz/LeverageMap.tsx",
    "frontend/src/components/peers/biz/PositioningMap.tsx",
    "frontend/src/components/peers/biz/quadrantChart.ts",
    "frontend/src/constants/chartDefaults.ts",
    "frontend/src/pages/self/FlowChart.tsx",
    "frontend/src/utils/axes.ts",
    "frontend/src/utils/forecast.ts",
})

_FETCH_RE = re.compile(r"\bfetch\s*\(")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_ENV_RE = re.compile(r"\bos\.(getenv|environ)\b")
_GET_DB_IMPORT_RE = re.compile(r"\bimport\b.*\bget_db\b")


# ── ① with get_db() 블록 내 가공 (db/ 한정) ────────────────────────────────────
#
# 허용(정본 예시 db/reads/dashboard.py 기준): 커넥션 블록 안은 fetch 만 —
#   · conn.execute(...).fetchall()/fetchone()/fetchmany() 및 그 단순 대입
#   · placeholder 문자열 조립(ph = ",".join([...]))·config 리스트 리터럴
#   · execute+append(dict(row)) 루프(단일 루프)
#   · SQL 조립·INSERT 파라미터 빌드용 comprehension(fetch 결과 가공이 아님)
# 위반(검출): 커넥션 블록 안 중첩 루프(For/While 안의 For/While) = 커넥션 점유 중 집계.
# 이것이 in-connection 가공의 유일하게 확실한 AST 신호다. comprehension 은 SQL 조립·
# INSERT 파라미터 빌드(정상)와 fetch 결과 가공(위반)이 AST 로 구분 불가라 검출하지 않는다
# (게이트는 확실한 위반만·오탐 0 — CLAUDE.md 일관성 게이트 원칙). 현재 db/ 전체 0 위반.


def _is_get_db_with(node: ast.With) -> bool:
    for item in node.items:
        expr = item.context_expr
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "get_db":
            return True
    return False


def _has_nested_loop(body: list[ast.stmt]) -> bool:
    for stmt in body:
        for sub in ast.walk(stmt):
            if isinstance(sub, (ast.For, ast.While)):
                for inner in ast.walk(sub):
                    if inner is not sub and isinstance(inner, (ast.For, ast.While)):
                        return True
    return False


def check_get_db_processing(py_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not rel.startswith("db/"):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.With) or not _is_get_db_with(node):
                continue
            if _has_nested_loop(node.body):
                bad.append(f"{rel}:{node.lineno}: 커넥션 블록 내 중첩 루프 집계 — fetch 후 블록 밖에서 가공(B4)")
    return bad


# ── ② settings.py 외 os.getenv/os.environ ──────────────────────────────────────


def check_env_access(py_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if rel == "settings.py":
            continue
        if rel.startswith(("scripts/", "docs/", "tests/")):
            continue
        if rel in ENV_ALLOWLIST:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _ENV_RE.search(line):
                bad.append(f"{rel}:{i}: settings.py 외 os.getenv/environ — {stripped[:60]}")
    return bad


# ── ③ web/ await 없는 async def ─────────────────────────────────────────────────
#
# ARCHITECTURE 핵심규칙 6 / CONVENTIONS B3: 라우트 핸들러는 동기 def.
# async def 는 본문에 실제 await(SSE·to_thread·request.form) 있을 때만.
# 제외: async generator(yield 보유 — SSE 스트림은 def 로 못 바꿈).


def _async_has_await(node: ast.AsyncFunctionDef) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Await, ast.AsyncFor, ast.AsyncWith)):
            return True
    return False


def _is_async_generator(node: ast.AsyncFunctionDef) -> bool:
    for sub in ast.walk(node):
        # 중첩 함수 내부 yield 는 제외 — 이 함수 자신 스코프의 yield 만
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub is not node:
            continue
        if isinstance(sub, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _returns_streaming_response(node: ast.AsyncFunctionDef) -> bool:
    """SSE 핸들러 제외 — 반환 어노테이션이 StreamingResponse/EventSourceResponse 계열."""
    ann = node.returns
    ann_name = ""
    if isinstance(ann, ast.Name):
        ann_name = ann.id
    elif isinstance(ann, ast.Attribute):
        ann_name = ann.attr
    return ann_name in ("StreamingResponse", "EventSourceResponse")


def check_web_async_no_await(py_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not rel.startswith("web/"):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            if _async_has_await(node) or _is_async_generator(node) or _returns_streaming_response(node):
                continue
            bad.append(f"{rel}:{node.lineno}: await 없는 async def '{node.name}' — 동기 def 로(B3)")
    return bad


# ── ⑤ db/reads·writes get_db import 단일 경로 ──────────────────────────────────
#
# CONVENTIONS B1: `from db.connection import get_db` 단일(core 경유 금지).
# 상대경로 `from ..connection` 은 허용, `from ..core`/`from db.core` 경유만 위반.


def check_get_db_import_path(py_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not (rel.startswith("db/reads/") or rel.startswith("db/writes/")):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or "get_db" not in line or "import" not in line:
                continue
            if not _GET_DB_IMPORT_RE.search(line):
                continue
            if re.search(r"from\s+(\.\.core|db\.core|\.core)\s+import", line):
                bad.append(f"{rel}:{i}: get_db 를 core 경유 import — from db.connection 로(B1)")
    return bad


# ── ⑥ bypass_ssl_verification 전역패치 호출 위치 제한 ──────────────────────────
#
# CONVENTIONS B6: 전역 SSL 패치는 verify kwarg 못 받는 라이브러리(pykrx류) 전용 —
# 배치/스크립트 진입점에서만 호출. web 이 import 하는 모듈에서 호출 시 보안 회귀(전역 전파).
# (인라인 urllib3.disable_warnings 는 B6 가 허용 — 여기서 검사하지 않음.)


def check_ssl_bypass_location(py_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        # 검사기 자신은 제외 — 규칙 설명 문자열(docstring)의 호출 표기가 자기검출됨
        if rel.startswith(("batches/", "scripts/")) or rel == "utils/ssl_utils.py" \
                or rel.startswith("kernel/"):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # 호출(())만 위반 — import·docstring 언급은 제외
            if re.search(r"\bbypass_ssl_verification\s*\(", line):
                bad.append(f"{rel}:{i}: 전역 SSL 패치를 배치/스크립트 밖에서 호출(B6) — {stripped[:50]}")
    return bad


# ── ⑦ web/routes/ 에러 반환 JSONResponse (admin 제외) ──────────────────────────
#
# CONVENTIONS B2: web/routes/ 에러 반환은 raise HTTPException. web/admin/ 은 JSONResponse 관례(제외).
# 성공 응답용 JSONResponse(쿠키 부착 등, status_code 없음/200)는 위반 아님 —
# `return JSONResponse(..., status_code=4xx/5xx)` 만 검출.


def check_routes_error_jsonresponse(py_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in py_files:
        rel = _rel(f)
        if not rel.startswith("web/routes/"):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
                continue
            call = node.value
            func = call.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name != "JSONResponse":
                continue
            for kw in call.keywords:
                if kw.arg == "status_code" and isinstance(kw.value, ast.Constant) \
                        and isinstance(kw.value.value, int) and kw.value.value >= 400:
                    bad.append(f"{rel}:{node.lineno}: 에러 반환 JSONResponse(status {kw.value.value}) — raise HTTPException 로(B2)")
    return bad


# ── ⑨ frontend 비admin raw fetch() ─────────────────────────────────────────────


def _is_admin_ui(rel: str) -> bool:
    return "/admin/" in rel or rel.startswith("frontend/src/admin/")


def check_frontend_raw_fetch(ui_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if _is_admin_ui(rel) or rel in FETCH_WRAPPERS or rel in FETCH_ALLOWLIST:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue
            if _FETCH_RE.search(line):
                bad.append(f"{rel}:{i}: 비admin raw fetch() — useApi 경유(F1) — {stripped[:50]}")
    return bad


# ── ⑧ frontend hex 리터럴 (비활성 — --full 전용, P4 진행 중이라 sections 미편입) ──


def check_frontend_hex(ui_files: list[Path]) -> list[str]:
    bad: list[str] = []
    for f in ui_files:
        rel = _rel(f)
        if rel.endswith("constants/colors.ts") or _is_admin_ui(rel) or rel in HEX_ALLOWLIST:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue
            for m in _HEX_RE.finditer(line):
                bad.append(f"{rel}:{i}: hex 리터럴 {m.group(0)} — constants/colors.ts 또는 CSS var(F2)")
    return bad


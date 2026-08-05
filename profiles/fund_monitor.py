"""profiles/fund_monitor.py — fund_monitor 프로젝트 프로파일.

커널에서 걷어낸 fund_monitor 고유 이름을 전부 여기로 모았다. 스키마 정의와 각 항목의 뜻은
`profiles/_template.py` 가 정본이다 — 여기엔 값만 둔다.

이 파일이 커널 리팩터의 검증 기준이기도 하다. 커널이 이 프로파일을 받아 fund_monitor 레포에서
리팩터 전과 같은 판정을 내려야 이관이 끝난 것으로 본다.
"""

from __future__ import annotations

STAGE = "mature"


LAYERS: dict[str, str | None] = {
    "read":      "db/reads",
    "write":     "db/writes",
    "db":        "db",
    "web":       "web",
    "routes":    "web/routes",
    "ui":        "frontend/src",
    "ui_admin":  "frontend/src/admin",
    "ui_tokens": "frontend/src/constants/colors.ts",
    "tests":     "tests",
    "schema":    "db/schema",
    "shared":    "utils",
    "batch":     "batches",
}

FILES: dict[str, str | None] = {
    "settings": "settings.py",
    "ssl_util": "utils/ssl_utils.py",
}

SYMBOLS: dict[str, str | None] = {
    "db_accessor":        "get_db",
    "db_accessor_module": "db.connection",
    "ssl_bypass":         "bypass_ssl_verification",
    "error_response":     "JSONResponse",
}


SCOPE: dict[str, tuple[str, ...]] = {
    # 하네스 사본·내부자료·레거시 UI. 원본 코드는 "harnes/" 오타였고 실제 디렉토리는 harness/ 다.
    "exclude_all":     ("harness/", "idea/", "web/static/", "web/templates/"),
    "exclude_scratch": ("scripts/", "docs/"),
}


HUBS: tuple[str, ...] = (
    "CLAUDE.md", "AGENTS.md", "DEVGUIDE.md", "DESIGN_GUIDE.md", "README.md", "HARNESS.md",
)
HUB_DOMAIN_MD_IMPLICIT = True
HARNESS_MAP = "HARNESS.md"

MD: dict[str, tuple[str, ...]] = {
    "doc_exclude":   ("docs/", ".claude/", ".codex/", ".agents/", "EDITING.md"),
    "ref_exclude":   ("docs/", "idea/", "memory/"),
    "style_exclude": ("docs/", ".agents/", ".codex/", ".claude/skills/impeccable/", "EDITING.md"),
    "date_exempt":   ("dev/LESSONS.md",),
}


VOCAB: dict[str, tuple[str, ...]] = {
    "ui_denylist": (
        # design/UX.md — 자기설명 라벨·조어 금지
        "순신고가", "흡수력", "선점기회", "검증된수요", "단독미투",
        # 내부어 — 만든 사람만 아는 말. "관리자도 사용자다" 지적으로 화면에서 걷어냈다
        "백필", "미분석 (NULL)", "무결성", "파이프라인",
        "batch_log", "미매핑", "(LIKE)", "낙/비",
    ),
    "abbrev_prefixes": ("oper_", "rev_"),   # NAMING.md — op_*/revenue_* 를 쓴다
    "abbrev_names":    ("net",),
}


ALLOWLIST: dict[str, tuple[str, ...]] = {
    # 제네릭 래퍼(coerce·데코레이터·SSE)만. 신규 코드는 `# any-ok: 사유` 인라인 예외를 쓴다
    "py_any": (
        "db/reads/etf_common.py",
        "batches/equity/pykrx_setup.py",
        "utils/ttl_cache.py",
        "web/admin/_sse.py",
    ),
    # 다크 격리 스코프와 canvas/SVG 컨텍스트(CSS 변수 미해석) 잔존분 66개.
    # 목록이 길어 레포 쪽 `hex_allowlist.txt` 로 뺀다 — 이관 시 파일에서 읽어 여기에 합친다.
    "ui_hex": (),
    # 쓰기(POST) 또는 404=정상 시맨틱. 조회 훅으로 표현할 수 없는 것만이다.
    "ui_fetch": (
        "frontend/src/hooks/useMemberSession.ts",
        "frontend/src/utils/briefingApi.ts",
        "frontend/src/pages/News.tsx",
        "frontend/src/pages/NewsCompany.tsx",
        "frontend/src/components/briefing/useNoticeApplication.ts",
        "frontend/src/components/issues/useTaskReorder.ts",
        "frontend/src/components/peers/aum/AumBriefing.tsx",
    ),
    "ui_fetch_wrappers": ("frontend/src/hooks/useFetchApi.ts",),
    "env_access": ("utils/claude_cli.py",),   # os.environ 전체 순회로 subprocess env 상속
}


DOC_SYNC: list[dict[str, object]] = [
    {"doc": "DEVGUIDE.md", "code": "batch_runner.py",
     "kind": "int_consts", "marker": "_HOUR"},
    {"doc": "DEVGUIDE.md", "code": "settings.py",
     "kind": "env_keys", "section": "## .env 키 목록",
     # pykrx 가 KRX 로그인 시 .env 를 직접 읽는다 — settings.py 를 안 거치지만 문서엔 있어야 한다
     "allow": ("KRX_ID", "KRX_PW")},
]


BEHAVIOR_TESTED_ROOTS: tuple[str, ...] = (
    "analyst_reports/", "batches/", "businfo/", "dart/", "dept_issues/", "etf/",
    "kofia/", "kr_cycle/", "macro/", "market_briefing/", "news/", "us_cycle/",
)


# 사고 1건마다 붙은 fund_monitor 전용 게이트. 커널에서 걷어냈으니 이 레포의
# `harness_gates/` 아래에 옮겨 심어야 한다. 원본은 harness 레포의 `src/static_check_*.py` 다.
LOCAL_GATES: tuple[str, ...] = (
    "prompt_version",     # 프롬프트 본문↔헤더 버전 동시 갱신
    "krx_pacing",         # KRX 호출 간격 단일 정본
    "complete_date",      # 기준일 완전성 — bare MAX(date) 금지
    "batch_select",       # 배치 직접 SELECT 금지
    "llm_client",         # LLM 클라이언트 단일 정본
    "region_merge",       # region 국내+해외 합산 정본
    "admin_batch_paths",  # admin 배치 경로 레지스트리
    "roster_literals",    # 단일 정본 리터럴
    "web_param_guards",   # web 파라미터 가드 정본
)

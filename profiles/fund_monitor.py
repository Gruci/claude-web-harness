"""profiles/fund_monitor.py — fund_monitor 프로젝트 프로파일.

`src/static_check*.py` 14개 모듈에 흩어져 박혀 있던 프로젝트 고유 토큰 50개를 한곳에 모은 것이다.
스키마 정의와 각 항목의 의미는 `profiles/_template.py` 에 있다 — 여기엔 값만 둔다.

이 파일의 존재 이유는 회귀 검증이다. 커널이 이 프로파일을 받아 `src/` 의 현재 출력과
한 글자도 다르지 않게 판정해야 P2 가 끝난 것으로 본다.
"""

from __future__ import annotations

STAGE = "mature"


LAYERS: dict[str, str | None] = {
    "read":     "db/reads",
    "write":    "db/writes",
    "web":      "web",
    "routes":   "web/routes",
    "ui":        "frontend/src",
    "ui_admin":  "frontend/src/admin",
    "ui_tokens": None,   # P2 에서 실측 후 채운다 — 현재 HEX_ALLOWLIST 는 파일 단위 면제뿐이다
    "tests":    "tests",
    "batch":    "batches",
    "shared":   "utils",
}


SCOPE: dict[str, tuple[str, ...]] = {
    # 템플릿 참고 사본·내부자료·레거시 UI. 원본은 "harnes/" 오타였고 실제 디렉토리는 harness/ 다.
    "exclude_all":     ("harness/", "idea/", "web/static/", "web/templates/"),
    "exclude_scratch": ("scripts/", "docs/"),
}


HUBS: tuple[str, ...] = (
    "CLAUDE.md", "AGENTS.md", "DEVGUIDE.md", "DESIGN_GUIDE.md", "README.md", "HARNESS.md",
)
HUB_DOMAIN_MD_IMPLICIT = True


VOCAB: dict[str, tuple[str, ...]] = {
    "ui_denylist": (
        # design/UX.md — 자기설명 라벨·조어 금지
        "순신고가", "흡수력", "선점기회", "검증된수요", "단독미투",
        # 내부어 — 만든 사람만 아는 말. 2026-08-04 "관리자도 사용자다" 지적으로 화면에서 걷어냈다
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
    # P2 이관 예정 — 현재는 static_check_gates.py 의 HEX_ALLOWLIST(66) · FETCH_ALLOWLIST(14).
    # 파일 단위 목록이 길어 baselines/ 로 뺄지 여기 둘지는 이관 시점에 정한다.
    "ui_hex":   (),
    "ui_fetch": (),
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


# 사고 1건마다 하나씩 붙은 프로젝트 전용 게이트. 새 프로젝트는 이 튜플이 비어 있다.
LOCAL_GATES: tuple[str, ...] = (
    "prompt_version",     # ⑯ 프롬프트 본문↔헤더 버전 동시 갱신
    "krx_pacing",         # ⑰ KRX 호출 간격 단일 정본
    "complete_date",      # ⑱ 기준일 완전성 — bare MAX(date) 금지
    "batch_select",       # ⑲ 배치 직접 SELECT 금지
    "llm_client",         # ⑳ LLM 클라이언트 단일 정본
    "region_merge",       # ㉑ region 국내+해외 합산 정본
    "admin_batch_paths",  # ㉓ admin 배치 경로 레지스트리
    "roster_literals",    # ㉔ 단일 정본 리터럴
    "web_param_guards",   # ㉕ web 파라미터 가드 정본
)

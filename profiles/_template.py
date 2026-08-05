"""profiles/_template.py — 새 프로젝트가 채우는 유일한 파일.

커널은 이 파일 말고 프로젝트에 대해 아무것도 모른다. 게이트 판정 로직은 `kernel/gates/`,
훅 배선은 `.claude/settings.json` 이고, 여기엔 **이 프로젝트에서만 참인 이름과 어휘**만 담는다.

핵심 규약 하나: 값이 None 이거나 비어 있으면 그 게이트는 조용히 통과하지 않고 `[SKIP]` 으로
명시 출력된다. 지금까지의 실패 모드가 "레이어 이름이 안 맞아 대상 0개인데 [OK] 로 찍혀
지켜준다고 믿는 것"이었기 때문이다.

새 프로젝트 절차: 이 파일을 `profiles/<프로젝트명>.py` 로 복사 → 아는 것만 채운다 →
`python -m kernel.runner --adopt` 로 현재 위반을 동결하고 시작한다. 다 채울 필요 없다.
"""

from __future__ import annotations

# ── 프로젝트 성숙도 ────────────────────────────────────────────────────────────
# greenfield : MD 가 코드보다 먼저 나오는 시기. 아직 없는 경로 참조(④A)를 [REPORT] 로 강등한다
# growing    : 구조가 잡히는 중. 레이어 게이트는 선언된 것만 동작
# mature     : 전 게이트 강제. 예외는 allowlist·인라인 주석·baseline 셋뿐
STAGE = "greenfield"


# ── 레이어 이름 ────────────────────────────────────────────────────────────────
# 키는 커널이 아는 역할, 값은 이 프로젝트에서의 실제 경로다. 모르면 None 으로 둔다.
LAYERS: dict[str, str | None] = {
    "read":   None,     # SELECT 전용 레이어. 쓰기 SQL·commit 금지 게이트가 여기를 본다
    "write":  None,     # 변경 전용 레이어
    "web":    None,     # HTTP 핸들러. await 없는 async·에러 응답 형식 게이트가 여기를 본다
    "routes": None,     # web 안의 라우트 디렉토리. None 이면 web 을 그대로 쓴다
    "ui":     None,     # 프론트 소스 루트. hex 리터럴·raw fetch·배열 옵셔널 게이트 대상
    "ui_admin": None,   # ui 안에서 raw fetch 를 허용하는 구역. None 이면 예외 없음
    "ui_tokens": None,  # 색·타이포 정본 파일. hex 리터럴 게이트가 "저기 쓰라"고 가리킬 곳
    "tests":  "tests",  # 테스트 루트
    "batch":  None,     # 배치 스크립트. 직접 SELECT 금지 게이트 대상
    "shared": None,     # 공용 유틸. "재구현 금지" 계열 게이트의 정본 위치
}


# ── 검사 스코프 ────────────────────────────────────────────────────────────────
# exclude_all     : 어떤 게이트도 보지 않는다. 벤더 사본·참고 자료·레거시
# exclude_scratch : 일회성 스크립트. 구조 규칙(중첩 def·축약어·타입)만 면제된다
SCOPE: dict[str, tuple[str, ...]] = {
    "exclude_all":     (),
    "exclude_scratch": ("scripts/", "docs/"),
}


# ── MD 허브 ────────────────────────────────────────────────────────────────────
# 고아 MD 판정(④D)의 시드. 여기서 링크를 타고 도달 못 하는 MD 는 "읽힐 타이밍이 없는 문서"다.
HUBS: tuple[str, ...] = ("CLAUDE.md", "README.md", "HARNESS.md")

# 패키지명과 파일명이 같은 도메인 정본(`macro/MACRO.md`)을 총칭 라우팅으로 도달 인정할지.
HUB_DOMAIN_MD_IMPLICIT = True


# ── 프로젝트 어휘 ──────────────────────────────────────────────────────────────
# 게이트 로직은 커널에 있고 단어만 여기 있다. 리뷰에서 새 조어를 발견하면 그 문자열 그대로 넣는다.
VOCAB: dict[str, tuple[str, ...]] = {
    "ui_denylist":     (),   # 사용자에게 노출되면 안 되는 조어·내부어
    "abbrev_prefixes": (),   # 금지 축약 접두. 예: ("oper_", "rev_")
    "abbrev_names":    (),   # 금지 축약 단독 변수명. 예: ("net",)
}


# ── 예외 ───────────────────────────────────────────────────────────────────────
# 파일 단위 영구 면제. 신규 코드는 여기 등재 대신 인라인 주석(`# any-ok: 사유`)을 쓴다.
ALLOWLIST: dict[str, tuple[str, ...]] = {
    "py_any": (),
    "ui_hex": (),
    "ui_fetch": (),
}


# ── 문서 ↔ 코드 대조 ───────────────────────────────────────────────────────────
# 문서에 코드와 같은 값이 적혀 있는 곳. 한쪽만 고치면 게이트가 잡는다.
# kind: "int_consts"  — code 의 최상위 int 상수 vs doc 표의 시각/숫자 (marker 로 상수명 필터)
#       "env_keys"    — code 의 os.getenv 키 vs doc 의 키 목록, 양방향 diff
DOC_SYNC: list[dict[str, object]] = [
    # {"doc": "DEVGUIDE.md", "code": "batch_runner.py",
    #  "kind": "int_consts", "marker": "_HOUR"},
    # {"doc": "DEVGUIDE.md", "code": "settings.py",
    #  "kind": "env_keys", "section": "## .env 키 목록", "allow": ("KRX_ID",)},
]


# ── 행동 테스트 짝(⑫) 대상 ─────────────────────────────────────────────────────
# "깨지면 아무도 모르는" 수집·계산 모듈이 사는 곳. 비우면 이 게이트는 [SKIP] 이다.
BEHAVIOR_TESTED_ROOTS: tuple[str, ...] = ()


# ── 프로젝트 전용 게이트 ───────────────────────────────────────────────────────
# `gates_local/<name>.py` 를 로드한다. 사고가 나면 그때 하나씩 는다. 새 프로젝트는 비어 있다.
LOCAL_GATES: tuple[str, ...] = ()

"""profiles/_template.py — 새 프로젝트가 채우는 유일한 파일.

`<프로젝트 루트>/harness_profile.py` 로 복사해서 쓴다. 커널은 이 파일 말고 프로젝트에 대해
아무것도 모른다 — 판정 로직은 `kernel/gates/`, 훅 배선은 `.claude/settings.json` 이고,
여기엔 **이 프로젝트에서만 참인 이름과 어휘**만 담는다.

핵심 규약: 값이 비어 있으면 그 게이트는 조용히 통과하지 않고 `[SKIP]` 으로 사유와 함께 찍힌다.
채우면 켜지고, 안 채우면 안 켜졌다고 화면에 말한다. 다 채울 필요 없다 — 아는 것부터 채운다.
"""

from __future__ import annotations

# ── 성숙도 ─────────────────────────────────────────────────────────────────────
# greenfield : MD 가 코드보다 먼저 나오는 시기. 아직 없는 경로 참조와 하네스 지도 부재를
#              막지 않고 리포트로만 낸다. 새 프로젝트의 기본값이다
# growing    : 구조가 잡히는 중. 선언한 레이어의 게이트만 동작
# mature     : 전 게이트 강제. 예외는 allowlist·인라인 주석·baseline 셋뿐
STAGE = "greenfield"


# ── 레이어 ─────────────────────────────────────────────────────────────────────
# 키는 커널이 아는 역할, 값은 이 프로젝트에서의 실제 경로다. 모르면 None.
LAYERS: dict[str, str | None] = {
    "read":      None,   # 조회 전용. 쓰기 SQL·commit 금지 게이트가 여기를 본다
    "write":     None,   # 변경 전용
    "db":        None,   # read·write 를 아우르는 DB 레이어. 커넥션 점유 게이트가 본다
    "web":       None,   # HTTP 핸들러. await 없는 async 게이트가 본다
    "routes":    None,   # web 안의 라우트 디렉토리. 에러 응답 형식 게이트가 본다
    "ui":        None,   # 프론트 소스 루트. 이게 없으면 프론트 게이트 전부 [SKIP]
    "ui_admin":  None,   # 프론트 안에서 관례를 면제받는 구역(내부 도구 등)
    "ui_tokens": None,   # 색·타이포 정본 파일. hex 게이트가 "저기 쓰라"고 가리킬 곳
    "tests":     None,   # 테스트 루트
    "schema":    None,   # DDL 이 사는 곳. 저장 타입 게이트가 본다
    "shared":    None,   # 공용 유틸. 재구현 금지 계열 게이트의 정본 위치
    "batch":     None,   # 배치·스크립트 진입점. SSL 전역 패치가 허용되는 유일한 곳
}

# 경로가 아니라 파일 하나를 가리키는 것들
FILES: dict[str, str | None] = {
    "settings": None,    # 환경변수를 읽는 유일한 모듈. 예: "settings.py"
    "ssl_util": None,    # 전역 SSL 패치 정의부. 호출 위치 게이트의 예외
}

# 코드에서 이름으로 찾는 것들. 프레임워크마다 다르다.
SYMBOLS: dict[str, str | None] = {
    "db_accessor":        None,   # 커넥션 컨텍스트 헬퍼. 예: "get_db"
    "db_accessor_module": None,   # 그 헬퍼의 정본 모듈. 예: "db.connection"
    "ssl_bypass":         None,   # 전역 SSL 패치 함수명
    "error_response":     None,   # 에러를 감싸 반환하는 래퍼. 예: "JSONResponse"
}


# ── 검사 스코프 ────────────────────────────────────────────────────────────────
# exclude_all     : 어떤 게이트도 보지 않는다. 벤더 사본·참고 자료·레거시
# exclude_scratch : 일회성 스크립트. 구조 규칙(중첩 def·축약어·타입)만 면제된다
#
# clone 으로 하네스를 가져왔다면 그 자기 자산(픽스처·정답지·설명서)도 빼야 한다. 안 빼면
# 새 프로젝트가 자기 것도 아닌 위반을 안고 출발한다. 프리셋들이 `HARNESS_ASSETS` 로 묶어둔다.
SCOPE: dict[str, tuple[str, ...]] = {
    "exclude_all":     ("tests/fixtures/", "tests/golden/", "tests/build_fixture.py",
                        "tests/fixture_files.py", "tests/run_golden.py",
                        "PLAN.md", "docs/site/"),
    "exclude_scratch": (),
}


# ── MD ─────────────────────────────────────────────────────────────────────────
HUBS: tuple[str, ...] = ()          # 고아 판정의 시드. 여기서 도달 못 하는 MD 는 읽힐 일이 없다
HUB_DOMAIN_MD_IMPLICIT = True       # `macro/MACRO.md` 같은 동명 정본을 총칭 라우팅으로 인정
HARNESS_MAP = "HARNESS.md"          # 훅·에이전트·스킬 지도 파일

MD: dict[str, tuple[str, ...]] = {
    "doc_exclude":   (),   # 정본 취급하지 않는 MD. 작업 산출물·하네스 내부 문서
    "ref_exclude":   (),   # 백틱 경로가 실존하지 않아도 되는 접두. 아카이브·외부 메모
    "style_exclude": (),   # 작성 규칙 검사에서 뺄 MD. 벤더 사본·동적 파일
    "date_exempt":   (),   # 날짜 태그 밀도 리포트 면제. 경위를 남기는 문서 하나 정도
}


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
    "py_any":            (),
    "ui_hex":            (),
    "ui_fetch":          (),
    "ui_fetch_wrappers": (),   # 공용 래퍼 자신 — 검사 대상이 아니다
    "env_access":        (),
    "ui_platform":       (),   # 브라우저 API 래퍼 정본. 비우면 그 게이트는 [SKIP]
}


# ── 편집 자체를 막을 레거시 경로 ───────────────────────────────────────────────
# (경로 조각, 확장자) 쌍. 확장자가 None 이면 그 디렉토리 전체. 저장 훅이 되돌리라고 막는다.
# 옮기는 중인 구코드가 있을 때만 쓴다. 이사가 끝나면 비운다.
LEGACY_PATHS: tuple[tuple[str, "str | None"], ...] = ()


# ── 루트에 남아도 되는 앱 파일 ─────────────────────────────────────────────────
# 배치 게이트는 루트 앱 코드를 막는다. 설정 모듈처럼 루트가 제자리인 것만 여기 적는다.
ROOT_FILES: tuple[str, ...] = ()      # 예: ("settings.py", "batch_runner.py")


# ── 문서 ↔ 코드 대조 ───────────────────────────────────────────────────────────
# 문서에 코드와 같은 값이 적혀 있는 곳. 한쪽만 고치면 게이트가 잡는다.
# kind "int_consts" : code 의 최상위 int 상수 vs doc 표의 숫자 (marker 로 상수명 필터)
# kind "env_keys"   : code 의 os.getenv 키 vs doc 의 키 목록, 양방향 diff
DOC_SYNC: list[dict[str, object]] = [
    # {"doc": "DEVGUIDE.md", "code": "scheduler.py", "kind": "int_consts", "marker": "_HOUR"},
    # {"doc": "DEVGUIDE.md", "code": "settings.py", "kind": "env_keys",
    #  "section": "## .env 키 목록", "allow": ()},
]


# ── 행동 테스트 짝 대상 ────────────────────────────────────────────────────────
# "깨지면 아무도 모르는" 수집·계산 모듈이 사는 곳. 비우면 이 게이트는 [SKIP] 이다.
BEHAVIOR_TESTED_ROOTS: tuple[str, ...] = ()


# ── 사고 기록 ──────────────────────────────────────────────────────────────────
# 사고 절마다 `> 강제: 검사 N` 또는 `> 강제: 산문 전용 — 사유` 선언을 요구한다.
# 산문 전용으로 남은 목록이 곧 다음에 게이트로 올릴 후보다. None 이면 [SKIP].
LESSONS_DOC: str | None = None        # 예: "dev/LESSONS.md"


# ── 에이전트 모델 정책 ─────────────────────────────────────────────────────────
# 역할별 (model, effort) 고정. 판단은 위로, 볼륨은 아래로 — 그 배정의 정본이다.
# 여기 없는 에이전트는 제약하지 않는다. 등재가 곧 계약이다.
AGENT_MODEL_POLICY: dict[str, tuple[str, str]] = {
    # "executor": ("fable", "high"),     # 완결된 설계서 통째 실행 — 저판단 고볼륨
    # "backend":  ("opus", "high"),      # 레이어 규칙 판단
    # "qa":       ("sonnet", "medium"),  # 경계면 대조 — 볼륨은 크고 판단은 좁다
}


# ── 프로젝트 전용 게이트 ───────────────────────────────────────────────────────
# 이 레포의 `harness_gates/<이름>.py` 를 로드한다. 각 모듈은 아래를 노출한다:
#
#   def run(py_files: list[Path], ui_files: list[Path]) -> list[tuple[str, list[str]]]:
#       return [("게이트 제목", ["경로:줄: 사유", ...])]
#
# 사고가 나면 그때 하나씩 는다. 새 프로젝트는 비어 있고, 커널은 이 목록을 모른 채 배포된다.
LOCAL_GATES: tuple[str, ...] = ()

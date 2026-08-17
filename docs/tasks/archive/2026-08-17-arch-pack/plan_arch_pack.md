# docs/tasks/plan_arch_pack.md — 아키텍처팩(ARCH) 도입 설계

> 담는 것: kernel/arch.py + kernel/archs/ 신설과 [SKIP]→[N/A] 아키텍처 축 확장의 구현 설계 — 결정·스니펫·파일 설계표·Todo. 담지 않는 것: 코드 실물 정독 근거(→ `research_arch_pack.md`). 읽는 시점: 승인 심사와 3단계 구현.

## 접근 방식 — 한 문단

언어팩 패턴을 아키텍처 축에 그대로 복제한다. 팩은 `NOT_APPLICABLE: dict[slug, 사유]` 하나만 선언하는 순수 데이터 파일이고, `kernel/runner.py`의 `_entry()`가 이미 모든 게이트에서 `profile.not_applicable(slug)`를 최우선 조회하므로(runner.py:128) **게이트 배선 수정 없이 slug 선언만으로 전 게이트에 N/A가 통한다** — profile 키가 없어 끌 수단이 없던 `api_array`까지 포함이다. 게이트 코드의 물리 이동은 하지 않는다. 언어팩도 검사 코드를 팩에 담지 않는다 — 팩은 선언, 판정은 `kernel/gates/`라는 기존 대칭을 유지한다.

## 리서치 미해결 질문 10 — 결정

| # | 질문 | 결정 | 근거 |
|---|------|------|------|
| 1 | N/A 채널 | 기존 `NOT_APPLICABLE` 단일 dict 유지. 소스 접두("go: "·"headless: ")를 **병합 시점에 베이킹**하고 러너의 f-string 접두를 제거 | 러너 수정 2줄로 접두 오염 해소. 별도 채널·함수 신설 불필요 |
| 2 | 팩 선언 형식 | slug 직접 나열 dict | "레이어→게이트 유도"는 커널에 매핑표가 필요한 투기적 기계 — YAGNI |
| 3 | 병합 승자 | 언어팩 → 아키텍처팩 → 프로파일, 나중이 이김 | 기존 원칙("프로젝트 사정이 언어 관례보다 우선") 연장. 결정적·1줄 문서화 |
| 4 | N/A vs TOOL | 기존 순서 유지 (N/A > TOOL) | 아키텍처상 없는 규칙엔 파서 부재가 무의미 |
| 5 | ARCH 기본값 | `None` — 미선언이면 오늘의 SKIP 동작 그대로. 프리셋 4종은 전부 명시 선언 | 기존 프로파일 무손상 + 암묵 편입 금지 |
| 6 | 조건부 5개 | `ui_jargon`·`ts_any`·`api_array`는 화면 부재 팩의 N/A 목록에. `env_access`·`file_placement`는 보편 잔류 — 어떤 팩에도 안 넣음 | 배선이 아키텍처 전제인 3개만 팩 소관. 환경변수 경유·배치 규칙은 아키텍처 무관 |
| 7 | 물리 이동 | 없음. 예외 하나 — `check_reads_writes`를 `core.py`→`layers.py` 이관(slug 불변) | core.py 머리의 "레이어를 모르는 검사만" 선언 위반 해소. baseline은 slug 기준이라 무영향 |
| 8 | `_LAYER_KEYS` 일반화 | 이번 범위 제외 | 커스텀 레이어를 선언할 두 번째 실아키텍처가 없는 상태의 일반화는 투기 |
| 9 | --doctor | LANG 줄 옆에 ARCH 1줄 병기 + N/A 목록 라벨 문구 수정 | 기존 `print_language_report`가 `NOT_APPLICABLE`을 이미 순회 — 베이킹 덕을 자동으로 봄 |
| 10 | 골든 재생성 | `--update` 후 예상 diff 목록과 수동 대조를 Todo로 명문화 (아래 검증 절) | 완전 문자열 일치 대조의 안전망 유지 |

## shipped 팩 3종과 slug 집합

- UI7 = `ui_jargon` `ts_any` `raw_fetch` `hex_literal` `responsive` `browser_api` `api_array`
- WEB2 = `web_async` `routes_error`

| 팩 | 뜻 | NOT_APPLICABLE |
|----|----|----|
| `web_layered` | 화면+서버 풀스택 | `{}` — 전 게이트 성립 선언 |
| `backend_only` | 서버는 있고 화면이 없다 | UI7 |
| `headless` | 웹도 화면도 없다 — 배치·CLI·라이브러리 | UI7 + WEB2 (9종) |

DB 계열(`reads_writes` 등 4종)은 어느 팩에도 안 넣는다 — 배치·라이브러리도 DB를 가질 수 있어 "정의상 부재"가 아니다. 프로젝트별 부재는 기존 프로파일 `NOT_APPLICABLE` 채널이 담당한다.

배정: `web_fastapi_react`·`fund_monitor` → web_layered / `api_fastapi` → backend_only / `batch_python` → headless / 하네스 자신(`harness_profile.py`) → headless / go 픽스처 → headless.

## 파일 설계표

| 파일 | 단일 책임 | 성격 | 규모 |
|------|----------|------|------|
| `kernel/arch.py` 신설 | 아키텍처팩 로더 — pack_path·available·load, 깨진 팩은 기본값 폴백 | 신규 | ~55줄 |
| `kernel/archs/web_layered.py` 신설 | 풀스택 선언 (빈 N/A) | 신규 | ~5줄 |
| `kernel/archs/backend_only.py` 신설 | 화면 부재 선언 (UI7) | 신규 | ~15줄 |
| `kernel/archs/headless.py` 신설 | 웹·화면 부재 선언 (UI7+WEB2) | 신규 | ~17줄 |
| `kernel/profile.py` | ARCH 키 로드 + 3소스 병합 + 접두 베이킹 헬퍼 | 수정 | +12줄 |
| `kernel/runner.py` | `_entry`·`_syntax_section`의 f-string 접두 제거, reads_writes import 교체 | 수정 | 3줄 |
| `kernel/gates/core.py` | `check_reads_writes` 제거 | 수정 | −21줄 |
| `kernel/gates/layers.py` | `check_reads_writes` 수용 | 수정 | +21줄 |
| `profiles/_template.py` | ARCH 블록 문서화 (LANG 블록 병기) | 수정 | +8줄 |
| 프리셋 4종 (`profiles/*.py`) | `ARCH = "<팩>"` 1줄씩 | 수정 | 4×1줄 |
| `harness_profile.py` (하네스 자신) | `ARCH = "headless"` | 수정 | 1줄 |
| `harness_install.py` | doctor에 ARCH 병기·라벨 문구 | 수정 | +3줄 |
| `tests/fixture_files.py` | 픽스처 프로파일 리터럴에 `ARCH = "web_layered"` | 수정 | 1줄 |
| `tests/fixture_go.py` | `ARCH = "headless"` | 수정 | 1줄 |
| `tests/golden/{bare,full,go}.txt` | `--update` 재생성 + 수동 diff 검토 | 재생성 | — |
| `HARNESS.md` | 아키텍처팩 절 신설·구성 지도 갱신 (검사 28 대조 대상) | 수정 | +10줄 |
| `README.md`·`README.en.md` | §5.3 설정표에 `ARCH` 행 | 수정 | 각 1줄 |

400줄 근접 파일 없음. 화면 작업 아님 — 반응형 설계표 해당 없음.

## 스니펫 — 실물

### kernel/arch.py (신설, 전문)

```python
"""kernel/arch.py — 아키텍처팩 로더.

아키텍처 하나를 늘리는 비용을 **데이터 파일 하나**로 만든다. `kernel/lang.py` 와 같은
골격이고, 선언은 하나뿐이다.

  NOT_APPLICABLE   이 아키텍처에서는 규칙 자체가 성립하지 않는 게이트와 그 사유

언어팩과 나뉘는 선: 언어팩은 "검사기가 그 언어를 이해하는 방법"이고, 아키텍처팩은
"이 프로젝트 형태에 어떤 레이어가 존재하는가"다. 화면 없는 서비스의 UI 게이트가
[SKIP](설정을 안 채움)이 아니라 [N/A](채울 것이 없음)로 찍히게 하는 것이 존재 이유다.

실물은 `kernel/archs/<이름>.py` 이고, 프로파일의 `ARCH` 가 어느 것을 쓸지 정한다.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from kernel.context import ROOT

SHIPPED_DIR = Path(__file__).resolve().parent / "archs"
PROJECT_DIR = "profiles/arch"

DEFAULTS: dict[str, Any] = {"NOT_APPLICABLE": {}}


def pack_path(name: str) -> Path | None:
    """이 아키텍처팩의 실물. 프로젝트 것이 커널 것을 이긴다."""
    for candidate in (ROOT / PROJECT_DIR / f"{name}.py", SHIPPED_DIR / f"{name}.py"):
        if candidate.is_file():
            return candidate
    return None


def available() -> list[str]:
    names: set[str] = set()
    for directory in (SHIPPED_DIR, ROOT / PROJECT_DIR):
        if directory.is_dir():
            names |= {p.stem for p in directory.glob("*.py") if not p.stem.startswith("_")}
    return sorted(names)


def load(name: str | None) -> dict[str, Any]:
    """아키텍처팩을 읽는다. 이름이 없거나 못 찾거나 깨졌으면 기본값(전 게이트 성립)."""
    pack: dict[str, Any] = {"NOT_APPLICABLE": {}}
    if not name:
        return pack
    path = pack_path(name)
    if path is None:
        return pack
    spec = importlib.util.spec_from_file_location(f"_arch_{name}", path)
    if spec is None or spec.loader is None:
        return pack
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return pack                     # 깨진 팩은 기본값으로 — 러너를 크래시시키지 않는다
    given = getattr(module, "NOT_APPLICABLE", None)
    if given:
        pack["NOT_APPLICABLE"] = dict(given)
    return pack
```

### kernel/archs/headless.py (신설, 전문 — backend_only는 UI7만 남긴 부분집합)

```python
"""kernel/archs/headless.py — 웹도 화면도 없는 아키텍처. 배치·CLI·라이브러리."""

NOT_APPLICABLE = {
    "web_async":    "웹 서버가 없는 아키텍처",
    "routes_error": "웹 서버가 없는 아키텍처",
    "ui_jargon":    "화면 레이어가 없는 아키텍처",
    "ts_any":       "화면 레이어가 없는 아키텍처",
    "raw_fetch":    "화면 레이어가 없는 아키텍처",
    "hex_literal":  "화면 레이어가 없는 아키텍처",
    "responsive":   "화면 레이어가 없는 아키텍처",
    "browser_api":  "화면 레이어가 없는 아키텍처",
    "api_array":    "화면 레이어가 없는 아키텍처",
}
```

### kernel/profile.py — ARCH 로드와 접두 베이킹 (LANG 블록 뒤, :104-106 교체)

```python
# ── 아키텍처 ──────────────────────────────────────────────────────────────────
#
# 이 프로젝트 형태에 어떤 레이어가 존재하는가. 미선언(None)이면 아무것도 N/A 로
# 돌리지 않는다 — ARCH 도입 전 프로파일의 동작이 그대로 보존된다.
ARCH: str | None = getattr(_MOD, "ARCH", None) if _MOD else None
_ARCH_PACK = arch.load(ARCH)


def _na_prefixed(entries: dict[str, str], tag: str | None) -> dict[str, str]:
    """N/A 사유에 출처 접두를 베이킹한다. 러너는 이 문자열을 그대로 찍는다."""
    label = tag or "미선언"
    return {slug: f"{label}: {reason}" for slug, reason in entries.items()}


# 병합 순서: 언어팩 → 아키텍처팩 → 프로파일. 나중이 이긴다 —
# 프로젝트 사정이 언어·아키텍처 관례보다 우선이라는 기존 원칙의 연장이다.
NOT_APPLICABLE: dict[str, str] = _na_prefixed(dict(_PACK["NOT_APPLICABLE"]), SYNTAX)
NOT_APPLICABLE.update(_na_prefixed(_ARCH_PACK["NOT_APPLICABLE"], ARCH))
if _MOD and getattr(_MOD, "NOT_APPLICABLE", None):
    NOT_APPLICABLE.update(_na_prefixed(dict(_MOD.NOT_APPLICABLE), SYNTAX))
```

상단 import에 `from kernel import arch` 추가. `not_applicable()`·`_LAYER_KEYS`·`layer()`는 무수정.

### kernel/runner.py — 접두 제거 (2곳: :130, :144)

```python
# 변경 전
return (slug, title, [], ("N/A", f"{profile.SYNTAX}: {unneeded}"))
# 변경 후 — 접두는 profile 병합 시점에 이미 베이킹돼 있다
return (slug, title, [], ("N/A", unneeded))
```

`:175`의 `core.check_reads_writes` → `layers.check_reads_writes`.

### profiles/_template.py — ARCH 블록 (LANG 블록 :25-35 아래 병기)

```python
# ── 아키텍처 ── 이 프로젝트 형태에 어떤 레이어가 존재하는가. kernel/archs/ 팩 이름 하나.
#   web_layered   화면+서버 풀스택 — 전 게이트 성립
#   backend_only  서버는 있고 화면이 없다 — 화면 게이트 7종 [N/A]
#   headless      웹도 화면도 없다 (배치·CLI·라이브러리) — +웹 게이트 2종 [N/A]
# 미선언이면 아무것도 [N/A] 로 돌리지 않는다. [SKIP] 은 "설정을 안 채움",
# [N/A] 는 "아키텍처상 채울 것이 없음" — 이 구분이 ARCH 의 존재 이유다.
ARCH: str | None = None
```

### harness_install.py — doctor 병기 (:118-119 인접, :124 라벨)

```python
from kernel import arch, lang, linters

print(f"쓸 수 있는 언어팩: {' '.join(lang.available())}")
print(f"쓸 수 있는 아키텍처팩: {' '.join(arch.available())}\n")
print(f"현재 설정 — LANG={profile.LANG!r} SYNTAX={profile.SYNTAX!r} ARCH={profile.ARCH!r}")
# :124 라벨 교체
print("\n이 언어·아키텍처에서 해당 없는 검사 (손실 아님):")
```

## 브레이킹 체인지 · 트레이드오프

| 항목 | 내용 |
|------|------|
| 기존 프로파일 (ARCH 미선언) | **무손상** — `getattr` 기본 None → 빈 팩 → 오늘의 SKIP 동작 그대로 |
| 골든 3종 | bare.txt 무변경 / full.txt 무변경 (web_layered = 빈 N/A) / go.txt ~10줄 변경 — 9줄 SKIP→N/A + `web_async` 사유가 `go:`→`headless:`로 덮임(결정 3의 의도된 결과) |
| doctor 출력 | N/A 목록 사유에 출처 접두가 붙음 — 정보 증가, 소비자는 사람뿐 |
| 훅 | 무변경 — 두 훅은 returncode만 보는 블랙박스, trace.py는 `[FAIL]`만 매치 (research §4) |
| baseline | slug 불변이라 무영향. `check_reads_writes` 이관도 slug 유지 |
| 트레이드오프 | `_LAYER_KEYS` 일반화 보류 — 커스텀 레이어가 필요한 아키텍처는 아직 못 담는다. 두 번째 실수요 등장 시 후속 과업 |
| 체커 선실행 | N/A 게이트도 체커는 돈다(무해한 낭비). 오늘의 SKIP 경로가 이미 빈 입력으로 전 체커를 돌리고 있어 새 크래시 표면 없음 |

## Todo — 구현 순서

1. `kernel/arch.py` + `kernel/archs/` 3팩 생성
2. `kernel/profile.py` ARCH 로드·베이킹 병합
3. `kernel/runner.py` 접두 제거 2곳 + import 교체
4. `check_reads_writes` core→layers 이관 (core.py 머리 주석은 이관 후 자연 정합 — 갱신 불필요 여부 확인)
5. `profiles/_template.py` ARCH 블록 + 프리셋 4종 선언 + 하네스 자신 `harness_profile.py`
6. `harness_install.py` doctor 병기
7. 픽스처 2종에 ARCH 추가 → `python -X utf8 tests/run_golden.py --update` → **수동 diff 검토**: 위 브레이킹 표의 예상 변경만 있는지 확인. 예상 외 diff 발견 시 STOP·원인 규명
8. `python -X utf8 -m kernel.runner` 실행 — 하네스 자신에서 UI7+WEB2가 `[N/A ] headless: …`로 전환됨을 출력으로 확인
9. `HARNESS.md`·`README.md`·`README.en.md` 같은 턴 갱신 → 전체 게이트 재실행 → archive 이동

## 완료 기준

- `tests/run_golden.py` (인자 없음·`--bare`) exit 0
- 하네스 자신의 러너 출력에서 SKIP 17개 중 9개가 `[N/A ] headless:` 접두로 전환
- go 골든의 기존 언어 N/A 줄(`go: 클로저…` 등) 바이트 불변
- 검사 28(하네스 지도)·27(고아 MD) 포함 전 게이트 통과

"""kernel/runner.py — 게이트를 모아 돌리고 결과를 등급으로 찍는다.

사용:
  python -X utf8 -m kernel.runner                전 게이트. 위반이 있으면 exit 1
  python -X utf8 -m kernel.runner --file <경로>  방금 저장한 파일 하나만 (작성 시점 훅 경유)

출력 등급:
  [OK]     해당 섹션 위반 0건
  [FAIL]   강제 위반 — 총계에 합산되고 exit 1 을 만든다
  [REPORT] 연성 신호 — 오탐 여지가 있어 합산하지 않는다
"""

from __future__ import annotations

import sys
from pathlib import Path

from kernel.context import ROOT, _rel, tracked_py_files, tracked_ui_files
from kernel.gates import api_types, core, layers, md_graph, md_style, schema, tests_pairing
from kernel.local import batches, complete_date, dup, krx, llm, prompt, region

# (제목, 위반 목록, 건너뛴 사유). 사유가 있으면 [SKIP] — 대상이 0개였다는 뜻이다.
Section = tuple[str, list[str], "str | None"]

# 검사 자체를 하지 않는 트리 — 벤더 사본·참고 자료·레거시.
SKIP_PREFIXES = ("harness/", "idea/", "web/static/", "web/templates/")
# 전역 교차검사(④·⑯)를 재실행하지 않는 MD — 하네스 내부 문서와 작업 산출물.
LOCAL_MD_PREFIXES = (".claude/", "docs/")
UI_PREFIX = "frontend/src/"

NO_PY = "검사할 .py 없음"
NO_UI = "프론트 소스 없음"
NO_SRC = "검사할 소스 없음"
NO_WEB = "web 레이어 없음"
NO_BATCH = "배치 디렉토리 없음"


def _print_style_reports(reports: list[str]) -> None:
    """⑬ 리포트 항목 — 오탐 여지가 있어 total 에 합산하지 않는다(강제 아님)."""
    for report in reports:
        print(f"[REPORT] {report}")


def _print_sections(sections: list[Section]) -> int:
    total = 0
    for title, violations, skipped in sections:
        if skipped:
            print(f"[SKIP] {title} — {skipped}")
        elif violations:
            total += len(violations)
            print(f"\n[FAIL] {title} — {len(violations)}건")
            for v in violations:
                print(f"   - {v}")
        else:
            print(f"[OK]   {title}")
    return total


def _under(files: list[Path], *prefixes: str) -> list[Path]:
    return [f for f in files if _rel(f).startswith(prefixes)]


def _entry(title: str, violations: list[str], targets: list[Path], need: str) -> Section:
    """대상이 하나도 없으면 [SKIP]. `위반 0건`과 `대상 0개`를 구분하는 것이 이 함수의 전부다.

    지금까지의 실패 모드가 여기 있었다 — 레이어 이름이 안 맞아 대상이 0개인데 [OK] 로 찍혀,
    지켜주지 않는 게이트를 지켜준다고 믿었다.
    """
    if not targets:
        return (title, [], need)
    return (title, violations, None)


def _build_sections(
    files: list[Path], ui_files: list[Path], include_md: bool, md_files: list[Path]
) -> list[Section]:
    both = files + ui_files
    reads = _under(files, "db/reads/")
    web = _under(files, "web/")
    batch = _under(files, "batches/")
    admin = _under(files, "web/admin/")

    sections: list[Section] = [
        _entry("400줄 초과", core.check_line_limit(files), files, NO_PY),
        _entry("중첩 def(클로저) 전 레이어", core.check_closures(files), files, NO_PY),
        _entry("db/reads 쓰기 SQL/commit", core.check_reads_writes(files), reads, "읽기 레이어 없음"),
        _entry("축약어 net 변수", core.check_net_abbrev(files), files, NO_PY),
        _entry("축약어 oper_/rev_", core.check_oper_rev_abbrev(both), both, NO_SRC),
        _entry("UI 라벨 금칙어", core.check_ui_jargon(ui_files), ui_files, NO_UI),
        _entry("⑩py Any 타입힌트", core.check_py_any(files), files, NO_PY),
        _entry("⑪frontend TS any", core.check_ts_any(ui_files), ui_files, NO_UI),
        _entry("①get_db 커넥션 내 가공(B4)", layers.check_get_db_processing(files),
               _under(files, "db/"), "DB 레이어 없음"),
        _entry("②settings 외 os.getenv(B5)", layers.check_env_access(files), files, NO_PY),
        _entry("③web await없는 async def(B3)", layers.check_web_async_no_await(files), web, NO_WEB),
        _entry("⑤get_db import 단일경로(B1)", layers.check_get_db_import_path(files),
               _under(files, "db/reads/", "db/writes/"), "읽기·쓰기 레이어 없음"),
        _entry("⑥전역 SSL 패치 위치(B6)", layers.check_ssl_bypass_location(files), files, NO_PY),
        _entry("⑦routes 에러 JSONResponse(B2)", layers.check_routes_error_jsonresponse(files),
               _under(files, "web/routes/"), "라우트 디렉토리 없음"),
        _entry("⑨frontend 비admin raw fetch(F1)", layers.check_frontend_raw_fetch(ui_files),
               ui_files, NO_UI),
        _entry("⑧frontend hex 리터럴(F2)", layers.check_frontend_hex(ui_files), ui_files, NO_UI),
        _entry("⑫수집/계산 모듈 행동 테스트 짝(B20)", tests_pairing.check_module_test_pairing(files),
               _under(files, *tests_pairing.DOMAIN_PREFIXES), "수집·계산 패키지 없음"),
        _entry("⑭DDL 저장 타입 잘림(B21)", schema.check_ddl_lossy_types(files),
               _under(files, "db/schema"), "스키마 디렉토리 없음"),
        _entry("⑮API 응답 배열 필드 옵셔널(F3)", api_types.check_api_array_optional(ui_files),
               ui_files, NO_UI),
        _entry("⑰KRX 호출 간격 단일 정본(B22)", krx.check_krx_call_pacing(files), batch, NO_BATCH),
        _entry("⑱기준일 완전성(B23)", complete_date.check_bare_latest_date(files),
               reads + web, "읽기 경로 없음"),
        _entry("⑲배치 직접 SELECT 금지(B13)", batches.check_batches_direct_select(files),
               batch, NO_BATCH),
        _entry("⑳LLM 클라이언트 단일 정본(B18)", llm.check_llm_single_client(files), files, NO_PY),
        _entry("㉑region 합산 정본 경유(F16)", region.check_region_merge_source(ui_files),
               ui_files, NO_UI),
        _entry("㉒py 헤더 경로 주석 일치", core.check_header_path_comment(files), files, NO_PY),
        _entry("㉓admin 배치 경로 레지스트리(B24)", batches.check_admin_batch_paths(files),
               admin, "admin 디렉토리 없음"),
        _entry("㉔단일 정본 리터럴(로스터·라벨·분기)",
               dup.check_single_source_literals(files, ui_files), both, NO_SRC),
        _entry("㉕web 파라미터 가드 정본(clamp·market·프롬프트CRUD)",
               dup.check_web_param_guards(files) + dup.check_admin_prompt_crud(files), web, NO_WEB),
    ]
    if md_files:
        hard, soft = md_style.check_md_style(md_files)
        sections.append(("⑬ MD 작성 규칙(dev/MD_STANDARD.md)", hard, None))
        _print_style_reports(soft)
    if include_md:
        # 전역 교차검사 — 파일 목록이 아니라 레포 전체를 스스로 훑으므로 스코프 판정이 없다.
        sections += [
            ("④A MD 경로 참조 실존", md_graph.check_md_path_refs(), None),
            ("④B 배치 스케줄(DEVGUIDE↔batch_runner)", md_graph.check_batch_schedule(), None),
            ("④C .env 키(DEVGUIDE↔settings)", md_graph.check_env_keys(), None),
            ("④D 고아 MD(허브 도달 불가)", md_graph.check_md_orphans(), None),
            ("④E 하네스 지도 대조(HARNESS↔실물)", md_graph.check_harness_map(), None),
            ("⑯프롬프트 본문↔헤더 버전", prompt.check_prompt_version_bump(), None),
        ]
    return sections


def tracked_md_files() -> list[Path]:
    """게이트 ⑬ 대상 — 추적 중인 .md 중 스타일 검사 스코프에 드는 것."""
    from kernel.context import _ls_files
    return [ROOT / rel for rel in _ls_files("*.md")
            if md_style.style_target(rel) and (ROOT / rel).is_file()]


def _single_file_lists(raw_path: str) -> tuple[list[Path], list[Path], bool, list[Path]]:
    """--file 모드: 대상 파일 하나를 (py, ui, md전역검사여부, md스타일대상)으로 분류."""
    p = Path(raw_path).resolve()
    try:
        rel = p.relative_to(ROOT).as_posix()
    except ValueError:
        return [], [], False, []
    if not p.exists() or rel.startswith(SKIP_PREFIXES):
        return [], [], False, []
    if p.suffix == ".py":
        return [p], [], False, []
    if p.suffix in (".ts", ".tsx") and rel.startswith(UI_PREFIX):
        return [], [p], False, []
    if p.suffix == ".md":
        # ④A~E 는 전역 교차검사라 정본 MD 편집 시에만 재실행. ⑬ 스타일은 그 파일만.
        style = [p] if md_style.style_target(rel) else []
        return [], [], not rel.startswith(LOCAL_MD_PREFIXES), style
    return [], [], False, []


def main(argv: list[str]) -> int:
    # Windows cp949 콘솔에서 위반 라인(유니코드 포함) 출력 크래시 방지
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(errors="replace")
    if len(argv) >= 2 and argv[0] == "--file":
        files, ui_files, include_md, md_files = _single_file_lists(argv[1])
        if not files and not ui_files and not include_md and not md_files:
            return 0
    else:
        files, ui_files, include_md = tracked_py_files(), tracked_ui_files(), True
        md_files = tracked_md_files()
    total = _print_sections(_build_sections(files, ui_files, include_md, md_files))

    if total:
        print(f"\n총 {total}건 위반 (활성 게이트).")
        return 1
    print("\n활성 게이트 모두 통과.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

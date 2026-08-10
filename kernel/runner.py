"""kernel/runner.py — 게이트를 모아 돌리고 결과를 등급으로 찍는다.

사용:
  python -X utf8 -m kernel.runner                전 게이트. 위반이 있으면 exit 1
  python -X utf8 -m kernel.runner --file <경로>  방금 저장한 파일 하나만 (작성 시점 훅 경유)

출력 등급:
  [OK]     검사했고 위반 0건
  [SKIP]   **검사할 대상이 없었다.** 프로파일에 레이어·어휘 선언이 없으면 여기로 온다
  [FAIL]   강제 위반 — 총계에 합산되고 exit 1 을 만든다
  [REPORT] 연성 신호 — 오탐 여지가 있어 합산하지 않는다

[OK] 와 [SKIP] 을 가르는 것이 이 러너의 핵심이다. 이전 하네스는 레이어 이름이 안 맞아 대상이
0개인데도 [OK] 로 찍어, 지켜주지 않는 게이트를 지켜준다고 믿게 만들었다.

각 섹션은 slug 를 갖는다. slug 는 `harness_baseline.txt` 의 동결 키를 겸한다 — 설치 시점에
이미 있던 위반을 (slug, 파일) 단위로 얼려서 초록불에서 출발하게 하는 것이 그 목적이다.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from kernel import profile
from kernel.context import READ_ENC, ROOT, _rel, app_code, is_harness_own, tracked
from kernel.gates import (api_types, core, harness_self, layers, md_graph, md_style,
                          placement, schema, tests_pairing)

# (slug, 제목, 위반 목록, 건너뛴 사유). 사유가 있으면 [SKIP].
Section = tuple[str, str, list[str], "str | None"]

LOCAL_PACKAGE = "harness_gates"
BASELINE_FILE = ROOT / "harness_baseline.txt"

NO_PY = "검사할 소스 없음"
NO_UI = "프론트 소스 없음"


def _print_style_reports(reports: list[str]) -> None:
    for report in reports:
        print(f"[REPORT] {report}")


def _print_sections(sections: list[Section]) -> int:
    total = 0
    for _slug, title, violations, skipped in sections:
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


# ── 동결(baseline) ─────────────────────────────────────────────────────────────
#
# 하네스를 기존 레포에 끼운 첫 실행이 수백 건을 뱉으면 사람은 게이트를 통째로 끈다. 그게
# 하네스가 죽는 실제 경로다. 그래서 설치는 현재 위반을 (slug, 파일)로 얼리고 초록불에서
# 출발한다. 줄번호로 얼리지 않는 이유는 코드가 한 줄만 밀려도 동결이 풀리기 때문이다.


def violation_path(violation: str) -> str | None:
    """위반 문자열 앞머리의 파일 경로. 파일에 귀속되지 않는 전역 위반이면 None."""
    head = violation.split(":", 1)[0].strip()
    if not head or " " in head or ("/" not in head and "." not in head):
        return None
    return head


def load_baseline() -> set[tuple[str, str]]:
    if not BASELINE_FILE.exists():
        return set()
    frozen: set[tuple[str, str]] = set()
    for line in BASELINE_FILE.read_text(encoding=READ_ENC).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        slug, _tab, path = line.partition("\t")
        if path.strip():
            frozen.add((slug.strip(), path.strip()))
    return frozen


def _apply_baseline(sections: list[Section]) -> list[Section]:
    frozen = load_baseline()
    if not frozen:
        return sections
    kept: list[Section] = []
    for slug, title, violations, skipped in sections:
        live = [v for v in violations
                if (slug, violation_path(v) or "") not in frozen]
        kept.append((slug, title, live, skipped))
    return kept


def _under(files: list[Path], layer_name: str) -> list[Path]:
    prefix = profile.layer(layer_name)
    if not prefix:
        return []
    return [f for f in files if _rel(f).startswith(prefix)]


def _entry(slug: str, title: str, violations: list[str], ok: object, need: str) -> Section:
    """ok 가 거짓이면 [SKIP]. `위반 0건`과 `대상 0개`를 구분하는 것이 이 함수의 전부다."""
    return (slug, title, violations, None) if ok else (slug, title, [], need)


def _need_layer(name: str) -> str:
    return f"프로파일에 {name} 레이어 미선언"


def _need_symbol(name: str) -> str:
    return f"프로파일에 {name} 심볼 미선언"


def _kernel_sections(files: list[Path], ui_files: list[Path]) -> list[Section]:
    both = files + ui_files
    reads, web = _under(files, "read"), _under(files, "web")
    vocab = profile.VOCAB
    settings = profile.FILES.get("settings")

    return [
        _entry("line_limit", "파일 길이 상한", core.check_line_limit(files), files, NO_PY),
        _entry("closures", "중첩 def(클로저)", core.check_closures(files), files, NO_PY),
        _entry("reads_writes", "읽기 레이어의 쓰기 SQL·commit", core.check_reads_writes(files),
               reads, _need_layer("read")),
        _entry("abbrev_names", "축약 이름 단독 대입", core.check_abbrev_names(files),
               files and vocab["abbrev_names"], "프로파일에 금지 축약 이름 없음"),
        _entry("abbrev_prefixes", "축약 접두 식별자", core.check_abbrev_prefixes(both),
               both and vocab["abbrev_prefixes"], "프로파일에 금지 축약 접두 없음"),
        _entry("ui_jargon", "UI 라벨 금칙어", core.check_ui_jargon(ui_files),
               ui_files and vocab["ui_denylist"], "프로파일에 UI 금칙어 없음"),
        _entry("py_any", "py Any 타입힌트", core.check_py_any(files), files, NO_PY),
        _entry("type_hints", "공개 함수 타입힌트", core.check_type_hints(files), files, NO_PY),
        _entry("secrets", "시크릿 토큰 하드코딩", core.check_secrets(both), both, NO_PY),
        _entry("ts_any", "TS any 타입", core.check_ts_any(ui_files), ui_files, NO_UI),
        _entry("conn_processing", "커넥션 블록 내 가공", layers.check_connection_processing(files),
               _under(files, "db") and profile.symbol("db_accessor"), _need_symbol("db_accessor")),
        _entry("env_access", "설정 밖 환경변수 조회", layers.check_env_access(files),
               files and settings, "프로파일에 settings 파일 미선언"),
        _entry("web_async", "await 없는 async 핸들러", layers.check_web_async_no_await(files),
               web, _need_layer("web")),
        _entry("accessor_import", "커넥션 접근자 import 단일 경로",
               layers.check_accessor_import_path(files),
               (reads or _under(files, "write")) and profile.symbol("db_accessor_module"),
               _need_symbol("db_accessor_module")),
        _entry("ssl_bypass", "전역 SSL 패치 호출 위치", layers.check_ssl_bypass_location(files),
               files and profile.symbol("ssl_bypass"), _need_symbol("ssl_bypass")),
        _entry("routes_error", "라우트 에러 응답 형식", layers.check_routes_error_response(files),
               _under(files, "routes") and profile.symbol("error_response"),
               _need_symbol("error_response")),
        _entry("raw_fetch", "공용 래퍼 없는 fetch", layers.check_frontend_raw_fetch(ui_files),
               ui_files, NO_UI),
        _entry("hex_literal", "프론트 색 리터럴", layers.check_frontend_hex(ui_files),
               ui_files, NO_UI),
        _entry("responsive", "폰을 깨뜨리는 고정 폭", layers.check_frontend_responsive(ui_files),
               ui_files, NO_UI),
        _entry("browser_api", "브라우저 API 직접 호출",
               layers.check_frontend_browser_api(ui_files),
               ui_files and profile.ALLOWLIST["ui_platform"],
               "프로파일에 브라우저 API 래퍼 미선언"),
        _entry("file_placement", "앱 코드 배치",
               placement.check_file_placement(files, ui_files),
               placement.layer_prefixes(), "프로파일에 레이어가 하나도 미선언"),
        _entry("test_pairing", "수집·계산 모듈의 행동 테스트 짝",
               tests_pairing.check_module_test_pairing(files),
               profile.BEHAVIOR_TESTED_ROOTS, "프로파일에 행동 테스트 대상 루트 없음"),
        _entry("ddl_types", "DDL 저장 타입 잘림", schema.check_ddl_lossy_types(files),
               _under(files, "schema"), _need_layer("schema")),
        _entry("api_array", "API 응답 배열 필드 옵셔널",
               api_types.check_api_array_optional(ui_files),
               ui_files and api_types.baseline_ready(),
               NO_UI if not ui_files else "배열 동결 파일 미생성 — harness_install.py 가 만든다"),
    ]


def _doc_sections() -> list[Section]:
    greenfield = profile.STAGE == "greenfield"

    # 새 프로젝트는 MD 가 코드보다 먼저 나온다 — plan 문서가 아직 없는 경로를 가리키는 게 정상
    # 순서다. 그 시기에 이걸 강제하면 첫 문서부터 막힌다. 파일이 생기면 mature 에서 잡힌다.
    refs = md_graph.check_md_path_refs()
    if greenfield:
        _print_style_reports(refs)
    map_exists = (ROOT / profile.HARNESS_MAP).exists()
    lessons = profile.LESSONS_DOC

    sections: list[Section] = [
        _entry("md_path_refs", "MD 경로 참조 실존", refs, not greenfield, "greenfield — 리포트로만"),
        _entry("md_orphans", "고아 MD(허브 도달 불가)", md_graph.check_md_orphans(),
               profile.HUBS, "프로파일에 허브 목록 없음"),
        _entry("md_harness_map", "하네스 지도 대조", md_graph.check_harness_map(),
               (ROOT / ".claude").is_dir() and (map_exists or not greenfield),
               f"greenfield — {profile.HARNESS_MAP} 아직 없음"),
        _entry("agent_model", "에이전트 모델 정책", harness_self.check_agent_model_policy(),
               profile.AGENT_MODEL_POLICY, "프로파일에 에이전트 모델 정책 없음"),
        _entry("lessons_promotion", "사고 절 승격 상태", harness_self.check_lessons_promotion(),
               lessons and (ROOT / lessons).exists(),
               f"선언된 {lessons} 가 아직 없음" if lessons else "프로파일에 사고 기록 문서 미선언"),
    ]
    for pair in profile.DOC_SYNC:
        title = f"문서↔코드 대조({pair['doc']}↔{pair['code']})"
        sections.append(_entry(f"doc_sync:{pair['doc']}", title,
                               md_graph.check_doc_sync(pair),
                               md_graph.doc_sync_ready(pair), "대조할 양쪽 실물이 아직 없음"))
    return sections


def _local_sections(files: list[Path], ui_files: list[Path]) -> list[Section]:
    """프로젝트가 자기 레포에 둔 게이트. `harness_gates/<이름>.py` 가 run(py, ui) 을 노출한다."""
    sections: list[Section] = []
    for name in profile.LOCAL_GATES:
        try:
            module = importlib.import_module(f"{LOCAL_PACKAGE}.{name}")
            results = module.run(files, ui_files)
        except Exception as exc:                     # 로드 실패를 조용히 넘기면 게이트가 사라진다
            sections.append((f"local:{name}", f"프로젝트 게이트 {name}",
                             [f"로드 실패 {exc.__class__.__name__}: {exc}"], None))
            continue
        for title, violations in results:
            sections.append((f"local:{name}", title, violations, None))
    return sections


def _build_sections(
    files: list[Path], ui_files: list[Path], include_md: bool, md_files: list[Path]
) -> list[Section]:
    sections = _kernel_sections(files, ui_files)
    sections += _local_sections(files, ui_files)
    if md_files:
        hard, soft = md_style.check_md_style(md_files)
        sections.append(("md_style", "MD 작성 규칙", hard, None))
        _print_style_reports(soft)
    if include_md:
        sections += _doc_sections()
    return sections


def _in_scope(f: Path) -> bool:
    """프로파일이 통째로 뺀 경로인가. 벤더 사본·참고 자료·픽스처가 여기 해당한다."""
    exclude = profile.SCOPE["exclude_all"]
    return not (exclude and _rel(f).startswith(exclude))


def source_files() -> tuple[list[Path], list[Path]]:
    """전 게이트가 볼 (py, ui) 목록. 하네스 자기 발자국과 스코프 제외를 뺀 것이다."""
    ui = profile.layer("ui")
    files = [f for f in app_code("*.py") if _in_scope(f)]
    ui_files = [f for f in app_code("*.tsx", "*.ts", under=ui) if _in_scope(f)] if ui else []
    return files, ui_files


def collect_all_violations() -> list[tuple[str, str]]:
    """동결 대상 — 현재 전 게이트 위반의 (slug, 파일) 쌍. 설치 스크립트가 쓴다.

    baseline 을 적용하지 않은 날것이다. 파일에 귀속되지 않는 전역 위반은 얼릴 키가 없어
    빠지고, 그래서 설치 후에도 남는다 — 사람이 직접 봐야 하는 것들이다.
    """
    files, ui_files = source_files()
    sections = _build_sections(files, ui_files, True, tracked_md_files())
    pairs = {(slug, path) for slug, _title, violations, _skip in sections
             for v in violations if (path := violation_path(v))}
    return sorted(pairs)


def tracked_md_files() -> list[Path]:
    return [f for f in tracked("*.md") if _in_scope(f) and md_style.style_target(_rel(f))]


def _single_file_lists(raw_path: str) -> tuple[list[Path], list[Path], bool, list[Path]]:
    """--file 모드: 대상 파일 하나를 (py, ui, 전역검사 여부, 스타일 대상)으로 분류."""
    p = Path(raw_path).resolve()
    try:
        rel = p.relative_to(ROOT).as_posix()
    except ValueError:
        return [], [], False, []
    exclude = profile.SCOPE["exclude_all"]
    if not p.exists() or (exclude and rel.startswith(exclude)):
        return [], [], False, []
    if p.suffix in (".py", ".ts", ".tsx") and is_harness_own(rel):
        return [], [], False, []
    if p.suffix == ".py":
        return [p], [], False, []
    ui = profile.layer("ui")
    if p.suffix in (".ts", ".tsx") and ui and rel.startswith(ui):
        return [], [p], False, []
    if p.suffix == ".md":
        # 전역 교차검사는 정본 MD 편집일 때만 재실행. 스타일은 그 파일만.
        style = [p] if md_style.style_target(rel) else []
        doc_exclude = tuple(profile.MD["doc_exclude"])
        canonical = not (doc_exclude and (rel.startswith(doc_exclude) or rel in doc_exclude))
        return [], [], canonical, style
    return [], [], False, []


def main(argv: list[str]) -> int:
    # Windows cp949 콘솔에서 위반 라인(유니코드 포함) 출력 크래시 방지
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(errors="replace")
    if not profile.LOADED:
        print(f"[SETUP] {profile.PROFILE_FILE} 없음 — 프로젝트를 모르는 상태다. "
              f"레이어를 요구하는 게이트는 전부 [SKIP] 이다.")
    if len(argv) >= 2 and argv[0] == "--file":
        files, ui_files, include_md, md_files = _single_file_lists(argv[1])
        if not files and not ui_files and not include_md and not md_files:
            return 0
    else:
        files, ui_files = source_files()
        include_md, md_files = True, tracked_md_files()
    sections = _apply_baseline(_build_sections(files, ui_files, include_md, md_files))
    total = _print_sections(sections)

    if total:
        print(f"\n총 {total}건 위반.")
        return 1
    print("\n전 게이트 통과.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""kernel/gates/arch_diagram.py — 그림과 실물의 1:1 대조 (검사 48).

그림 속 상자가 코드 어디인지 증명되지 않으면 그 그림은 산문이다. 정본 JSON 의 노드 `sources`
로 실존·행 범위·커버리지·영수증·revision 을 보고, 스키마·배치·증거의 정본 판정은 엔진
validate 에 위임한다. node 가 없으면 위임분만 [TOOL] 이고 자체 판정은 그대로 돈다.

  자체 판정   external 아닌 노드마다 sources · 레이어·패키지 커버리지 · 경로·행 실존 · 영수증 해시 · revision 실존
  REPORT      revision 이후 원류가 바뀐 노드 — 재검토 신호. 오탐 여지가 있어 합산하지 않는다
  엔진 위임   validate --repo-root 의 diagnostics[] → FAIL, node 없음 → TOOL
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from kernel import diagram, profile
from kernel.context import READ_ENC, ROOT, tracked
from kernel.gates import placement

Skip = tuple[str, str]
Section = tuple[str, str, list[str], "Skip | None"]

# 코드에 대응물이 없는 노드 — 사람·외부 시스템·상태기계의 추상 상태
EXEMPT_TYPES = {"external"}
EXEMPT_KINDS = {"lifecycle"}


def diagrams() -> list[Path]:
    """추적되는 정본 전부. 영수증·HTML 은 제외."""
    return [p for p in tracked("*.json", under=diagram.DIAGRAM_DIR + "/") if diagram.kind_of(p)]


def expected_nodes() -> tuple[str, ...]:
    """디스크에 실존하는 레이어 경로와 도메인 패키지 — architecture 가 전부 그려야 하는 것."""
    layers = [p for p in placement.layer_prefixes() if (ROOT / p).exists()]
    return tuple(sorted(set(layers) | set(placement.domain_prefixes())))


def _git_ok(*args: str) -> bool:
    done = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True)
    return done.returncode == 0


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding=READ_ENC, errors="replace").splitlines())


def _source_lines(rel: str, node_id: str, sources: list[object]) -> list[str]:
    """한 노드의 sources 실존·행 범위. 반환은 위반 문장."""
    found: list[str] = []
    for item in sources:
        if not isinstance(item, dict) or not item.get("path"):
            found.append(f"{rel}: 노드 {node_id} 의 sources 항목에 path 없음")
            continue
        target = ROOT / str(item["path"])
        if not target.is_file():
            found.append(f"{rel}: 노드 {node_id} → {item['path']} 실존하지 않음 — 이름을 바꿨으면 그림도 고친다")
            continue
        line, end = item.get("line"), item.get("end_line")
        last = end or line
        if isinstance(last, int) and last > _line_count(target):
            found.append(f"{rel}: 노드 {node_id} → {item['path']} 행 {last} 없음 (파일은 {_line_count(target)}줄)")
    return found


def _stale_lines(rel: str, revision: str, node_id: str, sources: list[object]) -> list[str]:
    """revision 이후 원류가 바뀐 노드 — REPORT."""
    if not revision:
        return []
    found: list[str] = []
    for item in sources:
        path = str(item.get("path") or "") if isinstance(item, dict) else ""
        if path and not _git_ok("diff", "--quiet", revision, "HEAD", "--", path):
            found.append(f"{rel}: 노드 {node_id} 의 원류 {path} 가 revision 이후 바뀜 — 그림을 다시 본다")
    return found


def _check_one(source: Path) -> tuple[list[str], list[str]]:
    rel = source.relative_to(ROOT).as_posix()
    kind = diagram.kind_of(source) or ""
    doc = diagram.load(source)
    if not doc:
        return [f"{rel}: JSON 파싱 실패"], []
    hard: list[str] = []
    soft: list[str] = []
    repository = doc.get("meta", {}).get("repository") if isinstance(doc.get("meta"), dict) else None
    revision = str(repository.get("revision") or "") if isinstance(repository, dict) else ""
    if revision and not _git_ok("cat-file", "-e", f"{revision}^{{commit}}"):
        hard.append(f"{rel}: revision {revision[:7]} 이 이 레포에 없음 — deliver 를 다시 돌려 HEAD 로 찍는다")
        revision = ""                    # 없는 커밋과의 diff 는 전부 '바뀜' 이라 REPORT 가 소음이 된다
    covered: set[str] = set()
    for node in doc.get(diagram.NODE_KEY[kind], []) or []:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "?")
        sources = node.get("sources") or []
        if not sources:
            if kind not in EXEMPT_KINDS and node.get("type") not in EXEMPT_TYPES:
                hard.append(f"{rel}: 노드 {node_id} 에 sources 없음 — 코드 어디인지 적어야 그림이다")
            continue
        hard += _source_lines(rel, node_id, sources)
        soft += _stale_lines(rel, revision, node_id, sources)
        covered |= {str(item.get("path") or "") for item in sources
                    if isinstance(item, dict) and (ROOT / str(item.get("path") or "")).is_file()}
    if kind == "architecture":
        for prefix in expected_nodes():
            if not any(path.startswith(prefix) for path in covered):
                hard.append(f"{rel}: {prefix} 를 가리키는 노드 없음 — 레이어·도메인 패키지는 전부 그린다")
    hard += _receipt_lines(rel, source)
    return hard, soft


def _receipt_lines(rel: str, source: Path) -> list[str]:
    receipt = diagram.load(diagram.receipt_path(source)) if diagram.receipt_path(source).exists() else {}
    if not receipt:
        return [f"{rel}: 영수증 없음 — `python -X utf8 -m kernel.diagram deliver` 로 렌더한다"]
    if receipt.get("spec_sha256_lf") != diagram.spec_sha256_lf(source):
        return [f"{rel}: 영수증 해시가 현재 정본과 다름 — 정본을 고쳤으면 다시 deliver 한다"]
    if not diagram.output_path(source).exists():
        return [f"{rel}: 렌더 HTML 없음 — deliver 산출물을 커밋한다"]
    return []


def check_arch_diagram() -> tuple[list[str], list[str]]:
    """(강제 위반, REPORT). 그림이 없는 growing 이상 프로젝트는 그 자체가 위반이다."""
    found = diagrams()
    if not found:
        if expected_nodes() and profile.STAGE != "greenfield":
            return [f"{diagram.DIAGRAM_DIR}: 아키텍처 그림 없음 — 코드가 자란 프로젝트에 그림이 없는 건 손실이다. arch-diagram 스킬"], []
        return [], []
    hard: list[str] = []
    soft: list[str] = []
    for source in found:
        one_hard, one_soft = _check_one(source)
        hard += one_hard
        soft += one_soft
    return hard, soft


def engine_sections() -> list[Section]:
    """그림마다 엔진 validate 위임. node 없으면 TOOL — 통과가 아니다."""
    sections: list[Section] = []
    for source in diagrams():
        rel = source.relative_to(ROOT).as_posix()
        slug = f"arch_diagram_engine:{source.name}"
        receipt = diagram.validate(diagram.kind_of(source) or "", source)
        if receipt.get("tool_missing"):
            sections.append((slug, f"그림 엔진 진단({rel})", [],
                             ("TOOL", f"{receipt['tool_missing']} 없음 — node 를 설치하면 켜진다")))
            continue
        lines = [f"{rel}: {line}" for line in diagram.diagnostics_lines(receipt)]
        if not receipt.get("ok") and not lines:
            lines = [f"{rel}: 엔진 실패(진단 없음)"]
        sections.append((slug, f"그림 엔진 진단({rel})", lines, None))
    return sections

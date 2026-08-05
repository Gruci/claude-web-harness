"""kernel/gates/md_graph.py — 문서와 실물의 대조 게이트.

MD 는 읽을거리가 아니라 다음 세션의 행동을 정하는 규칙이다. 그래서 코드와 같은 기준으로 검사한다.

  경로 참조 실존   MD 안 백틱 경로가 레포에 있는가. 삭제·리네임 후 남은 stale 참조를 잡는다
  문서↔코드 대조   같은 값이 문서와 코드 양쪽에 적힌 곳. 한쪽만 고치면 잡힌다
  고아 MD          허브에서 링크를 타고 도달 가능한가. 도달 불가 = 읽힐 타이밍이 없는 문서
  하네스 지도      훅·에이전트·스킬 실물이 지도에 등재됐는가

허브 목록도 대조 쌍도 프로파일이 정한다. 선언이 없으면 러너가 [SKIP] 으로 찍는다.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from kernel import profile
from kernel.context import ROOT, _ls_files, _rel

MD_REF_ALLOWLIST_FILE = "md_ref_allowlist.txt"

_BACKTICK = re.compile(r"`([^`\n]+)`")
_PATH_TOKEN = re.compile(r"[\w][\w./-]*\.(?:py|tsx|ts|css|md|mjs|json)\b")
_MD_LINK = re.compile(r"\]\(([^)\s]+\.md)[^)]*\)")
_DOMAIN_MD = re.compile(r"^([a-z][a-z0-9_]*)/([A-Z][A-Z0-9_]*)\.md$")
_HOOK_CMD = re.compile(r"[\w./-]+\.(?:py|mjs|md)")


def _doc_md_files() -> list[Path]:
    """정본 MD — 작업 산출물·벤더 사본·동적 파일은 뺀다."""
    exclude = tuple(profile.MD["doc_exclude"])
    files: list[Path] = []
    for rel in _ls_files("*.md"):
        if not (ROOT / rel).exists() or "node_modules" in rel:
            continue
        if exclude and (rel.startswith(exclude) or rel in exclude):
            continue
        files.append(ROOT / rel)
    return files


def _load_ref_allowlist() -> set[str]:
    f = ROOT / MD_REF_ALLOWLIST_FILE
    if not f.exists():
        return set()
    allow: set[str] = set()
    for line in f.read_text(encoding="utf-8").splitlines():
        token = line.split("#", 1)[0].strip()
        if token:
            allow.add(token)
    return allow


_TRACKED: set[str] | None = None


def _tracked_set() -> set[str]:
    global _TRACKED
    if _TRACKED is None:
        _TRACKED = set(_ls_files())
    return _TRACKED


def _ref_exists(token: str, md_dir: Path) -> bool:
    """MD 는 bare 파일명·패키지 상대 경로를 섞어 쓰므로 base 해석과 접미 매칭을 병행한다.
    어디에도 없는 파일명(리네임·삭제된 stale 참조)만 미존재로 본다 — 게이트의 실목표."""
    candidates = (token, "." + token)   # leading dot 은 백틱 파싱에서 탈락한다
    bases = [ROOT, md_dir]
    ui = profile.layer("ui")
    if ui:
        bases.append(ROOT / ui)
    for base in bases:
        for cand in candidates:
            if (base / cand).exists():
                return True
    for tracked in _tracked_set():
        for cand in candidates:
            if tracked == cand or tracked.endswith("/" + cand):
                return True
    return False


def check_md_path_refs() -> list[str]:
    allow = _load_ref_allowlist()
    skip_prefix = tuple(profile.MD["ref_exclude"])
    bad: list[str] = []
    for md in _doc_md_files():
        rel_md = _rel(md)
        for i, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            for backtick in _BACKTICK.findall(line):
                for m in _PATH_TOKEN.finditer(backtick):
                    token = m.group(0)
                    if "*" in token or "/." in token or "//" in token or token in allow:
                        continue
                    if skip_prefix and token.startswith(skip_prefix):
                        continue
                    if not _ref_exists(token, md.parent):
                        bad.append(f"{rel_md}:{i}: 실존하지 않는 경로 참조 `{token}`")
    return bad


# ── 문서 ↔ 코드 대조 ───────────────────────────────────────────────────────────


def _top_level_ints(code: Path) -> dict[str, int]:
    consts: dict[str, int] = {}
    tree = ast.parse(code.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, int):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    consts[target.id] = node.value.value
    return consts


def _getenv_keys(code: Path) -> set[str]:
    keys: set[str] = set()
    tree = ast.parse(code.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "getenv" and node.args \
                and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            keys.add(node.args[0].value)
    return keys


_CONST_REF = re.compile(r"\(([A-Z][A-Z0-9_]*)\b")
_NUMBER = re.compile(r"\d+")
_UPPER_TOKEN = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\b")


def _sync_int_consts(doc: Path, code: Path, marker: str) -> list[str]:
    """문서 표가 참조한 상수의 값이 그 줄의 숫자와 맞는지."""
    consts = _top_level_ints(code)
    rel_doc = _rel(doc)
    bad: list[str] = []
    for i, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
        names = [n for n in _CONST_REF.findall(line) if marker in n]
        if not names:
            continue
        numbers = {int(n) for n in _NUMBER.findall(line)}
        for name in names:
            if name not in consts:
                bad.append(f"{rel_doc}:{i}: 문서가 참조한 {name} 가 {_rel(code)} 에 없음")
            elif numbers and consts[name] not in numbers:
                bad.append(f"{rel_doc}:{i}: {name}={consts[name]} 인데 문서 값 {sorted(numbers)} 불일치")
    return bad


def _sync_env_keys(doc: Path, code: Path, section: str, allow: tuple[str, ...]) -> list[str]:
    """코드가 읽는 환경변수 키와 문서 목록의 양방향 diff."""
    code_keys = _getenv_keys(code)
    doc_keys: set[str] = set()
    in_block = False
    for line in doc.read_text(encoding="utf-8").splitlines():
        if line.strip() == section:
            in_block = True
            continue
        if in_block:
            if line.strip().startswith("## "):
                break
            doc_keys.update(_UPPER_TOKEN.findall(line.split("#", 1)[0]))
    bad = [f"{_rel(code)} 가 읽는 '{k}' 가 {_rel(doc)} 목록에 없음"
           for k in sorted(code_keys - doc_keys)]
    bad += [f"{_rel(doc)} 의 '{k}' 를 {_rel(code)} 가 읽지 않음(타 모듈 로드 가능 — 확인)"
            for k in sorted(doc_keys - code_keys - set(allow))]
    return bad


def check_doc_sync(entry: dict[str, object]) -> list[str]:
    """프로파일 DOC_SYNC 한 쌍을 판정한다. 문서나 코드가 없으면 대조할 것이 없다."""
    doc = ROOT / str(entry["doc"])
    code = ROOT / str(entry["code"])
    if not doc.exists() or not code.exists():
        return []
    kind = entry.get("kind")
    if kind == "int_consts":
        return _sync_int_consts(doc, code, str(entry.get("marker", "")))
    if kind == "env_keys":
        return _sync_env_keys(doc, code, str(entry.get("section", "")),
                              tuple(entry.get("allow", ())))   # type: ignore[arg-type]
    return [f"{_rel(doc)}: 알 수 없는 대조 종류 '{kind}' — 프로파일 DOC_SYNC 확인"]


# ── 고아 MD ────────────────────────────────────────────────────────────────────


def _is_domain_md(rel: str) -> bool:
    """`macro/MACRO.md` 처럼 패키지명과 파일명이 같은 정본 — 총칭 라우팅으로 도달 인정."""
    m = _DOMAIN_MD.match(rel)
    return bool(m) and m.group(1).upper().replace("-", "_") == m.group(2)


def _outlinks(md_path: Path, known: set[str]) -> set[str]:
    text = md_path.read_text(encoding="utf-8")
    tokens: set[str] = set()
    for backtick in _BACKTICK.findall(text):
        tokens.update(t for t in _PATH_TOKEN.findall(backtick) if t.endswith(".md"))
    tokens.update(_MD_LINK.findall(text))
    found: set[str] = set()
    for token in tokens:
        name = token.lstrip("./")
        for candidate in known:
            if candidate == name or candidate.endswith("/" + name):
                found.add(candidate)
    return found


def check_md_orphans() -> list[str]:
    """허브에서 참조 그래프로 도달 불가한 정본 MD — 읽힐 타이밍이 없는 문서."""
    if not profile.HUBS:
        return []
    files = _doc_md_files()
    known = {_rel(f) for f in files}
    by_rel = {_rel(f): f for f in files}
    reachable = {s for s in profile.HUBS if s in known}
    if profile.HUB_DOMAIN_MD_IMPLICIT:
        reachable |= {r for r in known if _is_domain_md(r)}
    frontier = list(reachable)
    while frontier:
        current = frontier.pop()
        for target in _outlinks(by_rel[current], known):
            if target not in reachable:
                reachable.add(target)
                frontier.append(target)
    return [f"{rel}: 고아 — 허브에서 도달 불가. 라우팅표에 등재하거나 폐기하라"
            for rel in sorted(known - reachable)]


# ── 하네스 지도 ────────────────────────────────────────────────────────────────


def _harness_actuals() -> dict[str, set[str]]:
    actual: dict[str, set[str]] = {"훅": set(), "에이전트": set(), "스킬": set()}
    settings = ROOT / ".claude" / "settings.json"
    if settings.exists():
        raw = json.loads(settings.read_text(encoding="utf-8"))
        for entries in (raw.get("hooks") or {}).values():
            for entry in entries:
                for hook in entry.get("hooks") or []:
                    for token in _HOOK_CMD.findall(hook.get("command") or ""):
                        actual["훅"].add(Path(token).name)
    agents = ROOT / ".claude" / "agents"
    if agents.is_dir():
        actual["에이전트"] = {p.stem for p in agents.glob("*.md")}
    skills = ROOT / ".claude" / "skills"
    if skills.is_dir():
        actual["스킬"] = {p.parent.name for p in skills.glob("*/SKILL.md")}
    return actual


def check_harness_map() -> list[str]:
    """실물(훅·에이전트·스킬)이 지도에 빠짐없이 등재됐는가.

    단방향이다 — 지도에만 남은 유령 항목은 잡히지 않는다. 이름의 존재만 보고 서술 내용은
    검사하지 않는다. 그쪽은 사람이 하는 주기 감사의 몫이다.
    """
    actuals = _harness_actuals()
    if not any(actuals.values()):
        return []
    doc = ROOT / profile.HARNESS_MAP
    if not doc.exists():
        return [f"{profile.HARNESS_MAP} 없음 — 하네스 지도가 정본이다"]
    text = doc.read_text(encoding="utf-8")
    return [f"{profile.HARNESS_MAP}: {kind} '{name}' 이 지도에 없음 — 같은 턴에 등재하라"
            for kind, names in actuals.items() for name in sorted(names) if name not in text]

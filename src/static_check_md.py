"""static_check_md.py — P7 게이트 ④ (MD 참조 실존·배치 스케줄·.env 키·고아·하네스 지도 대조).

전부 활성 강제 게이트다(2026-07-17 활성 전환 — 위반 시 static_check 가 exit 1).
static_check_gates.py 가 400줄을 넘지 않도록 ④ 로직만 분리한 파일이다.

  ④A MD 경로 참조 실존 — 정본 MD 백틱 경로가 레포에 존재하는지 (md_ref_allowlist.txt 예외)
  ④B 배치 스케줄     — DEVGUIDE 배치표 *_HOUR 시각 vs batch_runner.py 상수값
  ④C .env 키         — DEVGUIDE .env 목록 vs settings.py os.getenv 키 양방향 diff
  ④D 고아 MD         — 허브에서 참조 그래프로 도달 불가한 정본 MD (dev/MD_STANDARD.md ② 연결성)
  ④E 하네스 지도     — 실물(settings.json 훅·에이전트·스킬) → HARNESS.md 단방향. 유령 항목은 /md-audit 몫
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from static_check_gates import ROOT, _rel

_MD_PATH_RE = re.compile(r"`([^`\n]+)`")
_PATH_TOKEN_RE = re.compile(r"[\w][\w./-]*\.(?:py|tsx|ts|css|md)\b")
MD_REF_ALLOWLIST_FILE = "md_ref_allowlist.txt"


def _canonical_md_files() -> list[Path]:
    import subprocess
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True)
    files: list[Path] = []
    for line in out.stdout.splitlines():
        rel = line.strip()
        if not rel or not (ROOT / rel).exists():
            continue
        if rel.startswith(("docs/", ".claude/")) or "node_modules" in rel:
            continue
        if "/prompts/" in rel or rel == "EDITING.md":
            continue
        files.append(ROOT / rel)
    return files


def _load_md_ref_allowlist() -> set[str]:
    f = ROOT / MD_REF_ALLOWLIST_FILE
    if not f.exists():
        return set()
    allow: set[str] = set()
    for line in f.read_text(encoding="utf-8").splitlines():
        s = line.split("#", 1)[0].strip()
        if s:
            allow.add(s)
    return allow


_TRACKED_CACHE: set[str] | None = None


def _tracked_set() -> set[str]:
    global _TRACKED_CACHE
    if _TRACKED_CACHE is None:
        import subprocess
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
        _TRACKED_CACHE = set(out.stdout.splitlines())
    return _TRACKED_CACHE


def _ref_exists(token: str, md_dir: Path) -> bool:
    """MD 경로 참조 실존 판정. MD 는 bare 파일명(트리 다이어그램)·frontend/src 상대·패키지
    상대 경로를 섞어 쓰므로, base 해석 + 전체 tracked 파일에 대한 suffix 매칭을 병행한다.
    어디에도 없는 파일명(리네임/삭제된 stale 참조)만 미존재로 판정 — 게이트의 실목표."""
    # leading dot 은 백틱 파싱에서 탈락하므로 '.'+token 도 후보(.claude/... 등)
    candidates = (token, "." + token)
    for base in (ROOT, ROOT / "frontend" / "src", md_dir):
        for cand in candidates:
            if (base / cand).exists():
                return True
    for p in _tracked_set():
        for cand in candidates:
            if p == cand or p.endswith("/" + cand):
                return True
    return False


def check_md_path_refs() -> list[str]:
    allow = _load_md_ref_allowlist()
    bad: list[str] = []
    for md in _canonical_md_files():
        rel_md = _rel(md)
        text = md.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            for backtick in _MD_PATH_RE.findall(line):
                for m in _PATH_TOKEN_RE.finditer(backtick):
                    token = m.group(0)
                    if "*" in token or "/." in token or "//" in token or token in allow:
                        continue
                    # 스코프 밖 트리(아카이브·외부 아이디어·메모리)는 의도적 참조 — 제외
                    if token.startswith(("docs/", "idea/", "memory/")):
                        continue
                    if not _ref_exists(token, md.parent):
                        bad.append(f"{rel_md}:{i}: 실존하지 않는 경로 참조 `{token}`")
    return bad


def check_batch_schedule() -> list[str]:
    """DEVGUIDE 배치 스케줄 표의 *_HOUR 상수 시각 vs batch_runner.py 상수값 대조 (import 금지·ast)."""
    runner = ROOT / "batch_runner.py"
    devguide = ROOT / "DEVGUIDE.md"
    if not runner.exists() or not devguide.exists():
        return []
    consts: dict[str, int] = {}
    tree = ast.parse(runner.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, int):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    consts[tgt.id] = node.value.value
    bad: list[str] = []
    hour_ref = re.compile(r"\(([A-Z][A-Z0-9_]*_HOUR)\b")
    time_ref = re.compile(r"(\d{1,2}):00")
    for i, line in enumerate(devguide.read_text(encoding="utf-8").splitlines(), 1):
        names = hour_ref.findall(line)
        if not names:
            continue
        times = {int(h) for h in time_ref.findall(line)}
        for name in names:
            if name not in consts:
                bad.append(f"DEVGUIDE.md:{i}: 배치표가 참조한 {name} 가 batch_runner.py 에 없음")
            elif times and consts[name] not in times:
                bad.append(f"DEVGUIDE.md:{i}: {name}={consts[name]} 인데 배치표 시각 {sorted(times)} 불일치")
    return bad


def check_env_keys() -> list[str]:
    """DEVGUIDE .env 키 목록 vs settings.py 로드 키 대조 (양방향 diff — 리포트용)."""
    settings = ROOT / "settings.py"
    devguide = ROOT / "DEVGUIDE.md"
    if not settings.exists() or not devguide.exists():
        return []
    settings_keys: set[str] = set()
    tree = ast.parse(settings.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "getenv" and node.args \
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            settings_keys.add(node.args[0].value)
    # DEVGUIDE .env 블록 파싱
    devtext = devguide.read_text(encoding="utf-8").splitlines()
    in_block = False
    dev_keys: set[str] = set()
    key_re = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\b")
    for line in devtext:
        if line.strip() == "## .env 키 목록":
            in_block = True
            continue
        if in_block:
            if line.strip().startswith("## "):
                break
            code = line.split("#", 1)[0]
            for m in key_re.findall(code):
                if m not in ("KST", "TTL", "HMAC", "API", "DM", "PW", "ID", "URL"):
                    dev_keys.add(m)
    # settings.py 를 거치지 않고 외부 라이브러리가 .env 를 직접 읽는 실키 (문서엔 있어야 함)
    env_doc_allowlist = {"KRX_ID", "KRX_PW"}   # pykrx 가 KRX 로그인 시 직접 로드
    bad: list[str] = []
    for k in sorted(settings_keys - dev_keys):
        bad.append(f"settings.py 로드 키 '{k}' 가 DEVGUIDE .env 목록에 없음")
    for k in sorted(dev_keys - settings_keys - env_doc_allowlist):
        bad.append(f"DEVGUIDE .env 키 '{k}' 가 settings.py 에 없음(타 모듈 로드 가능 — 확인)")
    return bad


# ─── ④D 고아 MD ────────────────────────────────────────────────────────────────

ORPHAN_SEEDS = ("CLAUDE.md", "AGENTS.md", "DEVGUIDE.md", "DESIGN_GUIDE.md",
                "README.md", "HARNESS.md")
_DOMAIN_MD_RE = re.compile(r"^([a-z][a-z0-9_]*)/([A-Z][A-Z0-9_]*)\.md$")
_MD_LINK_RE = re.compile(r"\]\(([^)\s]+\.md)[^)]*\)")


def _is_domain_md(rel: str) -> bool:
    """`macro/MACRO.md` 처럼 패키지명과 파일명이 같은 도메인 정본 — 총칭 라우팅으로 도달 인정."""
    m = _DOMAIN_MD_RE.match(rel)
    return bool(m) and m.group(1).upper().replace("-", "_") == m.group(2)


def _md_outlinks(md_path: Path, known: set[str]) -> set[str]:
    """이 MD 가 참조하는 다른 MD 의 rel 경로 집합 (백틱 경로 + 마크다운 링크)."""
    text = md_path.read_text(encoding="utf-8")
    tokens: set[str] = set()
    for backtick in _MD_PATH_RE.findall(text):
        tokens.update(t for t in _PATH_TOKEN_RE.findall(backtick) if t.endswith(".md"))
    tokens.update(_MD_LINK_RE.findall(text))
    found: set[str] = set()
    for token in tokens:
        name = token.lstrip("./")
        for candidate in known:
            if candidate == name or candidate.endswith("/" + name):
                found.add(candidate)
    return found


def check_md_orphans() -> list[str]:
    """허브 시드에서 참조 그래프로 도달 불가한 정본 MD — 읽힐 타이밍이 없는 문서.

    Codex 전용 트리(.codex/·.agents/)는 제외 — 진입점이 AGENTS.md 쪽이라 이 그래프의 대상이 아니다.
    """
    files = [f for f in _canonical_md_files()
             if not _rel(f).startswith((".codex/", ".agents/"))]
    known = {_rel(f) for f in files}
    by_rel = {_rel(f): f for f in files}
    reachable = {s for s in ORPHAN_SEEDS if s in known}
    reachable |= {r for r in known if _is_domain_md(r)}
    frontier = list(reachable)
    while frontier:
        current = frontier.pop()
        for target in _md_outlinks(by_rel[current], known):
            if target not in reachable:
                reachable.add(target)
                frontier.append(target)
    return [f"{rel}: ④D 고아 — 허브에서 도달 불가. 라우팅표에 등재하거나 폐기하라"
            for rel in sorted(known - reachable)]


# ─── ④E 하네스 지도 대조 ───────────────────────────────────────────────────────

HARNESS_MAP_FILE = "HARNESS.md"
_HOOK_CMD_RE = re.compile(r"[\w./-]+\.(?:py|mjs|md)")


def _harness_actuals() -> dict[str, set[str]]:
    """하네스 실물 — 훅 스크립트·에이전트명·스킬명."""
    import json
    actual: dict[str, set[str]] = {"훅": set(), "에이전트": set(), "스킬": set()}
    settings = ROOT / ".claude" / "settings.json"
    if settings.exists():
        raw = json.loads(settings.read_text(encoding="utf-8"))
        for entries in (raw.get("hooks") or {}).values():
            for entry in entries:
                for hook in entry.get("hooks") or []:
                    for token in _HOOK_CMD_RE.findall(hook.get("command") or ""):
                        actual["훅"].add(Path(token).name)
    agents_dir = ROOT / ".claude" / "agents"
    if agents_dir.is_dir():
        actual["에이전트"] = {p.stem for p in agents_dir.glob("*.md")}
    skills_dir = ROOT / ".claude" / "skills"
    if skills_dir.is_dir():
        actual["스킬"] = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    return actual


def check_harness_map() -> list[str]:
    """HARNESS.md 가 하네스 실물을 빠짐없이 담고 있는지 (④B 대조 패턴과 동일)."""
    doc = ROOT / HARNESS_MAP_FILE
    if not doc.exists():
        return [f"{HARNESS_MAP_FILE} 없음 — 하네스 지도가 정본이다(CLAUDE.md 하네스 등록)"]
    text = doc.read_text(encoding="utf-8")
    bad: list[str] = []
    for kind, names in _harness_actuals().items():
        for name in sorted(names):
            if name not in text:
                bad.append(f"{HARNESS_MAP_FILE}: {kind} '{name}' 이 지도에 없음 — 같은 턴에 등재하라")
    return bad

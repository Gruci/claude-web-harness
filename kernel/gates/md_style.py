"""static_check_md_style.py — 게이트 ⑬ MD 작성 규칙 (dev/MD_STANDARD.md 의 기계 검사 가능 부분).

의미 단위 판정 자체는 자동화 불가 — 여기는 '의미 뭉개짐의 구조적 신호'만 검출한다.
길이는 규칙이 아니다(의미가 하나면 길어도 된다). 규칙은 "한 줄에 독립 사실이 여럿인가"다.

  강제  ⑬a 코드펜스 트리 덤프 / ⑬b 나열 뭉개기 / ⑬c 괄호 중첩 / ⑬d 머리 역할 계약 누락
  리포트 ⑬e 날짜 태그 밀도 / ⑬f 경로 토큰 밀도 / ⑬g 시그니처 밀도  (성분 A·B·D 재유입 신호)

소급 유예: static_check_md_baseline.txt 등재 파일은 강제→리포트 강등. 감소만 허용(래칫).

⑬b 판정 근거: 구분자 개수만 세면 `db/`·`kofia/`·`etf/` 같은 정상 나열(코드명 12개 = 한 의미)이
걸린다. 그래서 인라인 코드를 걷어낸 뒤 남는 '산문 조각'만 센다 — 구분자 사이에 설명이 붙어야
독립 사실이 여럿이라는 뜻이다.
"""
from __future__ import annotations

import re
from pathlib import Path

from kernel.context import ROOT, _rel

BASELINE_FILE = "static_check_md_baseline.txt"
EXCLUDE_PREFIXES = ("docs/", ".agents/", ".codex/", ".claude/skills/impeccable/")
EXCLUDE_FILES = {"EDITING.md"}
DATE_EXEMPT = {"dev/LESSONS.md"}

MAX_PROSE_ITEMS = 6        # ⑬b 한 줄 안 '설명 붙은 나열' 조각 수
MIN_ITEM_CHARS = 15        # 조각이 이 길이 이상이면 산문으로 본다
MAX_PAREN_DEPTH = 2        # ⑬c 3중부터 위반
FENCE_MIN_LINES = 5        # ⑬a 펜스 최소 줄수
TREE_RATIO = 0.5           # ⑬a 트리 토큰 줄 비율
CONTRACT_HEAD_LINES = 12   # ⑬d 역할 계약을 찾는 머리 구간 (frontmatter 제외 후)
MAX_DATES = 6              # ⑬e
MAX_PATH_TOKENS = 5        # ⑬f
MAX_SIGNATURES = 4         # ⑬g

SEPARATOR = "·"
TREE_TOKEN = re.compile(r"[├└│]|^\s{2,}[\w.<-]+/")
DATE_TAG = re.compile(r"\b20\d\d-\d\d-\d\d\b")
PATH_TOKEN = re.compile(r"[\w][\w./-]*\.(?:py|tsx|ts|css|md|mjs|json|html)\b")
SIG_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\(")   # 한글 단어+괄호가 아니라 코드 식별자만
INLINE_CODE = re.compile(r"`[^`]*`")
ROLE_CONTRACT = re.compile(r"^>\s*담는 것:.*담지 않는 것:.*읽는 시점:", re.DOTALL)


def style_target(rel: str) -> bool:
    """게이트 ⑬ 검사 대상 여부. 벤더·Codex 전용·작업 산출물·동적 파일은 제외."""
    return (rel.endswith(".md")
            and rel not in EXCLUDE_FILES
            and not rel.startswith(EXCLUDE_PREFIXES)
            and "/prompts/" not in rel)


def _load_baseline() -> set[str]:
    path = ROOT / BASELINE_FILE
    if not path.exists():
        return set()
    entries: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        token = raw.split("#", 1)[0].strip()
        if token:
            entries.add(token)
    return entries


def _paren_depth(line: str) -> int:
    depth = deepest = 0
    for char in line:
        if char == "(":
            depth += 1
            deepest = max(deepest, depth)
        elif char == ")":
            depth = max(0, depth - 1)
    return deepest


def _prose_items(line: str) -> int:
    """구분자로 갈린 조각 중 '설명이 붙은' 것의 개수. 코드명만 나열한 줄은 0에 가깝다."""
    if SEPARATOR not in line:
        return 0
    return sum(1 for part in line.split(SEPARATOR) if len(part.strip()) >= MIN_ITEM_CHARS)


def _fence_is_tree(block: list[str]) -> bool:
    if len(block) < FENCE_MIN_LINES:
        return False
    tree_lines = sum(1 for line in block if TREE_TOKEN.search(line))
    return tree_lines >= len(block) * TREE_RATIO


def _body_after_frontmatter(lines: list[str]) -> list[str]:
    """YAML frontmatter(`---` 블록)를 걷어낸 본문. 에이전트·스킬 MD 가 frontmatter 를 쓴다."""
    if not lines or lines[0].strip() != "---":
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[index + 1:]
    return lines


def _has_role_contract(lines: list[str]) -> bool:
    """머리에 역할 계약 인용구가 있는가. 제목 형식이 파일마다 달라 머리 구간을 창으로 본다."""
    head = _body_after_frontmatter(lines)[:CONTRACT_HEAD_LINES]
    quote = [line.lstrip()[1:].strip() for line in head if line.lstrip().startswith(">")]
    return bool(quote) and bool(ROLE_CONTRACT.match("> " + " ".join(quote)))


def _scan_lines(rel: str, lines: list[str], hard: list[str], soft: list[str]) -> None:
    in_fence = False
    block: list[str] = []
    fence_start = 0
    dates = 0
    for number, raw in enumerate(lines, 1):
        if raw.lstrip().startswith("```"):
            if in_fence and _fence_is_tree(block):
                hard.append(f"{rel}:{fence_start}: ⑬a 코드펜스 트리 덤프 — 파일 목록의 정본은 Glob")
            in_fence = not in_fence
            block = []
            fence_start = number
            continue
        if in_fence:
            block.append(raw)
            continue

        dates += len(DATE_TAG.findall(raw))
        prose = INLINE_CODE.sub("", raw)
        items = _prose_items(prose)
        if items > MAX_PROSE_ITEMS:
            hard.append(f"{rel}:{number}: ⑬b 한 줄에 설명 붙은 나열 {items}개 — 표나 불릿으로 쪼개라")
        depth = _paren_depth(prose)
        if depth > MAX_PAREN_DEPTH:
            hard.append(f"{rel}:{number}: ⑬c 괄호 {depth}중 중첩 — 문장을 다시 써라")
        paths = len(PATH_TOKEN.findall(raw))
        if paths >= MAX_PATH_TOKENS:
            soft.append(f"{rel}:{number}: ⑬f 경로 토큰 {paths}개 — 성분 A·C 재유입 신호")
        if len(SIG_TOKEN.findall(prose)) >= MAX_SIGNATURES:
            soft.append(f"{rel}:{number}: ⑬g 시그니처 패턴 다수 — 성분 B 재유입 신호")

    if rel not in DATE_EXEMPT and dates >= MAX_DATES:
        soft.append(f"{rel}: ⑬e 날짜 태그 {dates}개 — 성분 D 의심(경위는 dev/LESSONS.md 로)")


def check_md_style(files: list[Path]) -> tuple[list[str], list[str]]:
    """반환 (강제 위반, 리포트). baseline 등재 파일의 강제 위반은 리포트로 강등한다."""
    baseline = _load_baseline()
    hard: list[str] = []
    soft: list[str] = []
    for path in files:
        rel = _rel(path)
        if not style_target(rel):
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        found: list[str] = []
        _scan_lines(rel, lines, found, soft)
        if not _has_role_contract(lines):
            found.append(f"{rel}:1: ⑬d 머리 역할 계약 누락 — "
                         f"`> 담는 것: … 담지 않는 것: … 읽는 시점: …`")
        if rel in baseline:
            soft.extend(found)
        else:
            hard.extend(found)
    return hard, soft

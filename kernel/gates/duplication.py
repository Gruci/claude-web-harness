"""kernel/gates/duplication.py — 정본을 다시 짠 것을 사고 나기 전에 찾는다 (래칫).

다른 게이트는 전부 **사고가 난 뒤에** 생겼다. 누가 눈치채야 규칙이 하나 늘었다는 뜻이고,
그래서 하네스가 강제는 해도 발견은 사람에게 맡겨 왔다. 이 게이트는 그 앞단이라 어느 정본을
우회했는지 모르는 채로 **"같은 것이 두 곳에 있다"만** 본다.

  선언 중복   함수·컴포넌트 선언의 **본문 전체**가 같다. 이름은 보지 않는다
  블록 중복   선언 안쪽 덩어리가 연속 여러 줄 같다. 함수로 안 뽑힌 복붙이 대상이다

이름을 안 보는 것이 핵심이다. `signedWon` 과 `wonSigned` 처럼 이름만 갈린 재구현은 이름으로는
영영 안 잡히고, 본문이 통째로 같은 것은 우연이 아니다.

## baseline 키가 내용 해시가 아니라 파일 목록인 이유

내용 해시를 키로 쓰면 한 줄만 고쳐도 키가 빗나가 **래칫이 조용히 풀린다.** 동결해둔 항목이
슬그머니 새 위반으로 바뀌거나, 반대로 고쳤는데도 동결이 남는다. 파일 집합은 그 사이 편집에
안 흔들린다 — 나머지 baseline 이 (slug, 파일) 쌍인 것과 같은 이유다.

## 전량 모드 전용

파일 간 교차 비교라 대상이 전량일 때만 성립한다. 작성 시점 `--file` 은 파일 하나뿐이라
비교할 상대가 없고, 편집 한 번에 레포 전체를 다시 읽으면 훅이 느려져 사람이 훅을 끈다.
"""

from __future__ import annotations

import ast
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from kernel import profile
from kernel.context import READ_ENC, ROOT, _rel

DECL_BASELINE_FILE = "dup_decl_baseline.txt"
BLOCK_BASELINE_FILE = "dup_block_baseline.txt"

MIN_DECL_STATEMENTS = 3   # 본문 3문장 미만은 위임 한 줄짜리 — 같아도 중복이 아니다
MIN_DECL_UI_LINES = 3     # 화면 소스 본문 유효 3줄. 같은 이유
BLOCK_WINDOW = 8          # 블록 중복의 연속 일치 줄 수
MIN_BLOCK_DISTINCT = 4    # 같은 줄 반복(닫는 태그 나열)은 정보가 없다
MIN_BLOCK_CHARS = 96      # 토큰 몇 개짜리 짧은 줄만 모인 창 제외

_PY_COMMENT = ("#",)
_UI_COMMENT = ("//", "*", "/*", "{/*")
_WS = re.compile(r"\s+")
# `function X(...)` 와 `const X = (...) =>` 두 형태. 화살표는 인자 괄호가 있는 것만 본다 —
# `const x = v => ...` 는 본문이 식이라 선언 단위 비교 대상이 아니다.
_UI_DECL = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:function\s+(\w+)"
    r"|const\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]*)?=>)")
# 문자열·템플릿 리터럴 안의 중괄호로 짝이 어긋난 경우의 폭주 방지.
_UI_SCAN_LIMIT = 400


@dataclass(frozen=True)
class _Decl:
    """한 선언의 위치와 본문 지문. `digest` 가 같으면 같은 구현이다."""

    rel: str
    line: int
    end_line: int
    name: str
    digest: str


def _norm(line: str, marks: tuple[str, ...]) -> str | None:
    """공백을 접은 코드 줄. 빈 줄·주석 줄은 None (창이 주석을 건너뛰지 않게 경계로 쓴다)."""
    stripped = line.strip()
    if not stripped or stripped.startswith(marks):
        return None
    return _WS.sub(" ", stripped)


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    first = node.body[0] if node.body else None
    return (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str))


def _py_decls(text: str, rel: str) -> list[_Decl]:
    """함수 선언. 이름과 독스트링을 뺀 본문 AST 덤프가 지문이라 이름만 갈린 재구현도 같게 본다."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    found: list[_Decl] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body[1:] if _has_docstring(node) else node.body
        if len(body) < MIN_DECL_STATEMENTS:
            continue
        digest = ast.dump(ast.Module(body=body, type_ignores=[]))
        found.append(_Decl(rel, node.lineno, node.end_lineno or node.lineno, node.name, digest))
    return found


def _brace_end(lines: list[str], start: int) -> int | None:
    """선언 여는 중괄호의 짝이 닫히는 줄 인덱스. 상한 안에 못 닫으면 None."""
    depth = 0
    opened = False
    for index in range(start, min(len(lines), start + _UI_SCAN_LIMIT)):
        for char in lines[index]:
            if char == "{":
                depth += 1
                opened = True
            elif char == "}":
                depth -= 1
        if opened and depth <= 0:
            return index
    return None


def _ui_decls(text: str, rel: str) -> list[_Decl]:
    """화면 소스 선언. 중괄호 짝이 어긋나도 두 파일이 같은 본문을 내놓으면 원문이 같다는
    뜻이라 발견은 성립한다 — 경계가 틀릴 뿐 '중복이 있다'는 판정은 뒤집히지 않는다."""
    lines = text.split("\n")
    found: list[_Decl] = []
    for index, line in enumerate(lines):
        matched = _UI_DECL.match(line)
        if not matched:
            continue
        end = _brace_end(lines, index)
        if end is None:
            continue
        body = [n for n in (_norm(raw, _UI_COMMENT) for raw in lines[index + 1:end]) if n]
        if len(body) < MIN_DECL_UI_LINES:
            continue
        name = matched.group(1) or matched.group(2)
        found.append(_Decl(rel, index + 1, end + 1, name, "\n".join(body)))
    return found


def _cluster(decls: list[_Decl]) -> list[list[_Decl]]:
    """지문이 같고 **서로 다른 파일**에 걸친 묶음만. 한 파일 안 반복은 지역 문제라 뺀다."""
    buckets: dict[str, list[_Decl]] = defaultdict(list)
    for decl in decls:
        buckets[hashlib.md5(decl.digest.encode("utf-8")).hexdigest()].append(decl)
    return [group for group in buckets.values() if len({d.rel for d in group}) >= 2]


def _key(rels: list[str]) -> str:
    return ",".join(sorted(set(rels)))


def _collapse(groups: list[list[_Decl]]) -> list[list[_Decl]]:
    """파일집합 키가 같은 묶음을 하나로 합친다.

    키가 baseline 단위라 나눠 두면 한 항목이 여러 번 뜬다 — 창이 한 줄씩 밀며 겹칠 때 같은
    복붙이 조각마다 잡히고, 같은 두 파일이 공유하는 다른 선언도 같은 키다.
    """
    merged: dict[str, list[_Decl]] = defaultdict(list)
    for group in groups:
        merged[_key([d.rel for d in group])] += group
    return sorted((sorted(g, key=lambda d: (d.rel, d.line)) for g in merged.values()),
                  key=lambda g: (-len({d.rel for d in g}), g[0].rel, g[0].line))


def _positions(group: list[_Decl]) -> str:
    """파일당 첫 위치만 — 겹친 창을 전부 찍으면 한 줄이 수십 개가 된다."""
    first: dict[str, int] = {}
    for decl in group:
        first.setdefault(decl.rel, decl.line)
    return ", ".join(f"{rel}:{line}" for rel, line in sorted(first.items()))


def _decl_violation(group: list[_Decl]) -> str:
    names = "/".join(sorted({d.name for d in group if d.name}))
    return (f"{group[0].rel}:{group[0].line}: 선언 본문 동일({names}) — 파일 "
            f"{len({d.rel for d in group})}개가 같은 구현을 들고 있다. 공용 모듈로 뽑고 한 벌만 "
            f"남긴다. 위치: {_positions(group)}")


def _block_violation(group: list[_Decl]) -> str:
    return (f"{group[0].rel}:{group[0].line}: {BLOCK_WINDOW}줄 블록 동일 — 파일 "
            f"{len({d.rel for d in group})}개에 같은 덩어리. 함수로 뽑아 공유한다. "
            f"위치: {_positions(group)}")


def _block_decls(text: str, rel: str, marks: tuple[str, ...],
                 covered: list[tuple[int, int]]) -> list[_Decl]:
    """창 단위 지문. 선언 중복이 이미 잡은 범위 안에서 시작하는 창은 세지 않는다."""
    lines = text.split("\n")
    norm = [_norm(raw, marks) for raw in lines]
    found: list[_Decl] = []
    for index in range(len(norm) - BLOCK_WINDOW + 1):
        window = norm[index:index + BLOCK_WINDOW]
        if any(part is None for part in window):
            continue
        if len({*window}) < MIN_BLOCK_DISTINCT:
            continue
        if sum(len(part) for part in window) < MIN_BLOCK_CHARS:
            continue
        line_no = index + 1
        if any(start <= line_no <= end for start, end in covered):
            continue
        found.append(_Decl(rel, line_no, line_no + BLOCK_WINDOW - 1, "", "\n".join(window)))
    return found


def _sources(py_files: list[Path], ui_files: list[Path]) -> list[tuple[str, str, tuple[str, ...]]]:
    """(경로, 본문, 주석표기) — 파일을 한 번만 읽어 두 검사가 함께 쓴다."""
    out: list[tuple[str, str, tuple[str, ...]]] = []
    for marks, files in ((_PY_COMMENT, py_files), (_UI_COMMENT, ui_files)):
        for path in files:
            try:
                out.append((_rel(path), path.read_text(encoding=READ_ENC), marks))
            except OSError:
                continue
    return out


def _analyze(py_files: list[Path],
             ui_files: list[Path]) -> tuple[list[list[_Decl]], list[list[_Decl]]]:
    """(선언 묶음, 블록 묶음). 검사와 baseline 재생성이 같은 계산을 공유한다.

    블록이 선언의 결과(covered)를 필요로 해서 한 번에 돈다 — 같은 사실을 두 baseline 이 함께
    세면 "감소만 허용"이 모호해진다(한 번 고쳤는데 두 항목이 준다).
    """
    sources = _sources(py_files, ui_files)

    decls: list[_Decl] = []
    for rel, text, marks in sources:
        decls += _py_decls(text, rel) if marks is _PY_COMMENT else _ui_decls(text, rel)
    decl_groups = _collapse(_cluster(decls))

    covered: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for group in decl_groups:
        for decl in group:
            covered[decl.rel].append((decl.line, decl.end_line))

    blocks: list[_Decl] = []
    for rel, text, marks in sources:
        blocks += _block_decls(text, rel, marks, covered[rel])
    return decl_groups, _collapse(_cluster(blocks))


def _load_baseline(name: str) -> set[str]:
    path = ROOT / name
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding=READ_ENC).splitlines():
        token = line.split("#", 1)[0].strip()
        if token:
            keys.add(token)
    return keys


def check_duplication(py_files: list[Path],
                      ui_files: list[Path]) -> tuple[list[str], list[str]]:
    """(선언 중복 위반, 블록 중복 위반). 동결된 파일 집합은 건너뛴다."""
    decl_groups, block_groups = _analyze(py_files, ui_files)
    decl_frozen = _load_baseline(DECL_BASELINE_FILE)
    block_frozen = _load_baseline(BLOCK_BASELINE_FILE)
    decl_bad = [_decl_violation(g) for g in decl_groups
                if _key([d.rel for d in g]) not in decl_frozen]
    block_bad = [_block_violation(g) for g in block_groups
                 if _key([d.rel for d in g]) not in block_frozen]
    return decl_bad, block_bad


def emit_baselines(py_files: list[Path], ui_files: list[Path]) -> tuple[list[str], list[str]]:
    """현재 소스의 파일집합 키 전량 — 동결본 재생성용. 래칫 갱신(행 삭제)은 사람이 한다.

    키를 손으로 조립하다 틀리면 동결이 빗나가고, 빗나간 동결은 조용히 통과한다. 그래서
    정답을 게이트가 직접 찍어준다.
    """
    decl_groups, block_groups = _analyze(py_files, ui_files)
    decl_keys = [f"{_key([d.rel for d in g])}\t# 파일 {len({d.rel for d in g})}개 "
                 f"{'/'.join(sorted({d.name for d in g if d.name}))}" for g in decl_groups]
    block_keys = [f"{_key([d.rel for d in g])}\t# 파일 {len({d.rel for d in g})}개"
                  for g in block_groups]
    return decl_keys, block_keys


if __name__ == "__main__":
    from kernel.context import app_code

    _py = [f for f in app_code(*profile.SOURCE_EXT)]
    _ui_dir = profile.layer("ui")
    _ui = [f for f in app_code(*profile.UI_EXT, under=_ui_dir)] if _ui_dir else []
    _decl, _block = emit_baselines(_py, _ui)
    print(f"--- {DECL_BASELINE_FILE} ({len(_decl)}건) ---")
    print("\n".join(_decl))
    print(f"--- {BLOCK_BASELINE_FILE} ({len(_block)}건) ---")
    print("\n".join(_block))

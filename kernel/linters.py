"""kernel/linters.py — 그 언어의 표준 도구에 위임한다.

커널이 Go 의 구문 트리를 다시 파싱할 이유가 없다. Go 에는 `go vet` 과 `staticcheck` 가
있고 Rust 에는 `clippy` 가 있다. 우리가 만든 어설픈 정규식보다 그쪽이 정확하다.

하네스가 대신 하는 일은 **위임과 정직한 보고**다.

  도구가 있다   → 돌리고 출력을 위반으로 읽는다
  도구가 없다   → [TOOL] 로 찍고 설치 명령을 준다. 통과로 처리하지 않는다

마지막 줄이 핵심이다. 도구 부재를 조용히 넘기면 "검사했는데 깨끗함"과 "검사 자체를 못 함"이
구분되지 않는다 — 이 하네스가 없애려는 상태 그대로다.

언어팩의 `LINTERS` 가 선언 정본이다:

    LINTERS = [
        {"slug": "vet", "cmd": ["go", "vet", "./..."], "parse": "gcc",
         "install": "go 툴체인에 포함"},
    ]

화면 레이어는 언어팩이 아니라 아래 「화면 린터」가 같은 원칙으로 위임한다. 검사 10·17~20·42 의
판정 정본은 `kernel/eslint.harness.mjs` 하나이고, 러너는 npm 프로젝트의 `node_modules/.bin/eslint`
로 그 설정을 돌려 메시지 머리의 `[slug]` 로 여섯 섹션에 나눈다. 줄 정규식은 문자열과 코드를
구분하지 못했다 — 주석 속 색이 걸리고 여러 줄 표현은 빠졌다.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from kernel import profile
from kernel.context import ROOT, _rel

TIMEOUT_SECONDS = 90

# `path:line:col: message` 와 `path:line: message` — 대부분의 도구가 이 모양으로 낸다.
_GCC_LINE = re.compile(r"^(?P<path>[^\s:][^:]*):(?P<line>\d+):(?:(?P<col>\d+):)?\s*(?P<msg>.+)$")


def _parse_gcc(output: str, slug: str) -> list[str]:
    found: list[str] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "warning: ", "note: ")):
            continue
        match = _GCC_LINE.match(line)
        if not match:
            continue
        path = match.group("path").replace("\\", "/").lstrip("./")
        found.append(f"{path}:{match.group('line')}: {match.group('msg').strip()} ({slug})")
    return found


PARSERS = {"gcc": _parse_gcc}


def _entry_name(entry: dict) -> str:
    return str(entry.get("slug") or (entry.get("cmd") or ["도구"])[0])


def missing_tool(entry: dict) -> str:
    """실행 파일이 없으면 그 이름. 있으면 빈 문자열."""
    cmd = entry.get("cmd") or []
    return "" if (cmd and shutil.which(cmd[0])) else (cmd[0] if cmd else "cmd 미선언")


def run_one(entry: dict) -> tuple[list[str], str]:
    """한 도구를 돌린다. 반환은 (위반 목록, 건너뛴 사유). 사유가 있으면 [TOOL]."""
    slug = _entry_name(entry)
    absent = missing_tool(entry)
    if absent:
        hint = entry.get("install") or ""
        tail = f" — 설치: {hint}" if hint else ""
        return [], f"{absent} 미설치{tail}"
    try:
        done = subprocess.run(entry["cmd"], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return [f"{slug}: {TIMEOUT_SECONDS}초 내 응답 없음 — 검사 불능"], ""
    except OSError as exc:
        return [f"{slug}: 실행 실패 {exc.__class__.__name__}"], ""

    parser = PARSERS.get(str(entry.get("parse", "gcc")), _parse_gcc)
    return parser((done.stdout or "") + "\n" + (done.stderr or ""), slug), ""


def sections() -> list[tuple[str, str, list[str], str]]:
    """언어팩이 선언한 도구 전부. 반환은 (slug, 제목, 위반, 건너뛴 사유)."""
    found: list[tuple[str, str, list[str], str]] = []
    for entry in profile.LINTERS:
        if not isinstance(entry, dict):
            continue
        slug = _entry_name(entry)
        title = f"정적 분석({slug})"
        violations, skipped = run_one(entry)
        found.append((f"lint:{slug}", title, violations, skipped))
    return found


# ── 화면 린터 ────────────────────────────────────────────────────────────────

UI_SLUGS = ("ts_any", "raw_fetch", "hex_literal", "responsive", "browser_api", "hash_nav")
UI_CONFIG = Path(__file__).resolve().parent / "eslint.harness.mjs"
UI_INSTALL = "npm i -D eslint @typescript-eslint/parser typescript"
_SLUG_TAG = re.compile(r"^\[(\w+)\]\s*")
# 정규식 시절 admin 화면(`ui_admin` 레이어·경로의 /admin/)을 면제하던 넷
_ADMIN_SLUGS = ("raw_fetch", "hex_literal", "responsive", "browser_api")


@dataclass
class UiLint:
    found: dict[str, list[str]]     # slug → 위반 문장(`경로:행: 메시지`)
    missing: str                    # 비어 있지 않으면 [TOOL] 사유


def ui_npm_dir() -> Path | None:
    """node_modules 를 가진 npm 프로젝트. 프로파일 `UI_NPM_DIR` 이 우선, 없으면 ui 레이어의 첫 세그먼트 —
    프리셋 셋 다 `frontend/src` 라 유도로 충분하고 다르면 선언이 이긴다."""
    ui = profile.layer("ui")
    if not ui:
        return None
    return ROOT / (profile.UI_NPM_DIR or ui.split("/", 1)[0])


def ui_eslint_bin(npm_dir: Path) -> Path | None:
    """실행 파일 실존. `npx --no-install` 은 패키지가 없어도 npm 오류를 내며 끝나 파서가 0건으로 읽는다 —
    그게 무음 통과 경로라 파일 존재로 본다."""
    exe = npm_dir / "node_modules" / ".bin" / ("eslint.cmd" if os.name == "nt" else "eslint")
    return exe if exe.exists() else None


def _npm_relative(npm_dir: Path, rel_path: str) -> str:
    prefix = npm_dir.relative_to(ROOT).as_posix() + "/"
    return rel_path[len(prefix):] if rel_path.startswith(prefix) else rel_path


def ui_allow(npm_dir: Path) -> dict[str, list[str]]:
    """slug 별 면제 glob(npm 디렉토리 기준). 프로파일 ALLOWLIST · admin 화면 · 토큰 정본 —
    정규식 시절의 allow·admin 판정을 그대로 옮긴 것이다."""
    admin = ["**/admin/**"]
    admin_layer = profile.layer("ui_admin")
    if admin_layer:
        admin.append(_npm_relative(npm_dir, admin_layer) + "**")
    allow = profile.ALLOWLIST
    tokens = profile.layer_raw("ui_tokens")
    per_slug: dict[str, list[str]] = {
        "ts_any": [],
        "raw_fetch": [*allow["ui_fetch"], *allow["ui_fetch_wrappers"]],
        "hex_literal": [*allow["ui_hex"], *([tokens] if tokens else [])],
        "responsive": [],
        "browser_api": list(allow["ui_platform"]),
        "hash_nav": [],
    }
    return {slug: (admin if slug in _ADMIN_SLUGS else []) + [_npm_relative(npm_dir, p) for p in paths]
            for slug, paths in per_slug.items()}


def eslint_report(npm_dir: Path, targets: list[Path], allow: dict[str, list[str]],
                  tokens_note: str) -> dict[str, list[str]]:
    """하네스 설정으로 ESLint 를 돌려 `[slug]` 태그로 나눈다.

    파싱 불능(fatal)은 여섯 slug 전부에 적는다 — 그 파일은 여섯 검사 전부가 불능이기 때문이다.
    테스트가 프로파일 없이 이 함수를 직접 부른다.
    """
    exe = ui_eslint_bin(npm_dir)
    if not exe:
        raise FileNotFoundError(f"{npm_dir}/node_modules/.bin/eslint")
    env = {**os.environ, "HARNESS_UI_ALLOW": json.dumps(allow), "HARNESS_UI_TOKENS": tokens_note}
    done = subprocess.run([str(exe), "-c", str(UI_CONFIG), "--no-config-lookup", "--format", "json",
                           "--no-error-on-unmatched-pattern", *map(str, targets)],
                          cwd=npm_dir, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=TIMEOUT_SECONDS, env=env)
    found: dict[str, list[str]] = {slug: [] for slug in UI_SLUGS}
    try:
        report = json.loads(done.stdout)
    except ValueError:
        reason = (done.stderr or done.stdout).strip()[:300]
        for slug in UI_SLUGS:
            found[slug].append(f"eslint 실행 실패 — {reason}")
        return found
    for entry in report:
        rel = _rel(Path(entry["filePath"]))
        for message in entry.get("messages", []):
            head = f"{rel}:{message.get('line', 0)}: "
            if message.get("fatal"):
                for slug in UI_SLUGS:
                    found[slug].append(head + f"파싱 실패 — {message.get('message', '')[:120]}")
                continue
            tag = _SLUG_TAG.match(message.get("message", ""))
            if tag and tag.group(1) in found:
                found[tag.group(1)].append(head + _SLUG_TAG.sub("", message["message"]))
    return found


def run_ui_lint(ui_files: list[Path]) -> UiLint:
    """프로파일 글루. 대상은 러너가 준 파일 그대로 — `--file` 이면 하나, 전량이면 ui 레이어 전부."""
    npm_dir = ui_npm_dir()
    if not npm_dir or not npm_dir.is_dir():
        return UiLint({}, "npm 디렉토리 없음 — 프로파일 UI_NPM_DIR 로 지정 (기본은 ui 레이어 첫 세그먼트)")
    if not ui_eslint_bin(npm_dir):
        return UiLint({}, f"{npm_dir.relative_to(ROOT).as_posix()}/node_modules/.bin/eslint 없음 — 설치: {UI_INSTALL}")
    tokens = profile.layer_raw("ui_tokens")
    note = f"{tokens} 또는 CSS 변수" if tokens else "토큰 정본 또는 CSS 변수"
    return UiLint(eslint_report(npm_dir, ui_files, ui_allow(npm_dir), note), "")

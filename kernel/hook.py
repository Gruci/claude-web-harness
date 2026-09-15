"""Shared Claude/Codex save and stop gates; stdin is one runtime JSON payload.

PostToolUse reports violations after writes. Stop checks the full checkout,
including untracked source files. Each runtime retains its own tool policy.
"""

from __future__ import annotations

import argparse
import codecs
import json
import subprocess
import sys
from pathlib import Path

SOURCE_SUFFIXES = (".py", ".ts", ".tsx", ".md")


def read_payload() -> dict[str, object]:
    """Read one JSON object without waiting for the host to close its pipe."""
    decoder = json.JSONDecoder()
    utf8 = codecs.getincrementaldecoder("utf-8-sig")()
    text = ""
    while True:
        chunk = sys.stdin.buffer.read1(65536)
        text += utf8.decode(chunk, final=not chunk)
        try:
            value, _end = decoder.raw_decode(text.lstrip())
        except json.JSONDecodeError:
            if chunk:
                continue
            raise
        if not isinstance(value, dict):
            raise ValueError("hook payload must be an object")
        return value


def checkout_root(cwd: Path) -> Path:
    """Resolve the actual checkout, including external worktrees and nested cwd."""
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=10)
    if result.returncode:
        raise ValueError("git checkout not found")
    root = Path(result.stdout.strip()).resolve()
    if not (root / "kernel" / "runner.py").is_file():
        raise ValueError("checkout has no kernel/runner.py")
    return root


def edited_paths(payload: dict[str, object], cwd: Path) -> list[Path]:
    """Normalize Claude paths and all add/update/move destinations in a patch."""
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        direct = tool_input.get("file_path")
        if isinstance(direct, str) and direct:
            return [(cwd / direct).resolve()]
        patch = tool_input.get("command", tool_input.get("patch", tool_input.get("input", "")))
    else:
        patch = tool_input
    if not isinstance(patch, str) or "*** Begin Patch" not in patch:
        raise ValueError("file edit payload has no file_path or patch")
    if "*** End Patch" not in patch:
        raise ValueError("incomplete patch payload")
    paths: list[Path] = []
    for line in patch.splitlines():
        for prefix in ("*** Add File: ", "*** Update File: ", "*** Move to: "):
            if line.startswith(prefix):
                path = (cwd / line[len(prefix):]).resolve()
                if path not in paths:
                    paths.append(path)
    return paths


def untracked_paths(root: Path) -> list[Path]:
    """A new source file must not escape Stop because git add was omitted."""
    from kernel.context import is_harness_own

    result = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "-z"],
                            cwd=root, capture_output=True, check=True, timeout=10)
    return [root / name for name in result.stdout.decode("utf-8").split("\0")
            if name and Path(name).suffix in SOURCE_SUFFIXES
            and (Path(name).suffix == ".md" or not is_harness_own(name))]


def record_result(root: Path, event: str, sid: str, output: str, error: str = "") -> None:
    """Observation failure cannot override a gate result."""
    try:
        sys.path.insert(0, str(root))
        from kernel import trace
        trace.TRACE = root / "harness_trace.jsonl"
        name = "check_file_rules" if event == "PostToolUse" else "check_coding_rules"
        if error:
            trace.record(name, "gate_error", sid=sid, msg=error)
        else:
            trace.record_runner_output(name, sid, output)
    except Exception:
        pass


def check_file(root: Path, path: Path) -> str:
    """Enforce the checkout boundary and the shared legacy-path policy."""
    path.relative_to(root)
    sys.path.insert(0, str(root))
    from kernel import profile
    rel = path.as_posix()
    for fragment, suffix in profile.LEGACY_PATHS:
        if fragment in rel and (suffix is None or path.suffix == suffix):
            return f"[FAIL] 레거시 경로 편집 금지 (legacy_path) — 1건\n   - {path}: 현행 경로를 사용하라."
    return ""


def run_checks(root: Path, paths: list[Path], event: str, sid: str) -> int:
    """Run file checks plus the Stop full gate, preserving failure severity."""
    jobs: list[list[str]] = []
    code = 0
    for path in paths:
        legacy = check_file(root, path)
        if legacy:
            print(legacy, file=sys.stderr)
            record_result(root, event, sid, legacy)
            code = 2
        elif path.is_file() and path.suffix in SOURCE_SUFFIXES:
            jobs.append(["--file", str(path)])
    if event == "Stop":
        jobs.append([])
    for args in jobs:
        try:
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-m", "kernel.runner", *args],
                cwd=root, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=60 if event == "Stop" else 30,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            message = f"검사 불능: {type(exc).__name__}"
            print(message, file=sys.stderr)
            record_result(root, event, sid, "", message)
            code = max(code, 2 if event == "Stop" else 1)
            continue
        if result.returncode == 0:
            continue
        failure = "[FAIL]" in result.stdout
        message = "게이트 위반 — 수정 후 재검증하라." if failure else "검사 불능 — 검사기 자체를 점검하라."
        print(message, file=sys.stderr)
        print(result.stdout + result.stderr, file=sys.stderr)
        record_result(root, event, sid, result.stdout, "" if failure else message)
        code = max(code, 2 if failure or event == "Stop" else 1)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("claude", "codex"), required=True)
    parser.add_argument("--event", choices=("PostToolUse", "Stop"), required=True)
    args = parser.parse_args(argv)
    try:
        payload = read_payload()
    except (ValueError, UnicodeError) as exc:
        print(f"훅 입력 경고: {exc}", file=sys.stderr)
        if args.event != "Stop":
            return 1
        payload = {}
    cwd = Path(str(payload.get("cwd") or Path.cwd())).resolve()
    sid = str(payload.get("session_id") or "")
    try:
        root = checkout_root(cwd)
        if root != Path(__file__).resolve().parents[1]:
            # Inserting sys.path cannot rebind an already imported kernel package.
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-m", "kernel.hook",
                 "--agent", args.agent, "--event", args.event], cwd=root,
                input=json.dumps(payload), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=120,
            )
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            if result.returncode not in (0, 2):
                raise RuntimeError("대상 체크아웃의 훅 검사 불능")
            return result.returncode
        sys.path.insert(0, str(root))  # Direct script launch starts with kernel/ on sys.path.
        paths = untracked_paths(root) if args.event == "Stop" else edited_paths(payload, cwd)
        code = run_checks(root, paths, args.event, sid)
    except Exception as exc:
        # A broken executable profile is an infrastructure error, not a violation.
        print(f"검사 불능: {exc}", file=sys.stderr)
        return 2 if args.event == "Stop" else 1
    if code == 0 and args.agent == "codex":
        print("{}")
    return code


if __name__ == "__main__":
    sys.exit(main())

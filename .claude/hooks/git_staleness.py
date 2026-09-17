"""SessionStart hook — 열린 과업 주입 + 체크아웃 stale 감시.

## 열린 과업 주입

겹침 확인이 비싸면 착수 전에 건너뛰게 되고, 그 순간 보드는 있으나 마나다. `workboard/`
를 세션이 직접 열지 않아도 되도록 시작 시점에 한 줄씩 싣는다. **브랜치와 무관하게 돈다** —
착수하는 쪽은 오히려 worktree 세션이다.

## stale 감시

아무도 pull하지 않은 체크아웃은 origin보다 뒤처진다. 그 상태로 백로그를 읽으면
**이미 끝난 일을 다시 계획하게 된다** — 원본 프로젝트 실사고(2026-07-29).

기본 브랜치 + 뒤처짐이면 ff-only로 자동 정렬하고, 거부되면 격차만 알린다.
worktree 세션(다른 브랜치)은 이 절만 조용히 통과한다.

SessionStart(startup 한정 — /clear·compact마다 pull이 도는 것을 막는다). 작업 트리를
바꾸는 유일한 훅이라 발화 범위를 최소로 둔다.

기본 브랜치는 origin/HEAD에서 자동 감지한다 — main/master 하드코딩은 이식성을 깬다.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 보드는 공유 체크아웃 한 곳이다 — 자기 트리로 잡으면 세션 수만큼 갈라진다
# (`kernel.workboard.board_dir`). 커널을 못 읽으면 보드 주입만 접고 stale 감시는 계속한다.
try:
    from kernel.workboard import board_dir  # noqa: E402
    BOARD_DIR: Path | None = board_dir()
except Exception:
    BOARD_DIR = None

_FETCH_TIMEOUT_SEC = 15


def _git(*args: str, timeout: int = 5) -> str | None:
    """git 실행 → stdout strip. 실패·타임아웃이면 None (훅은 조용히 통과)."""
    try:
        done = subprocess.run(
            ("git", *args), capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _default_branch() -> str | None:
    """origin/HEAD → 브랜치명. 미설정 클론이면 main/master 중 origin에 실존하는 쪽."""
    ref = _git("rev-parse", "--abbrev-ref", "origin/HEAD")
    if ref and "/" in ref:
        return ref.rsplit("/", 1)[-1]
    for candidate in ("main", "master"):
        if _git("rev-parse", "--verify", "--quiet", f"origin/{candidate}") is not None:
            return candidate
    return None


def _field(text: str, name: str) -> str:
    """workboard 파일에서 `- <name>: <값>` 한 줄. 없으면 빈 문자열."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"- {name}:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def print_open_tasks() -> None:
    """열린 과업 한 줄 요약 — 착수 전 확인을 세션 기억에 안 맡긴다."""
    if BOARD_DIR is None or not BOARD_DIR.is_dir():
        return
    rows = []
    for path in sorted(BOARD_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        state = _field(text, "상태") or "?"
        task = _field(text, "과업")
        rows.append(f"  {path.stem} [{state}] {task}")
    if not rows:
        return
    print(f"[WORKBOARD] 열린 과업 {len(rows)}건 — 같은 범위면 새로 파지 말고 합류하거나 쌓는다.")
    for row in rows:
        print(row)
    print("  서식·착수 라우팅: workboard/README.md")


def main() -> None:
    print_open_tasks()
    branch = _default_branch()
    if branch is None or _git("rev-parse", "--abbrev-ref", "HEAD") != branch:
        return   # 원격 미설정이거나 worktree 세션 — 자기 브랜치가 정본이라 검사 대상이 아니다
    if _git("fetch", "origin", "--quiet", timeout=_FETCH_TIMEOUT_SEC) is None:
        return   # 오프라인·인증 실패 — 세션 시작을 막을 이유가 없다
    behind = _git("rev-list", "--count", f"HEAD..origin/{branch}")
    if not behind or behind == "0":
        return

    # 자동 정렬은 ff-only라 커밋을 잃을 수 없다. 로컬 변경과 부딪히는지는 git이 판정한다 —
    # 자체 dirty 검사는 상시 변경되는 tracked 파일 하나에 막혀 영영 안 타는 실패 사례가 있었다.
    if _git("pull", "--ff-only", "origin", branch, timeout=_FETCH_TIMEOUT_SEC) is not None:
        print(f"[GIT SYNC] 체크아웃이 {behind}커밋 뒤여서 origin/{branch}로 정렬했다. "
              f"BACKLOG.md 는 최신이다.")
        return

    print(f"[GIT STALE] 체크아웃이 origin/{branch}보다 {behind}커밋 뒤고 자동 정렬(ff-only)이 거부됐다. "
          f"로컬 변경이 유입분과 겹친다.\n"
          f"  BACKLOG.md·소스를 그대로 믿지 마라 — 이미 머지된 과업을 다시 계획하게 된다.\n"
          f"  착수 전 `git log --oneline HEAD..origin/{branch}`로 그 사이 뭐가 들어왔는지 먼저 봐라.")


if __name__ == "__main__":
    main()
    sys.exit(0)

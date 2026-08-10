"""SessionStart hook — 체크아웃 stale 감시.

아무도 pull하지 않은 체크아웃은 origin보다 뒤처진다. 그 상태로 EDITING.md 백로그를
읽으면 **이미 끝난 일을 다시 계획하게 된다** — 원본 프로젝트 실사고(2026-07-29).

기본 브랜치 + 뒤처짐이면 ff-only로 자동 정렬하고, 거부되면 격차만 알린다.
worktree 세션(다른 브랜치)은 조용히 통과한다.

SessionStart(startup 한정 — /clear·compact마다 pull이 도는 것을 막는다). 작업 트리를
바꾸는 유일한 훅이라 발화 범위를 최소로 둔다.

기본 브랜치는 origin/HEAD에서 자동 감지한다 — main/master 하드코딩은 이식성을 깬다.
"""
import subprocess
import sys

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


def main() -> None:
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
              f"EDITING.md 백로그는 최신이다.")
        return

    print(f"[GIT STALE] 체크아웃이 origin/{branch}보다 {behind}커밋 뒤고 자동 정렬(ff-only)이 거부됐다. "
          f"로컬 변경이 유입분과 겹친다.\n"
          f"  EDITING.md 백로그·소스를 그대로 믿지 마라 — 이미 머지된 과업을 다시 계획하게 된다.\n"
          f"  착수 전 `git log --oneline HEAD..origin/{branch}`로 그 사이 뭐가 들어왔는지 먼저 봐라.")


if __name__ == "__main__":
    main()
    sys.exit(0)

"""공유 메인 체크아웃 stale 감시 — SessionStart 훅.

공유 체크아웃(main 고정 읽기 구역)은 아무도 pull 하지 않으면 origin/main 보다 뒤처진다.
그 상태로 EDITING.md 백로그를 읽으면 **이미 끝난 일을 계획하게 된다** — 2026-07-29 실사고.

main + 클린 트리면 ff-only 로 자동 정렬하고, 아니면 격차만 알린다.
worktree 세션(브랜치가 main 이 아님)은 조용히 통과한다.
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


def main() -> None:
    if _git("rev-parse", "--abbrev-ref", "HEAD") != "main":
        return   # worktree 세션 — 자기 브랜치가 정본이라 검사 대상이 아니다
    if _git("fetch", "origin", "--quiet", timeout=_FETCH_TIMEOUT_SEC) is None:
        return   # 오프라인·인증 실패 — 세션 시작을 막을 이유가 없다
    behind = _git("rev-list", "--count", "HEAD..origin/main")
    if not behind or behind == "0":
        return

    # 자동 정렬은 ff-only 라 커밋을 잃을 수 없다. 로컬 변경과 부딪히는지는 git 이 판정한다 —
    # 자체 dirty 검사는 상시 변경되는 tracked 파일 하나에 막혀 영영 안 타는 실패 사례가 있었다.
    if _git("pull", "--ff-only", "origin", "main", timeout=_FETCH_TIMEOUT_SEC) is not None:
        print(f"[GIT SYNC] 공유 체크아웃이 {behind}커밋 뒤여서 origin/main 으로 정렬했다. "
              f"EDITING.md 백로그는 최신이다.")
        return

    print(f"[GIT STALE] 공유 체크아웃이 origin/main 보다 {behind}커밋 뒤고 자동 정렬(ff-only)이 거부됐다. "
          f"로컬 변경이 유입분과 겹친다.\n"
          f"  EDITING.md 백로그·소스를 그대로 믿지 마라 — 이미 머지된 과업을 다시 계획하게 된다.\n"
          f"  착수 전 `git log --oneline HEAD..origin/main` 으로 그 사이 뭐가 들어왔는지 먼저 봐라.")


if __name__ == "__main__":
    main()
    sys.exit(0)

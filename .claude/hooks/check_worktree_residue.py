"""Stop hook — 일이 끝난 worktree 가 남아있으면 세션 종료를 막는다.

"머지 후 worktree remove → branch -d" 규칙이 산문으로만 있으면 흘러내린다. 원류 프로젝트
실태: 머지가 끝난 worktree 4개(최고령 4일)가 쌓여 `git worktree list` 로 "지금 누가 뭘
잡고 있나"를 못 읽었다 — 이름 접미 `--<sid8>` 을 강제한 이유가 그 조인인데, 죽은 것이
섞이면 무의미해진다.

## 죽은 worktree 판정 — 세 조건을 모두 만족할 때만

갓 판 worktree 와 머지 끝난 worktree 는 둘 다 기본 브랜치의 조상이고 자기 커밋이 0개라
그것만으로는 안 갈린다. 갈라주는 것은 **push 이력**이다.

1. `branch.<브랜치>.merge` 가 **자기 이름**(`refs/heads/<브랜치>`)이다 = `push -u` 로 한 번이라도
   올렸다. **`.remote` 유무로 가르면 안 된다** — `git worktree add -b X origin/<기본>` 은 시작점을
   upstream 으로 자동 등록해 `remote=origin, merge=refs/heads/<기본>` 을 남긴다. 그걸 push 이력으로
   읽으면 아래 셋이 전부 참이 되어 **갓 판 worktree 가 통째로 "머지 완료"** 가 된다. 실측으로
   확인했다 — 만든 직후 `remote=origin`, origin ref 없음, 기본 브랜치의 조상 참. 갓 판 브랜치의
   `merge` 는 기본 브랜치를 가리키므로 여기서 걸러진다.
2. `refs/remotes/origin/<브랜치>` 가 없다 = 머지되어 원격에서 삭제됐다.
   PR 이 열려 있는 동안은 있으므로 작업 중엔 안 걸린다.
   **미탐 조건**: 원격 자동삭제(deleteBranchOnMerge)가 없는 레포에서는 이 조건이 영영 거짓이라
   잔존을 못 잡는다 — 오탐(작업 중인 것을 지우라고 함)이 없음을 우선한 선택이다.
3. 브랜치가 원격 기본 브랜치의 조상이다 = 실제로 머지됐다.
   push 후 머지 없이 버린 브랜치는 여기서 걸러진다 — 남의 미머지 작업을 지우라고 하면 안 된다.

## 살아있는 세션은 건드리지 않는다

`git worktree list --porcelain` 의 lock 줄은 PID 를 싣는다. 그 프로세스가 살아있으면 남의
세션이 그 안에 서 있다는 뜻이라 건너뛴다. 반대로 PID 가 죽은 lock 은 건너뛰지 않는다 —
크래시 잔해를 살아있는 것으로 치면 이 게이트가 잡아야 할 바로 그 경우가 영구 면제된다.

훅 자신이 판정 불능이면(git 실패·기본 브랜치 미상) 통과시킨다. 하네스 오작동으로 종료를
막으면 복구 수단이 그 세션이라 잠긴다.

## 단계 = 경고(exit 1), 차단(2) 아님

여기 판정은 전부 **git 상태 추론**이다 — ref 유무와 config 값으로 "머지가 끝났을 것"을 추측한다.
직접 관측(검사기가 뱉은 위반·실제로 거기 있는 파일)이 아니라서 틀릴 수 있고, 실제로 틀렸다.
차단이면 잘못된 지시를 따르거나 세션이 잠기거나 둘 중 하나인데 둘 다 나쁘다.

검출을 끄면 잔해가 안 보이므로 **끄는 대신 단계를 낮춘다** — 매 턴 말은 하되 문은 안 잠근다.
정본은 `HARNESS.md` 「단계」다.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import default_branch, git_output as _git  # noqa: E402

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
_LOCK_PID = re.compile(r"\(pid (\d+)\)")


def _alive(pid: int) -> bool:
    """그 PID 가 살아있나. 판정 불능이면 살아있다고 본다(남의 세션을 함부로 죽은 것 취급하지 않는다)."""
    try:
        done = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                              capture_output=True, text=True, errors="replace", timeout=15)
    except Exception:
        return True
    return str(pid) in done.stdout


def parse_worktrees(porcelain: str) -> list[dict]:
    """`git worktree list --porcelain` → [{path, branch, lock_pid}]. 메인 체크아웃은 뺀다.

    메인은 **첫 레코드**로 가른다(git 계약). 훅 파일 경로로 가르면 안 된다 — 이 훅은 worktree
    안에서도 돌고 그때 `parents[2]` 는 그 worktree 라, 자기 자신을 메인으로 빼고 진짜 메인을
    검사 대상에 넣는 역전이 난다.
    """
    trees: list[dict] = []
    cur: dict = {}
    for line in porcelain.splitlines():
        if line.startswith("worktree "):
            if cur:
                trees.append(cur)
            cur = {"path": line[len("worktree "):], "branch": None, "lock_pid": None}
        elif line.startswith("branch refs/heads/"):
            cur["branch"] = line[len("branch refs/heads/"):]
        elif line.startswith("locked"):
            found = _LOCK_PID.search(line)
            cur["lock_pid"] = int(found.group(1)) if found else None
    if cur:
        trees.append(cur)
    return [t for t in trees[1:] if t["branch"]]


def is_dead(branch: str, base: str) -> bool:
    """머지가 끝나 존재 이유가 사라진 브랜치인가. 판정 근거는 모듈 머리 참조."""
    upstream = (_git("config", "--get", f"branch.{branch}.merge") or "").strip()
    if upstream != f"refs/heads/{branch}":
        return False                                    # push 이력 없음 = 작업 전이거나 작업 중
    if _git("show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}") is not None:
        return False                                    # 원격에 살아있음 = PR 진행 중
    return _git("merge-base", "--is-ancestor", f"refs/heads/{branch}", f"origin/{base}") is not None


def main() -> None:
    porcelain = _git("worktree", "list", "--porcelain")
    if porcelain is None:
        sys.exit(0)
    base = default_branch()
    if base is None:
        sys.exit(0)                                     # 기본 브랜치 미상 — 판정 불능은 통과

    residue = []
    for tree in parse_worktrees(porcelain):
        if tree["lock_pid"] is not None and _alive(tree["lock_pid"]):
            continue                                    # 남의 세션이 그 안에 서 있다
        if is_dead(tree["branch"], base):
            residue.append(tree)
    if not residue:
        sys.exit(0)

    # Stop 훅 차단 사유는 stderr 로 내보내야 Claude 에게 전달된다(stdout 은 무시됨).
    print(f"[WORKTREE RESIDUE] 일이 끝난 worktree {len(residue)}건이 남아있습니다.", file=sys.stderr)
    for tree in residue:
        name = Path(tree["path"]).name
        print(f"  {name}  [{tree['branch']}] — 머지 완료·원격 삭제됨", file=sys.stderr)
    print("`git worktree remove <경로>` → `git branch -d <브랜치>` 순서로 정리한 후 종료하세요.", file=sys.stderr)
    print("(순서가 계약이다 — worktree 가 점유 중인 브랜치는 로컬 삭제가 거부된다)", file=sys.stderr)
    # 경고(1)지 차단(2)이 아니다 — 판정 근거가 git 상태 추론이라서다. HARNESS.md 「단계」 참조.
    sys.exit(1)


if __name__ == "__main__":
    main()

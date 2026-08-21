"""PreToolUse(EnterWorktree|Bash|PowerShell) 훅 — 새 worktree 이름에 세션 식별자 접미를 강제.

매처는 셸을 실행하는 툴을 전부 담는다 — `Bash` 만 걸면 같은 `git worktree add` 가 `PowerShell`
툴로 빠져나간다(원류 프로젝트 2026-08-06 실측).

`git worktree list` 로 누가 무엇을 잡고 있는지 알 수 없었다. 이름이 브랜치와 갈리기까지 한다.
보드에는 `#sid:` 가 있는데 worktree 쪽에 연결고리가 없어 둘을 조인할 수 없다 — 그래서
"다들 쓰고 있나 보다"로 추측하게 된다.

서식은 `<주제>--<sid8>` 이다. 주제를 앞에 두는 이유는 사람이 목록에서 먼저 읽는 것이 "무엇"이고
"누구"는 조인 키이기 때문이다. 접미만 검사하고 주제 작명은 자율이다.

## 왜 Stop 이 아니라 생성 시점인가

이미 만들어진 것을 뒤늦게 지적하면 개명해야 하는데, 세션이 그 안에 서 있으면 디렉토리 이동이
실패한다. 남의 worktree 까지 잡으면 종료 데드락이다. 만들기 **전에** 막으면 개명 상황 자체가
없고, 내 호출에만 발화하므로 다른 세션에 영향이 없다. 기존 worktree 는 건드리지 않는다.

## 판정 불능

세션 식별자를 못 구하면 exit 1(비차단 경고)이다. 하네스가 자기 상태를 모르는 것은 규칙 위반이
아니라 오작동이고, 그것으로 worktree 생성을 막으면 격리 자체가 불가능해진다.
"""
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import read_hook_payload  # noqa: E402

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SID_LEN = 8
WORKTREE_ADD = re.compile(r"\bgit\b.*\bworktree\s+add\b")


def session_id8(payload: dict) -> str | None:
    """`session_id` 우선, 없으면 transcript 파일명에서. 둘 다 없으면 None."""
    session_id = str(payload.get("session_id") or "")
    if len(session_id) >= SID_LEN:
        return session_id[:SID_LEN]
    stem = Path(str(payload.get("transcript_path") or "")).stem
    return stem[:SID_LEN] if len(stem) >= SID_LEN else None


def offending_name(name: str, sid8: str) -> str | None:
    """서식을 안 지킨 worktree 이름. 지켰으면 None."""
    if not name:
        return None
    return None if name.endswith(f"--{sid8}") else name


def worktree_add_target(command: str) -> str | None:
    """`git worktree add` 가 만들려는 경로의 basename. 생성 명령이 아니면 None.

    `list`·`remove`·`move` 는 생성이 아니라 통과다. 옵션과 `-b <브랜치>` 값을 걷어낸 첫 인자가
    경로다 — 브랜치명을 경로로 오독하면 정상 호출이 막힌다.

    **명령의 머리에서만 찾는다.** 문자열 전체를 훑으면 커밋 메시지 heredoc 안에 적힌
    `git worktree add ...` 같은 산문을 명령으로 오독한다 — 이 훅이 자기 커밋을 막았다.
    같은 부류를 `check_bash_write.py` 의 링크 판정도 앞 3토큰 제한으로 막는다.
    """
    if not WORKTREE_ADD.search(command):
        return None
    try:
        # posix 모드는 백슬래시를 이스케이프로 먹는다 — Windows 경로가 뭉개져 basename 판정이
        # 통째로 틀린다. 쪼개기 전에 구분자를 정규화한다.
        tokens = shlex.split(command.replace("\\", "/"), posix=True)
    except ValueError:
        return None
    if "add" not in tokens:
        return None
    index = tokens.index("add")
    # `git worktree add` 는 세 토큰이 붙어 있다. 앞 둘이 그 형태가 아니면 인용문 안의 산문이다.
    if index < 2 or tokens[index - 1] != "worktree" or "git" not in tokens[index - 2]:
        return None
    rest = tokens[index + 1:]
    skip_next = False
    for token in rest:
        if skip_next:
            skip_next = False
            continue
        if token in ("-b", "-B", "--reason"):
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        return Path(token).name
    return None


def _target_name(tool_name: str, tool_input: dict) -> str | None:
    """이 호출이 만들려는 worktree 이름. 생성이 아니면 None."""
    if tool_name == "EnterWorktree":
        # `path` 는 기존 worktree 진입이라 생성이 아니다.
        return None if tool_input.get("path") else (tool_input.get("name") or None)
    return worktree_add_target(tool_input.get("command") or "")


def main() -> None:
    try:
        payload = read_hook_payload()
    except Exception as exc:
        print(f"[WORKTREE NAME] 훅 페이로드 파싱 실패({exc.__class__.__name__}) — 이름 검사가 쉬고 있다.",
              file=sys.stderr)
        sys.exit(1)

    name = _target_name(payload.get("tool_name") or "", payload.get("tool_input") or {})
    if not name:
        sys.exit(0)

    sid8 = session_id8(payload)
    if sid8 is None:
        print("[WORKTREE NAME] 세션 식별자를 못 구했다 — 이름 검사를 건너뛴다. 훅을 점검하라.",
              file=sys.stderr)
        sys.exit(1)

    if offending_name(name, sid8) is None:
        sys.exit(0)

    print(
        f"[WORKTREE NAME] worktree 이름에 세션 식별자가 없다 — `{name}` → `{name}--{sid8}`.\n"
        "`git worktree list` 만으로 누가 무엇을 잡고 있는지 보여야 하고, 그 키가 보드 행의 #sid 다.\n"
        "(정본: EDITING.md worktree 병렬 프로토콜)",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()

"""tests/test_hooks.py — 훅 판정 함수의 행동 테스트.

훅은 러너 밖에서 돌아 골든 대조가 안 닿는다. 그런데 훅의 오판은 게이트 오탐보다 비싸다 —
세션을 잠그거나 작업 중인 worktree 를 지우라고 요구한다. 실제로 그 둘이 연달아 났다
(`dev/LESSONS.md` §19). 그래서 판정 함수만 따로 잡아둔다.

  worktree 잔해   갓 판 worktree 를 잔해로 뒤집지 않는가
  격리 밖 링크    실사고 경로를 잡고 산문·정상 링크는 통과시키는가

실행: `python -X utf8 tests/test_hooks.py`
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"


def _load(name: str):
    """훅을 모듈로 읽는다. 훅끼리 `_hookio` 를 import 하므로 경로를 먼저 얹는다."""
    sys.path.insert(0, str(HOOKS))
    spec = importlib.util.spec_from_file_location(f"_hook_{name}", HOOKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 중첩 def 금지(검사 2)라 가짜 git 을 모듈 레벨에 둔다. `_UPSTREAM` 이 케이스를 가른다.
_UPSTREAM = ""


def _fake_git(*args: str) -> str | None:
    """worktree 잔해 판정이 묻는 세 질문만 답한다 — 나머지 둘은 항상 '잔해 쪽'이다."""
    if args[0] == "config":
        return _UPSTREAM                          # branch.<X>.merge 값
    if args[0] == "show-ref":
        return None                               # origin 에 없다
    if args[0] == "merge-base":
        return ""                                 # 기본 브랜치의 조상이다
    return None


def test_fresh_worktree_not_dead() -> None:
    """`git worktree add -b X origin/main` 이 남기는 upstream 은 push 이력이 아니다.

    시작점을 upstream 으로 자동 등록하므로 `branch.X.remote` 는 갓 판 브랜치에도 있다.
    그것을 push 이력으로 읽으면 나머지 두 조건(원격 ref 없음·기본 브랜치의 조상)이 자동으로
    참이라, worktree 를 만든 그 순간부터 "머지 완료, 지워라"가 된다.
    """
    global _UPSTREAM
    residue = _load("check_worktree_residue")
    residue._git = _fake_git

    _UPSTREAM = "refs/heads/main\n"               # 갓 판 것 — upstream 이 기본 브랜치다
    assert residue.is_dead("feat/x", "main") is False, "갓 판 worktree 를 잔해로 판정했다"

    _UPSTREAM = "refs/heads/feat/x\n"             # push -u 이력 — upstream 이 자기 이름이다
    assert residue.is_dead("feat/x", "main") is True, "진짜 잔해를 놓쳤다"

    _UPSTREAM = ""                                # upstream 없음 = 로컬 전용 브랜치
    assert residue.is_dead("feat/x", "main") is False


def test_outbound_link() -> None:
    """격리 밖 링크만 잡고 산문·트리 안 링크는 통과시킨다."""
    gate = _load("check_bash_write")
    blocked = [
        ("cmd /c mklink /J .claude/worktrees/f--1234/frontend/node_modules "
         "D:/proj/frontend/node_modules", "의존성 링크(실사고 경로)"),
        ("ln -s /etc/hosts .claude/worktrees/f--1234/hosts", "트리 밖"),
        ("New-Item -ItemType Junction -Path .claude/worktrees/a/nm -Target ../../node_modules",
         "PowerShell junction"),
    ]
    allowed = [
        ("ln -s docs/tasks/plan.md docs/tasks/current.md", "트리 안에서 안으로"),
        ('git commit -m "ln -s 로 걸었던 링크 제거"', "커밋 메시지 안의 산문"),
        ('echo "use ln -s here" >> notes.txt', "인용문 안"),
    ]
    for command, label in blocked:
        assert gate.outbound_link(command) is not None, f"막아야 하는데 통과: {label}"
    for command, label in allowed:
        assert gate.outbound_link(command) is None, f"통과해야 하는데 막음: {label}"


def test_board_header_is_split_by_separator() -> None:
    """표 헤더는 문구가 아니라 구분선 위치로 가른다.

    문구로 가르던 구버전은 서식이 바뀌면 헤더를 데이터 행으로 세어, 세션 식별 불가 경로에서
    헤더 하나만으로 영영 막혔다.
    """
    lock = _load("check_editing_lock")
    board = (
        "## 🔒 과업 보드 (Active Edits)\n\n"
        "| 무슨 일 | 어디를 | 언제 | 상태 |\n"
        "|---|---|---|---|\n"
        "| feat/a #sid:11111111 | 스코프 | 2026-08-21 | 진행 |\n"
        "\n## 다음 절\n"
    )
    rows = lock._active_edit_rows(board)
    assert len(rows) == 1, f"헤더가 데이터 행으로 셌다: {rows}"
    assert "#sid:11111111" in rows[0]
    assert lock.branch_of(rows[0]) == "feat/a"


def test_worktree_add_only_at_command_head() -> None:
    """인용문 안의 `git worktree add` 는 명령이 아니다.

    문자열 전체를 훑던 판정이 커밋 메시지 heredoc 안의 산문을 명령으로 읽어 자기 커밋을 막았다.
    `outbound_link` 가 앞 3토큰 제한으로 막는 것과 같은 부류다 — 명령인지 인자인지는 자리가 정한다.
    """
    naming = _load("check_worktree_name")
    # 실제로 이 훅을 터뜨린 명령이다. heredoc 본문은 따옴표가 아니라 shlex 가 그대로 낱말로
    # 쪼개므로 `git`·`worktree`·`add` 가 나란히 선다 — 인접성 검사로는 안 갈리고 자리로만 갈린다.
    heredoc_prose = (
        "git commit -q -F - <<'EOF'\n"
        "feat(harness): 역이식\n\n"
        "잔해 훅이 갓 판 worktree 를 뒤집었다. `git worktree add -b X origin/main`\n"
        "이 시작점을 upstream 으로 자동 등록해서 remote 가 갓 판 브랜치에도 있다.\n"
        "EOF"
    )
    real = [
        ("git worktree add .claude/worktrees/feat-x--16aa3fa6 -b feat/x origin/main",
         "feat-x--16aa3fa6"),
        ("git worktree add -b feat/x .claude/worktrees/topic--abcd1234 origin/main",
         "topic--abcd1234"),
        ("cd /repo && git worktree add .claude/worktrees/z--abcd1234", "z--abcd1234"),
    ]
    prose = [
        (heredoc_prose, "커밋 메시지 heredoc 안 산문 — 실제 사고 케이스"),
        ('git commit -m "git worktree add -b X origin/main 설명"', "인용문 안"),
        ("echo git worktree add foo > notes.txt", "echo 인자"),
        ("git worktree list", "생성이 아닌 하위명령"),
        ("git worktree remove .claude/worktrees/a", "제거"),
    ]
    for command, expected in real:
        assert naming.worktree_add_target(command) == expected, f"정상 생성을 못 읽었다: {command}"
    for command, label in prose:
        assert naming.worktree_add_target(command) is None, f"명령으로 오독: {label}"


def demo() -> None:
    for check in (test_fresh_worktree_not_dead, test_outbound_link,
                  test_board_header_is_split_by_separator,
                  test_worktree_add_only_at_command_head):
        check()
        print(f"  [OK] {check.__name__}")
    print("훅 행동 테스트 전건 통과")


if __name__ == "__main__":
    demo()

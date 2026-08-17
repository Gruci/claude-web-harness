"""PreToolUse(Bash|PowerShell) 훅 — 셸 명령이 깨면 안 되는 계약 3종을 사전 차단.

매처에 **셸을 실행하는 툴을 전부** 담아야 한다. `Bash` 만 걸면 같은 명령이 `PowerShell`
툴로 그냥 나간다(원류 프로젝트 2026-08-06 실측). 두 툴의 입력 필드가 똑같이 `command` 다.

| 절 | 막는 것 | 근거 |
|----|---------|------|
| 소스 쓰기 | 리다이렉트·tee·sed -i 로 레포 안 소스 파일 쓰기 | 작성 시점 게이트 우회 |
| 판정 우회 | 판정 명령(gh pr checks 등)을 파이프·체인 앞에 두기 | exit code 가 사라져 pending 인 채 merge 가 나간다 |
| 공유 트리 변경 | 병렬 체제에서 공유 메인 체크아웃의 git 변경 명령 | add -A 쓸어담기·브랜치 오염 |

## 절 1 — 소스 쓰기 (작성 시점 게이트 우회 방지)

PostToolUse(Edit|Write) 게이트는 Edit·Write 툴이 지나간 자리만 본다. `echo ... > foo.py` 는
그 게이트를 통째로 지나가고 Stop 훅이 세션 끝에야 잡는데, 작성 시점 검사의 존재 이유가 바로
그 지연을 없애는 것이다. CLAUDE.md "게이트 우회 금지" 산문의 기계 강제분이다.
차단 조건은 **레포 안 + 소스 확장자** 둘 다일 때뿐이다. 스크래치패드·레포 밖·로그는
통과시킨다 — 게이트가 일상 셸 작업을 막기 시작하면 우회 습관이 생겨 역효과다.
확장자 정본은 프로파일(`SOURCE_EXT`·`UI_EXT`)이다 — 커널이 그 언어를 보면 이 훅도 본다.

## 절 3 — 발동 조건이 원류와 다르다

원류는 상시 worktree 체제라 무조건 발동이지만, 여기서는 **링크드 worktree 가 하나라도
있을 때만** 발동한다. 단일 세션 그린필드에는 지킬 대상(제2의 작성자)이 없고, 병렬이
시작되는 순간 공유 트리가 기계적으로 구현 금지 구역이 된다 — 체제 전환이 정책 선언이
아니라 관측으로 일어난다. 설정 0.
"""
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import read_hook_payload  # noqa: E402

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]

# 프로파일이 확장자 정본이다. 프로파일 로드가 깨져도 훅은 살아야 하므로 기본값 폴백.
_FALLBACK_EXT = (".py", ".ts", ".tsx", ".md", ".css", ".html", ".json")
sys.path.insert(0, str(ROOT))
try:
    from kernel import profile as _profile
    SOURCE_SUFFIXES = tuple(dict.fromkeys(
        [ext.lstrip("*").lower() for ext in (*_profile.SOURCE_EXT, *_profile.UI_EXT)]
        + list(_FALLBACK_EXT)))
except Exception:
    SOURCE_SUFFIXES = _FALLBACK_EXT

REDIRECTS = (">", ">>")
SEPARATORS = (";", "|", "||", "&&", "&")

# 절 2 — 판정 명령. 뒤에 파이프나 체인이 붙으면 판정의 exit code 가 사라진다.
# merge 는 되돌릴 수 없어서 CI 축만 넣는다. 빌드·테스트 체인은 되돌릴 수 있으므로 자율이다 —
# 하네스는 누적형과 비가역형만 강제한다.
VERDICT_COMMANDS = ("gh pr checks", "gh run watch")

# 절 3 — 병렬 체제의 공유 메인 체크아웃에서 금지되는 git 변경 명령.
# `git checkout` 은 파일 복원도 겸하지만 브랜치 전환이 실사고의 실제 기전이라 통째로 막는다.
MUTATING_GIT = ("git commit", "git add", "git switch", "git checkout", "git merge")


def _tokens(command: str) -> list[str]:
    """셸 토큰. 정규식이 아니라 shlex 를 쓰는 이유는 따옴표다 — `grep "> a.py"` 의 `>` 는
    리다이렉트가 아닌데 정규식은 구분하지 못해 과차단한다. `punctuation_chars` 가 `>`·`|` 를
    독립 토큰으로 떼주므로 연산자와 인자를 그대로 읽을 수 있다.

    lazy: 따옴표가 안 맞아 파싱이 깨지면 빈 목록(=통과)이다. 그런 명령은 셸도 못 돌린다.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return []


def _repo_source(target: str) -> str | None:
    """이 토큰이 '레포 안 소스 파일 경로'면 레포 상대경로, 아니면 None."""
    if not target or target.startswith(("&", "$", "-")) or target.startswith("/dev/"):
        return None
    path = Path(target)
    resolved = path if path.is_absolute() else ROOT / path
    try:
        rel = resolved.resolve().relative_to(ROOT)
    except (ValueError, OSError):
        return None                      # 레포 밖 — 스크래치패드·임시파일·시스템 경로
    if resolved.suffix.lower() not in SOURCE_SUFFIXES:
        return None
    return rel.as_posix()


def _write_candidates(tokens: list[str]) -> list[str]:
    """쓰기 대상이 될 수 있는 토큰들 — 리다이렉트 타깃 · `tee` 인자 · `sed -i` 대상 파일.

    lazy: 이 셋만 본다. `python -c "open('x.py','w')"`·`mv`·`cp` 로 제자리에 넣는 경로는 안
    잡는다 — 셸 의미론 전체를 재현하는 일반해는 없고, 실제로 쓰이는 우회는 이 셋이다.
    새 우회가 관측되면 여기 절을 추가한다.
    """
    candidates: list[str] = []
    in_sed = sed_inplace = False
    for index, token in enumerate(tokens):
        if token in SEPARATORS:
            in_sed = sed_inplace = False
        elif token in REDIRECTS:
            candidates += tokens[index + 1: index + 2]
        elif token == "tee":
            candidates += [t for t in tokens[index + 1:] if not t.startswith("-")][:1]
        elif token == "sed":
            in_sed, sed_inplace = True, False
        elif in_sed and token.startswith("-i"):
            sed_inplace = True
        elif sed_inplace and not token.startswith("-"):
            candidates.append(token)
    return candidates


def blocked_targets(command: str) -> list[str]:
    """셸 명령이 쓰려는 레포 안 소스 파일들 (레포 상대경로, 중복 제거)."""
    found: list[str] = []
    for candidate in _write_candidates(_tokens(command)):
        rel = _repo_source(candidate)
        if rel and rel not in found:
            found.append(rel)
    return found


def _segments(tokens: list[str]) -> list[list[str]]:
    """구분자로 끊은 명령 조각들. 조각의 머리만 봐야 `echo "git commit"` 처럼 인자로 들어간
    문자열을 명령으로 오독하지 않는다.
    """
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def piped_verdict(command: str) -> str | None:
    """판정 명령이 마지막 조각이 아니면 그 명령 이름, 아니면 None.

    `gh pr checks --watch | tail -2 && gh pr merge` 에서 체인의 exit code 는 tail 것이라
    checks 가 pending 이어도 merge 가 나간다. 판정이 마지막 조각이면 exit code 가 살아 있으니
    통과다 — `echo hi && gh pr checks` 는 막지 않는다.
    """
    for segment in _segments(_tokens(command))[:-1]:
        head = " ".join(segment[:3])
        hit = next((verdict for verdict in VERDICT_COMMANDS if head.startswith(verdict)), None)
        if hit:
            return hit
    return None


def _is_main_checkout() -> bool:
    """공유 메인 체크아웃 판정. 링크된 worktree 는 `.git` 이 파일이고 메인은 디렉토리다.

    `cwd == ROOT` 로는 구분되지 않는다 — 훅 파일이 트리마다 복제돼 있어 양쪽에서 참이다.
    """
    return (ROOT / ".git").is_dir()


def _parallel_mode() -> bool:
    """링크드 worktree 가 하나라도 있으면 병렬 체제다. 판정 불능이면 비병렬(불발동)."""
    try:
        done = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=str(ROOT),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=15)
    except Exception:
        return False
    if done.returncode != 0:
        return False
    records = [line for line in done.stdout.splitlines() if line.startswith("worktree ")]
    return len(records) > 1                              # 첫 레코드(메인) 이후가 있는가


def shared_tree_mutation(command: str) -> str | None:
    """병렬 체제에서 공유 트리를 겨눈 git 변경 명령. worktree 안에서는 항상 None 이라
    프로토콜을 지키는 경로에는 마찰이 없다. `git -C <worktree> commit` 도 통과한다 —
    대상이 공유 트리가 아니다.
    """
    if not _is_main_checkout() or not _parallel_mode():
        return None
    for segment in _segments(_tokens(command)):
        head = " ".join(segment[:3])
        hit = next((mutation for mutation in MUTATING_GIT if head.startswith(mutation)), None)
        if hit:
            return hit
    return None


def main() -> None:
    try:
        payload = read_hook_payload()
    except Exception as exc:
        # 하네스 오작동은 비차단(exit 1)이다. 여기서 exit 2 를 내면 Bash 가 통째로 막히고,
        # 셸이 막힌 세션은 복구 수단이 없다.
        print(f"[BASH GATE] 훅 페이로드 파싱 실패({exc.__class__.__name__}) — 셸 계약 검사가 쉬고 있다. 훅을 점검하라.",
              file=sys.stderr)
        sys.exit(1)

    command = (payload.get("tool_input") or {}).get("command") or ""

    targets = blocked_targets(command)
    if targets:
        print(
            "[BASH GATE] 셸로 소스 파일을 쓰려 한다 — " + " · ".join(targets) + ".\n"
            "Edit/Write 툴로 하라. Bash 리다이렉트는 작성 시점 게이트를 우회한다.\n"
            "임시 산출물이면 스크래치패드 경로로 내보내라(레포 밖은 검사하지 않는다).",
            file=sys.stderr,
        )
        sys.exit(2)

    verdict = piped_verdict(command)
    if verdict:
        print(
            f"[BASH GATE] `{verdict}` 뒤에 파이프·체인이 붙었다 — 판정의 exit code 가 사라진다.\n"
            "판정 명령을 단독 실행하고, merge 는 성공을 확인한 다음 호출로 분리하라.",
            file=sys.stderr,
        )
        sys.exit(2)

    mutation = shared_tree_mutation(command)
    if mutation:
        print(
            f"[BASH GATE] 병렬 체제의 공유 메인 체크아웃에서 `{mutation}` — 구현·커밋은 자기 worktree 에서만 한다.\n"
            "EnterWorktree 로 격리하거나, 이미 판 worktree 면 `git -C <worktree경로>` 로 호출하라.\n"
            "(정본: EDITING.md worktree 병렬 프로토콜)",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()

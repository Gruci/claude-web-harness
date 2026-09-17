"""훅 stdin 리더와 git 조회 — EOF에 의존하지 않는다.

git 헬퍼가 여기 있는 이유는 두 Stop 훅이 같은 조회를 하기 때문이다. 훅마다 따로 두면
기본 브랜치 감지 같은 판정이 두 벌이 되고, 한쪽만 고치는 순간 두 훅의 판정이 갈린다.


json.load(sys.stdin)은 stdin을 EOF까지 읽는다: CC가 페이로드를 준 뒤 파이프를 닫아준다는
가정이다. macOS/Linux와 EOF를 보내는 이벤트(Stop·PreToolUse·PostToolUse·SubagentStop)에선
문제없지만, Windows CC의 UserPromptSubmit stdin엔 EOF가 안 온다 — 그 읽기가 매달리다 훅
타임아웃으로 강제종료된다(output discarded). read1은 데이터가 있으면 즉시 반환하므로, 완결된
JSON 객체가 파싱되는 즉시 멈춰 EOF를 기다리지 않는다. EOF를 보내는 이벤트에서도 동일 동작.

바이트를 utf-8로 명시 디코드한다 — json.load(sys.stdin)은 Windows에서 stdin을 cp949로 읽어
한글 페이로드(프롬프트·경로)를 깨뜨릴 수 있었다.

파싱 실패 시 예외를 던진다. 훅마다 fail-open(exit 0)과 fail-closed(exit 2) 정책이 달라
정책 판단은 호출자 몫이다 — 헬퍼가 실패를 삼키면 fail-closed 훅이 무력화된다.
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_CHUNK = 65536
_ROOT = Path(__file__).resolve().parents[2]
_GIT_TIMEOUT_SEC = 10


def git_output(*args: str) -> str | None:
    """git 표준출력. 실패(비정상 종료·예외)면 None — 판정을 건너뛰라는 신호다."""
    try:
        done = subprocess.run(["git", *args], cwd=str(_ROOT), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=_GIT_TIMEOUT_SEC)
    except Exception:
        return None
    return done.stdout if done.returncode == 0 else None


def board_dir() -> Path:
    """공유 체크아웃의 과업 보드 `.claude/workboard/`. git 조회 실패 시 자기 트리로 폴백한다.

    훅 파일은 worktree 마다 복제되므로 `parents[2] / ".claude/workboard"` 로 잡으면 보드가
    세션 수만큼 갈라진다 — 보드를 git 밖으로 꺼낸 이유(같은 머신의 파일시스템이 공유 채널이다)
    자체가 무너진다. `git rev-parse --git-common-dir` 은 worktree 안에서도 **메인 `.git`** 을
    가리키고, 그 부모가 공유 체크아웃 루트다.

    폴백이 안전한 방향인 이유: 보드를 못 찾으면 '열린 과업 없음'으로 읽혀 잔존 검사가 돌고
    겹침 경고가 안 뜬다 — 둘 다 세션을 막지 않는다(경고·통과 계열).
    """
    common = git_output("rev-parse", "--git-common-dir")
    if not common or not common.strip():
        return _ROOT / ".claude" / "workboard"
    # 메인 체크아웃에서는 `.git` 처럼 상대경로가 온다 — git_output 의 cwd(_ROOT) 기준으로 푼다.
    found = Path(common.strip())
    if not found.is_absolute():
        found = _ROOT / found
    return found.resolve().parent / ".claude" / "workboard"


def default_branch() -> str | None:
    """원격 기본 브랜치 이름. `origin/HEAD` → 실패 시 main·master 실물 순 폴백.

    main 하드코딩은 이식성을 깬다 — master 레포에서 판정이 통째로 조용히 꺼진다.
    """
    head = git_output("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head and head.strip():
        return head.strip().rsplit("/", 1)[-1]
    for name in ("main", "master"):
        if git_output("show-ref", "--verify", "--quiet", f"refs/remotes/origin/{name}") is not None:
            return name
    return None


def read_hook_payload() -> dict[str, Any]:
    """stdin의 훅 페이로드(JSON 객체 1건)를 EOF 대기 없이 읽어 반환한다.

    비어 있거나 JSON 객체로 완결되지 않으면 예외(JSONDecodeError·ValueError)를 던진다.
    """
    decoder = json.JSONDecoder()
    buf = ""
    stream = sys.stdin.buffer
    while True:
        chunk = stream.read1(_CHUNK)
        if not chunk:  # 진짜 EOF — 아래에서 마지막으로 한 번 파싱 시도
            break
        buf += chunk.decode("utf-8", "replace")
        try:
            obj, _ = decoder.raw_decode(buf.lstrip())
        except json.JSONDecodeError:
            continue  # 객체가 아직 안 완성됨 — 더 읽는다
        return _as_object(obj)
    return _as_object(decoder.raw_decode(buf.lstrip())[0])


def _as_object(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("hook payload is not a JSON object")
    return obj

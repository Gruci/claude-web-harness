"""PreToolUse(Workflow) 훅 — 워크플로우 스크립트의 `agent()` 에 model 미지정을 차단.

`agent()` 에 model 을 안 주면 **메인 루프 모델을 상속한다.** 툴 문서는 그게 기본이라고 하는데,
그 말이 맞는 것은 메인이 Opus 일 때뿐이다. 메인이 Fable 이면 워커 전원이 Fable 단가에 더해
**Fable 전용 거부 정책까지 함께 상속한다.**

원류 실사고(2026-08-21): 15트랙 감사에서 1차 실행 28개가 전부 Fable 로 떴고, 재실행분 20개 중
11개가 safeguards 거부로 죽었다. 같은 재실행의 Opus 3개는 0건이다. 거부는 result 행을 안 남겨
`pipeline()` 이 영원히 기다렸고, 그 사이 cache_read 248M 이 나갔다.

## 왜 산문이 아니라 게이트인가

이 규칙은 이미 `CLAUDE.md` 모델 라우팅에 산문으로 있었다. 있는데도 사고가 났다 — 검사 가능한
규칙을 산문으로 단속하는 것 자체가 실패 메커니즘이라는 일관성 게이트 ①의 실증이다.
게다가 산문 문구는 「팬아웃 스테이지」로 좁았고, 사고는 그 밖(구현·검수)에서 났다. 여기는
**모든 `agent()` 호출**을 본다.

## 판정 — 자리로 가른다

`agent(` 를 찾을 때 **주석과 문자열 안은 세지 않는다.** 워크플로우 스크립트는 프롬프트를
문자열로 들고 다니고 거기 "agent(" 가 들어가는 것이 정상이다. 그걸 호출로 세면 정상 스크립트가
막힌다 — 이 하네스가 `outbound_link` 와 `worktree_add_target` 에서 두 번 겪은 부류라 처음부터
자리로 가른다.

호출 범위는 괄호 깊이로 잡는다. 정규식으로 같은 줄만 보면 여러 줄로 쓴 호출을 통째로 놓친다.

## 단계

위반은 **차단**(exit 2)이다 — 스크립트 본문에 `model:` 이 실제로 없다는 직접 관측이다.
판정 불능(본문 없음·파일 못 읽음·괄호 안 닫힘)은 **비차단 경고**(exit 1)다. 스크립트를 못 읽는
것은 규칙 위반이 아니라 훅 오작동이고, 그것으로 Workflow 를 막으면 고칠 수단이 사라진다.
정본은 `HARNESS.md` 「단계」다.
"""
import re
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
sys.path.insert(0, str(ROOT))

# 차단할 때마다 관찰을 남긴다 — 회고가 읽을 데이터다. 기록이 실패해도 차단은 계속돼야 한다.
try:
    from kernel.trace import record
except Exception:
    def record(*_args: object, **_kwargs: object) -> None: ...

CALL = re.compile(r"\bagent\s*\(")
MODEL_KEY = re.compile(r"\bmodel\s*:")
# `...opts` 나 `{...spec}` 처럼 통째로 넘기는 형태는 여기서 판정할 수 없다 — 전개 대상이
# 런타임 값이라 본문에 model 이 안 보인다. 정적 검사의 한계라 통과시킨다(오탐 0 우선).
SPREAD = re.compile(r"\.\.\.\s*\w+")


def strip_noncode(source: str) -> str:
    """주석과 문자열 리터럴을 같은 길이의 공백으로 지운다.

    길이를 보존하는 이유는 줄번호와 괄호 위치가 원본과 같아야 하기 때문이다. 지우지 않고
    검사하면 프롬프트 문자열 안의 `agent(` 를 호출로 세어 정상 스크립트를 막는다.
    """
    out = list(source)
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        nxt = source[index + 1] if index + 1 < length else ""
        if char == "/" and nxt == "/":                       # 줄 주석
            while index < length and source[index] != "\n":
                out[index] = " "
                index += 1
        elif char == "/" and nxt == "*":                     # 블록 주석
            out[index] = out[index + 1] = " "
            index += 2
            while index < length and not (source[index] == "*" and
                                          index + 1 < length and source[index + 1] == "/"):
                if source[index] != "\n":
                    out[index] = " "
                index += 1
            index = min(index + 2, length)
        elif char in "\"'`":                                 # 문자열·템플릿 리터럴
            quote = char
            out[index] = " "
            index += 1
            while index < length and source[index] != quote:
                if source[index] == "\\":
                    out[index] = " "
                    index += 1
                if index < length:
                    if source[index] != "\n":
                        out[index] = " "
                    index += 1
            if index < length:
                out[index] = " "
                index += 1
        else:
            index += 1
    return "".join(out)


def agent_calls(source: str) -> list[tuple[int, str]]:
    """(줄번호, 호출 인자 본문) — `agent(` 부터 짝이 맞는 닫는 괄호까지.

    괄호 깊이로 범위를 잡아 여러 줄 호출을 통째로 담는다. 짝이 안 맞으면 그 호출은 건너뛴다 —
    판정 불능이지 위반이 아니다.
    """
    code = strip_noncode(source)
    found: list[tuple[int, str]] = []
    for match in CALL.finditer(code):
        start = match.end()
        depth = 1
        index = start
        while index < len(code) and depth:
            if code[index] == "(":
                depth += 1
            elif code[index] == ")":
                depth -= 1
            index += 1
        if depth:
            continue                                  # 안 닫힘 — 판정 불능
        found.append((code.count("\n", 0, match.start()) + 1, code[start:index - 1]))
    return found


def missing_model(source: str) -> list[int]:
    """model 을 안 준 `agent()` 호출의 줄번호."""
    return [line for line, body in agent_calls(source)
            if not MODEL_KEY.search(body) and not SPREAD.search(body)]


def script_source(tool_input: dict) -> str | None:
    """검사할 스크립트 본문. 인라인 우선, 없으면 `scriptPath` 파일. 둘 다 없으면 None.

    None 은 등재된 워크플로우를 이름으로 부르는 경우다 — 본문이 이 호출에 없으니 검사할 것도 없다.
    """
    inline = tool_input.get("script")
    if isinstance(inline, str) and inline.strip():
        return inline
    raw_path = tool_input.get("scriptPath")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / raw_path
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def main() -> None:
    try:
        payload = read_hook_payload()
    except Exception as exc:
        print(f"[WORKFLOW GATE] 훅 페이로드 파싱 실패({exc.__class__.__name__}) — "
              f"model 검사가 쉬고 있다. 훅을 점검하라.", file=sys.stderr)
        sys.exit(1)

    source = script_source(payload.get("tool_input") or {})
    if source is None:
        sys.exit(0)

    lines = missing_model(source)
    if not lines:
        sys.exit(0)

    sid = str(payload.get("session_id") or "")
    record("check_workflow_script", "workflow_model", sid=sid,
           msg=f"model 미지정 agent() {len(lines)}건 — 줄 {lines}")
    print(
        f"[WORKFLOW GATE] model 을 안 준 `agent()` 호출 {len(lines)}건 — "
        f"줄 {', '.join(str(n) for n in lines)}.\n"
        "미지정은 메인 루프 모델을 상속한다. 메인이 Fable 이면 워커 전원이 Fable 단가에\n"
        "Fable 전용 거부 정책까지 함께 상속하고, 거부는 result 행을 안 남겨 pipeline 이 영원히 기다린다.\n"
        "구현·검수는 `model: 'opus'`, 기계적 팬아웃은 `model: 'sonnet'` 을 명시하라.\n"
        "(정본: .claude/agents/orchestrator.md §4-1 Workflow 스폰 계약)",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()

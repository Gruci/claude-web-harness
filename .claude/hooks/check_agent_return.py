"""SubagentStop hook — 서브에이전트 비만 반환 차단 (컨텍스트 가드 ②).

서브에이전트의 최종 반환문은 그대로 메인 루프 컨텍스트에 얹혀 남은 세션 내내 재전송된다.
반환이 MAX_RETURN_CHARS를 넘으면 exit 2로 종료를 막고, 에이전트가 stderr 피드백을 받아
"요약 + detail_path(파일)" 형태로 다시 쓰게 강제한다.

상한 2만자의 근거: 과도한 손실 압축은 오히려 재조사를 유발해 총비용이 커진다. 상세 반환은
허용하되 파일 전문 덤프는 막는 선이다.

무한루프 방지: stop_hook_active면 통과. 페이로드에 last_assistant_message가 없으면
통과시키고 그 사실만 알린다(fail-open). 트랜스크립트에서 마지막 assistant 메시지를
추정하던 폴백은 삭제했다 — SubagentStop이 서브에이전트 트랜스크립트를 주는지 메인을
주는지 확정되지 않아, 메인 루프 응답을 서브 반환으로 오인해 오차단할 수 있었다.
전 게이트 통틀어 "확실한 위반만 잡고 오탐 0" 원칙이 우선한다.
"""
import json
import sys
from pathlib import Path

try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

MAX_RETURN_CHARS = 20_000

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# 차단할 때마다 관찰을 남긴다 — 회고가 읽을 데이터다. 기록이 실패해도 차단은 계속돼야 한다.
try:
    from kernel.trace import record
except Exception:
    def record(*_args: object, **_kwargs: object) -> None: ...


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if payload.get("stop_hook_active"):
        sys.exit(0)

    sid = str(payload.get("session_id") or "")
    last_message = payload.get("last_assistant_message")
    if not isinstance(last_message, str) or not last_message:
        # 차단은 아니지만 게이트가 조용히 안 도는 상태다 — §15 가 경계하는 바로 그 모양이라 남긴다
        record("check_agent_return", "gate_error", sid=sid,
               msg="페이로드에 last_assistant_message 없음 — 반환 검사가 안 돌고 있다")
        print("[RETURN DIET] 페이로드에 last_assistant_message 없음 — 이번 반환은 미검사. "
              "이 줄이 뜨면 payload 실물을 확인해 게이트를 다시 붙여라.", file=sys.stderr)
        sys.exit(0)

    return_length = len(last_message)
    if return_length <= MAX_RETURN_CHARS:
        sys.exit(0)

    record("check_agent_return", "return_diet", sid=sid,
           msg=f"반환 {return_length}자 — 상한 {MAX_RETURN_CHARS}자 초과")
    print(
        f"[RETURN DIET] 최종 반환이 {return_length:,}자 — 상한 {MAX_RETURN_CHARS:,}자 초과. "
        f"이 반환은 통째로 메인 루프 컨텍스트에 얹혀 남은 세션 내내 재과금된다.\n"
        f"  상세는 파일로 저장하고 최종 반환은 다음 형식으로 다시 써라:\n"
        f"  · summary: 핵심 결론 1,500토큰 이하\n"
        f"  · 근거 포인터: file:line 형식\n"
        f"  · detail_path: 방금 저장한 상세 파일 경로\n"
        f"  (정본: CLAUDE.md 모델 라우팅 — 다이제스트 예산 계약)",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()

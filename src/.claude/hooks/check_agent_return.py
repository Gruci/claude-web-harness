"""SubagentStop hook — 서브에이전트 비만 반환 차단 (컨텍스트 가드 ②).

서브에이전트의 최종 반환문은 그대로 메인 루프 컨텍스트에 얹혀 남은 세션 내내 재전송된다.
반환이 MAX_RETURN_CHARS 를 넘으면 exit 2 로 종료를 막고, 에이전트가 stderr 피드백을 받아
"요약 + detail_path(파일)" 형태로 다시 쓰게 강제한다.

2026-07-28 Opus 5 전환 — 상한 8,000→20,000자. 구 값은 Fable 단가 방어치였고, 과도한 손실
압축이 오히려 재조사를 유발해 총비용이 컸다. 2만자는 상세 반환을 허용하되 파일 전문 덤프는 막는 선.

무한루프 방지: stop_hook_active 면 통과. 반환문을 못 찾으면 통과(fail-open —
페이로드 스키마가 버전에 따라 다를 수 있어 전 에이전트 차단이 더 위험).
"""
import json
import sys
from pathlib import Path

try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

MAX_RETURN_CHARS = 20_000


def _text_length_of_message(message_object: dict) -> int:
    """assistant 메시지 객체의 text 블록 총 길이. content 가 str/list 양쪽 다 대응."""
    content = message_object.get("content")
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                total += len(block.get("text") or "")
        return total
    return 0


def _last_assistant_length_from_transcript(transcript_path: str) -> int | None:
    """transcript .jsonl 에서 마지막 assistant 메시지의 text 길이. 실패 시 None."""
    path = Path(transcript_path)
    if not path.is_file():
        return None
    last_length: int | None = None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            message_object = entry.get("message") if isinstance(entry, dict) else None
            if not isinstance(message_object, dict):
                continue
            if entry.get("type") == "assistant" or message_object.get("role") == "assistant":
                length = _text_length_of_message(message_object)
                if length > 0:
                    last_length = length
    except Exception:
        return None
    return last_length


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if payload.get("stop_hook_active"):
        sys.exit(0)

    return_length: int | None = None
    last_message = payload.get("last_assistant_message")
    if isinstance(last_message, str) and last_message:
        return_length = len(last_message)
    elif payload.get("transcript_path"):
        return_length = _last_assistant_length_from_transcript(str(payload["transcript_path"]))

    if return_length is None or return_length <= MAX_RETURN_CHARS:
        sys.exit(0)

    print(
        f"[RETURN DIET] 최종 반환이 {return_length:,}자 — 상한 {MAX_RETURN_CHARS:,}자 초과. "
        f"이 반환은 통째로 메인 루프 컨텍스트에 얹혀 남은 세션 내내 재과금된다.\n"
        f"  상세 내용은 파일로 저장하고(detail_path), 최종 반환은 다음 형식으로 다시 써라:\n"
        f"  · summary: 핵심 결론 ≤1,500토큰\n"
        f"  · 근거 포인터: file:line 형식\n"
        f"  · detail_path: 방금 저장한 상세 파일 경로\n"
        f"  (정본: CLAUDE.md 'Fable 컨텍스트 다이어트' — 다이제스트 예산 계약)",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()

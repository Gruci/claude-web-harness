"""UserPromptSubmit hook — 세션 히스토리 비대 경고 (컨텍스트 가드 ③).

세션 누적 히스토리는 매 턴 전체 재전송된다(캐시 히트여도 유지비).
transcript 파일 크기를 프록시로 삼아, 임계 초과 시 사용자에게 systemMessage 경고 +
모델 컨텍스트에 /clear 권고를 주입한다. 차단은 하지 않는다(세션 분리는 사용자 결정).

2026-07-28 Opus 5 전환 — 5MB→15MB. transcript 는 실컨텍스트의 3~5배 프록시라
15MB ≈ 30~50만 토큰 = 1M 의 1/3~1/2 지점. 경고 전용이라 보수적으로 상향.

# lazy: transcript 파일 크기는 실제 컨텍스트 토큰의 거친 프록시(컴팩션 후 과대평가) —
# 정밀해지려면 컨텍스트 API 노출 필요, 현재는 경고 용도로 충분.
"""
import json
import sys
from pathlib import Path

WARN_BYTES = 15_000_000


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    transcript_path = payload.get("transcript_path") or ""
    path = Path(transcript_path)
    if not transcript_path or not path.is_file():
        sys.exit(0)

    size_bytes = path.stat().st_size
    if size_bytes < WARN_BYTES:
        sys.exit(0)

    size_mb = size_bytes / 1_000_000
    warning = (
        f"세션 히스토리 {size_mb:.0f}MB 누적 — 매 턴 전체가 재전송되는 중. "
        f"진행 중 태스크가 완결됐다면 /clear 로 세션을 분리하라 (CLAUDE.md '모델 라우팅')."
    )
    print(
        json.dumps(
            {
                "systemMessage": f"⚠️ {warning}",
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": f"[CONTEXT GROWTH] {warning}",
                },
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

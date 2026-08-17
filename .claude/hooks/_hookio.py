"""훅 stdin 리더 — EOF에 의존하지 않는다.

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
import sys
from typing import Any

_CHUNK = 65536


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

"""PreToolUse(Read) hook — 대용량 파일 통읽기 기계 차단 (컨텍스트 가드 ①).

배경(원본 프로젝트 실사고): 95KB 워크플로우 결과와 60KB 다이제스트를 메인 루프가 통으로 Read →
그 뒤 모든 턴에서 재전송·재과금. "요약만 받는다"는 산문 규칙은 드리프트하므로 훅으로 강제한다.

바이트가 아니라 토큰 추정으로 잰다. 한글은 UTF-8 3바이트/자라 바이트를 쓰면 3배 과대평가되고,
그러면 라우팅표가 "읽어라"고 지시하는 정본 MD를 훅이 막는 자기모순이 생긴다.

판정 (메인/서브 구분 없이 동작 — 훅은 서브에이전트 툴 호출에도 발화한다):
  - 추정 토큰이 LIMIT_TOKENS 초과 && 분할 파라미터(limit ≤ CHUNK_LIMIT_LINES) 없음 → exit 2 차단
  - 이미지·바이너리는 예외 (비전 에이전트가 통으로 읽어야 함 — 기계 판별 불가)
  - PDF는 Read 자체가 pages 분할을 강제하므로 예외
"""
import json
import sys
from pathlib import Path

try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

LIMIT_TOKENS = 16_000
CHUNK_LIMIT_LINES = 500
EXEMPT_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".pdf"}


def _estimate_tokens(path: Path) -> int:
    """ASCII 4자당 1토큰, 비ASCII(한글 등) 1자당 1토큰 — ±20% 근사면 차단 판정에 충분."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return 0
    ascii_count = sum(1 for ch in text if ord(ch) < 128)
    return ascii_count // 4 + (len(text) - ascii_count)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        sys.exit(0)

    path = Path(file_path)
    if not path.is_file() or path.suffix.lower() in EXEMPT_SUFFIXES:
        sys.exit(0)

    estimated = _estimate_tokens(path)
    if estimated <= LIMIT_TOKENS:
        sys.exit(0)

    limit_lines = tool_input.get("limit")
    if isinstance(limit_lines, (int, float)) and limit_lines <= CHUNK_LIMIT_LINES:
        sys.exit(0)

    print(
        f"[CONTEXT GUARD] {path.name} 약 {estimated:,}토큰 — 통읽기 차단 (상한 {LIMIT_TOKENS:,}).\n"
        f"  · offset/limit({CHUNK_LIMIT_LINES}줄 이하)으로 필요한 부분만 나눠 읽어라.\n"
        f"  · 수십 파일 독립 스캔이면 Sonnet 에이전트 팬아웃이 정답.\n"
        f"  (정본: CLAUDE.md 모델 라우팅 — 한 번 읽은 대용량은 남은 세션 내내 매 턴 재전송된다)",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()

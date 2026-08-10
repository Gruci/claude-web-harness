"""Stop hook — EDITING.md 과업 보드에 '이 세션'의 잠금이 남아있으면 종료를 막는다.

멀티 세션 대응: 구버전은 잠금 행 전체를 차단해서, 다른 세션이 작업 중이면 이 세션이 영원히
종료 못 하는 데드락이 났다. 훅이 세션을 식별하지 못하는 게 원인이었다.

관례(정본: CLAUDE.md 편집 잠금) — 보드 행에 `#sid:<세션ID 앞8자>` 태그를 붙인다. 판정:
  - 내 sid 태그 행 → 차단(exit 2). 내가 해제 안 한 잠금이다.
  - 다른 sid 태그 행이나 태그 없는 행 → 다른 세션의 활성 잠금일 수 있으므로 차단하지 않는다.
  - stdin 페이로드에서 session_id 를 못 읽으면 fail-closed로 전 행 차단(구동작 유지).
"""
import json
import re
import sys
from pathlib import Path

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

EDITING_MD = Path(__file__).resolve().parents[2] / "EDITING.md"
HEADER_PAIRS = (("세션 ID", "편집 파일"), ("과업", "스코프"))


def _my_sid8() -> str | None:
    """Stop 훅 stdin JSON의 session_id 앞 8자. 파싱 실패 시 None(fail-closed)."""
    try:
        payload = json.load(sys.stdin)
        session_id = str(payload.get("session_id") or "")
        return session_id[:8] if len(session_id) >= 8 else None
    except Exception:
        return None


def _active_edit_rows(text: str) -> list[str]:
    """과업 보드의 데이터 행만 추출 (주석 블록·헤더·구분선 제외)."""
    in_active = False
    in_comment = False
    data_rows: list[str] = []
    for line in text.splitlines():
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line:
            if "-->" not in line:
                in_comment = True
            continue
        # 섹션 제목에 이모지·한글 부연이 붙어도 매칭되도록 substring 검사
        if line.startswith("##") and "Active Edits" in line:
            in_active = True
            continue
        if in_active:
            if line.startswith("##"):
                break
            stripped = line.strip()
            if stripped.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", stripped):
                if any(a in stripped and b in stripped for a, b in HEADER_PAIRS):
                    continue
                data_rows.append(stripped)
    return data_rows


def main() -> None:
    if not EDITING_MD.exists():
        sys.exit(0)

    rows = _active_edit_rows(EDITING_MD.read_text(encoding="utf-8"))
    if not rows:
        sys.exit(0)

    sid8 = _my_sid8()
    blocking = rows if sid8 is None else [r for r in rows if f"#sid:{sid8}" in r]

    if blocking:
        # Stop 훅 차단 사유는 stderr로 내보내야 Claude에게 전달된다(stdout은 무시된다).
        reason = "이 세션의" if sid8 else "(세션 식별 불가 — 전 행 검사)"
        print(f"[EDITING LOCK] {reason} 과업 보드 행 {len(blocking)}건이 아직 해제되지 않았습니다.",
              file=sys.stderr)
        for row in blocking:
            print(f"  {row}", file=sys.stderr)
        print("완료 보고와 함께 이 세션의 행을 제거한 뒤 종료하세요.", file=sys.stderr)
        print("⚠️ 다른 세션의 행은 절대 지우지 말 것 — 그 세션의 작업이 진행 중이다.", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()

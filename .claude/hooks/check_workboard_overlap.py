"""PreToolUse(Edit|Write) hook — 남이 잡은 곳을 건드리면 알린다.

`check_editing_lock.py` 는 이름과 달리 **Stop 훅**이고 하는 일은 "머지 끝난 내 과업이 남았나"다.
즉 **편집을 시작할 때** 남이 잡은 곳을 건드리는지 알려주는 장치가 하나도 없었다. 겹침은 사람이
보드를 눈으로 읽어야만 발견됐다.

worktree 는 **파일 충돌**만 막는다. 두 세션이 서로 다른 파일로 같은 기능을 각자 만들면 git 은
조용히 둘 다 머지하고, 결과는 앞뒤가 안 맞는 화면이다(원류 MIS 2026-09-16 실측: 한쪽이
클래스명을 바꾸자 다른 쪽 CSS 가 통째로 무효가 됐다). 그 겹침을 착수 시점에 드러내는 것이
이 훅이다. 판정은 `kernel/workboard.py` 가 단일 정본이고 Codex 진입점(`kernel/hook.py`)도
같은 판정을 저장 직후에 돌린다 — Codex 에는 편집 전 이벤트가 없다.

## 경고지 차단이 아니다

판정 근거가 사람이 적은 `손대는 곳` 글로브라 넓게·낡게 적히기 쉽다. 차단으로 걸면 오탐 한 번에
세션이 멈춘다 — `HARNESS.md` 「단계」의 추론 계열 규칙과 같은 자리다.

## 내 과업 판정은 파일명이 아니라 `#sid:` 태그다

파일명(= 범위 이름)으로 가르면 범위 이름을 바꾼 순간 자기 과업을 남의 것으로 경고한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import read_hook_payload  # noqa: E402

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ⚠️ ROOT 는 **자기 worktree 루트**다(보드와 다른 자리). 편집 대상 파일을 상대경로로 바꿔
#    글로브와 맞대는 용도라, 공유 체크아웃으로 잡으면 worktree 안 파일이 전부 `relative_to`
#    에서 벗어나 경고가 통째로 죽는다.
ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT))

# 판정 정본은 kernel/workboard.py — 커널을 못 읽으면 fail-open: 경고 훅이 편집을 막지 않는다.
try:
    from kernel.workboard import board_dir, overlaps as _overlaps, touch_globs  # noqa: E402,F401
except Exception:
    sys.exit(0)

# 보드는 **공유 체크아웃 한 곳**이다 — 훅 파일이 worktree 마다 복제되므로 자기 트리로
# 잡으면 보드가 세션 수만큼 갈라진다(`kernel.workboard.board_dir` 헤더).
BOARD_DIR = board_dir()

# 알릴 때마다 관찰을 남긴다 — 회고가 읽을 데이터다. 기록이 실패해도 판정은 계속돼야 한다.
try:
    from kernel.trace import record
except Exception:
    def record(*_args: object, **_kwargs: object) -> None: ...

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def overlaps(target: Path, sid8: str) -> list[str]:
    """내 것이 아닌 과업의 글로브에 걸리는가 — 판정은 커널, 보드·루트 자리만 이 훅이 쥔다."""
    return _overlaps(target, sid8, BOARD_DIR, ROOT)


def _target(payload: dict) -> Path | None:
    """Edit·Write 가 건드리는 파일. 다른 도구면 None."""
    if payload.get("tool_name") not in EDIT_TOOLS:
        return None
    raw = (payload.get("tool_input") or {}).get("file_path")
    return Path(raw) if raw else None


def main() -> None:
    if not BOARD_DIR.is_dir():
        sys.exit(0)
    try:
        payload = read_hook_payload()
    except Exception:
        sys.exit(0)                       # 판정 불능이면 조용히 통과 — 경고 훅이 편집을 막지 않는다

    target = _target(payload)
    if target is None:
        sys.exit(0)
    sid8 = str(payload.get("session_id") or "")[:8]
    hits = overlaps(target, sid8)
    if not hits:
        sys.exit(0)

    record("check_workboard_overlap", "workboard_overlap", sid=sid8, msg=f"{len(hits)}건 {target.name}")
    print(f"[WORKBOARD] 다른 과업이 잡은 곳이다 — {target.name}", file=sys.stderr)
    for hit in hits:
        print(f"  {hit}", file=sys.stderr)
    print("같은 화면이면 그 세션에 합류하거나(항목 추가) 그 브랜치 위에서 쌓는다.", file=sys.stderr)
    print("겹치는 줄이 아니면 그대로 진행해도 된다 — 경고이지 차단이 아니다.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

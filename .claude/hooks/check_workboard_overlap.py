"""PreToolUse(Edit|Write) hook — 남이 잡은 곳을 건드리면 알린다.

`check_editing_lock.py` 는 이름과 달리 **Stop 훅**이고 하는 일은 "머지 끝난 내 과업이 남았나"다.
즉 **편집을 시작할 때** 남이 잡은 곳을 건드리는지 알려주는 장치가 하나도 없었다. 겹침은 사람이
보드를 눈으로 읽어야만 발견됐다.

worktree 는 **파일 충돌**만 막는다. 두 세션이 서로 다른 파일로 같은 기능을 각자 만들면 git 은
조용히 둘 다 머지하고, 결과는 앞뒤가 안 맞는 화면이다(원류 MIS 2026-09-16 실측: 한쪽이
클래스명을 바꾸자 다른 쪽 CSS 가 통째로 무효가 됐다). 그 겹침을 착수 시점에 드러내는 것이
이 훅이다.

## 경고지 차단이 아니다

판정 근거가 사람이 적은 `손대는 곳` 글로브라 넓게·낡게 적히기 쉽다. 차단으로 걸면 오탐 한 번에
세션이 멈춘다 — `HARNESS.md` 「단계」의 추론 계열 규칙과 같은 자리다.

## 내 과업 판정은 파일명이 아니라 `#sid:` 태그다

파일명(= 범위 이름)으로 가르면 범위 이름을 바꾼 순간 자기 과업을 남의 것으로 경고한다.
"""
import fnmatch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import board_dir, read_hook_payload  # noqa: E402

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 보드는 **공유 체크아웃 한 곳**이다 — 훅 파일이 worktree 마다 복제되므로 자기 트리로
# 잡으면 보드가 세션 수만큼 갈라진다(`_hookio.board_dir` 헤더).
BOARD_DIR = board_dir()
# ⚠️ ROOT 는 **자기 worktree 루트**다(보드와 다른 자리). 편집 대상 파일을 상대경로로 바꿔
#    글로브와 맞대는 용도라, 공유 체크아웃으로 잡으면 worktree 안 파일이 전부 `relative_to`
#    에서 벗어나 경고가 통째로 죽는다.
ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT))

# 알릴 때마다 관찰을 남긴다 — 회고가 읽을 데이터다. 기록이 실패해도 판정은 계속돼야 한다.
try:
    from kernel.trace import record
except Exception:
    def record(*_args: object, **_kwargs: object) -> None: ...

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def touch_globs(text: str) -> list[str]:
    """`손대는 곳:` 아래의 글로브 목록. 다음 필드(`- 이름:`)를 만나면 끝난다."""
    globs: list[str] = []
    collecting = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- 손대는 곳:"):
            collecting = True
            continue
        if collecting:
            # 두 칸 들여쓴 `- <glob>` 만 항목이다. 들여쓰기 없는 `- x:` 는 다음 필드다.
            if line.startswith("  - "):
                globs.append(stripped[2:].strip())
                continue
            if stripped.startswith("- "):
                break
    return globs


def overlaps(target: Path, sid8: str) -> list[str]:
    """내 것이 아닌 과업의 글로브에 걸리는가 — 걸리면 `범위 (글로브)` 목록."""
    try:
        rel = target.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return []                         # 레포 밖 파일(스크래치패드 등)은 대상이 아니다
    hits: list[str] = []
    for path in sorted(BOARD_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if sid8 and f"#sid:{sid8}" in text:
            continue                      # 내 과업
        for pattern in touch_globs(text):
            if fnmatch.fnmatch(rel, pattern) or rel.startswith(pattern.rstrip("*")):
                hits.append(f"{path.stem} ({pattern})")
                break
    return hits


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

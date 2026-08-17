"""Stop hook — docs/tasks/ 루트에 plan·research 가 남아있으면 세션 종료를 막는다.

`check_mockup_residue.py` 와 같은 계약이다. 루트에 남은 산출물은 다음 세션에게 "진행 중인
작업"으로 읽힌다. 실제로는 끝난 과업의 잔해라 그 오독이 리서치와 계획을 통째로 낭비시킨다.

`glob("*.md")` 는 루트만 훑어 `archive/`·`mockup/` 하위를 자동으로 제외한다 — archive 는
산출물의 목적지라 거기 있는 것은 잔존이 아니고, mockup 은 전용 훅의 관할이다.

## 진행 중에는 검사하지 않는다

plan 은 목업과 달리 **과업이 끝날 때까지 루트에 있는 게 정상**이다(1~3단계 내내 참조된다).
파일 존재만으로 잔존을 판정하면 진행 중인 세션의 종료를 매 턴 막는다 — 원류 프로젝트의 첫
버전이 다른 세션의 진행 중 plan 3건을 잡았다. 그 상태에서 빠져나가는 유일한 길이 `wip_`
접두라, 접두가 기본값이 되고 게이트는 소음이 된다.

완료 신호는 파일이 아니라 **과업 보드**다. `EDITING.md` Active Edits 에 행이 하나라도 있으면
누군가 작업 중이므로 검사를 건너뛴다. 보드가 비었는데 루트에 산출물이 남아 있으면 그것이 잔존이다.

대가는 명시한다 — 다른 과업이 진행 중인 동안에는 끝난 과업의 잔해도 안 잡힌다. 미탐을 택한
이유는 오탐이 곧 종료 데드락이기 때문이다.

예외: `wip_` 접두는 차단하지 않는다. 보드가 빈 상태로 세션을 넘겨 이어지는 검토용 산출물이다.
"""
import sys
from pathlib import Path

# 보드 행 파싱은 `check_editing_lock.py` 가 정본이다 — 주석 블록·헤더 제외 규칙을 재구현하지 않는다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_editing_lock import _active_edit_rows  # noqa: E402

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TASK_DIR = Path(__file__).resolve().parents[2] / "docs" / "tasks"
EDITING_MD = Path(__file__).resolve().parents[2] / "EDITING.md"


def board_is_busy() -> bool:
    """과업 보드에 진행 중 행이 있는지. 읽지 못하면 True — 판정 불능일 때는 막지 않는다.

    `#sid:` 태그가 붙은 행만 센다 — 태그는 과업 등록의 필수 요소라 실제 행과 헤더·예시를
    가르는 정확한 신호다.
    """
    try:
        rows = _active_edit_rows(EDITING_MD.read_text(encoding="utf-8"))
    except OSError:
        return True
    return any("#sid:" in row for row in rows)


def residue() -> list[Path]:
    """루트에 남은 과업 산출물. 정렬은 출력 안정성 목적이다."""
    if not TASK_DIR.is_dir() or board_is_busy():
        return []
    return sorted(path for path in TASK_DIR.glob("*.md")
                  if path.is_file() and not path.name.startswith("wip_"))


def main() -> None:
    leftover = residue()
    if not leftover:
        sys.exit(0)

    # Stop 훅 차단 사유는 stderr 로 내보내야 Claude 에게 전달된다(stdout 은 무시됨).
    print(f"[TASK RESIDUE] docs/tasks/ 루트에 산출물 {len(leftover)}건이 남아있습니다.", file=sys.stderr)
    for path in leftover:
        print(f"  docs/tasks/{path.name}", file=sys.stderr)
    print("구현이 끝났으면 docs/tasks/archive/YYYY-MM-DD-{작업명}/ 으로 옮기세요.", file=sys.stderr)
    print("판단이 세션을 넘겨 이어지는 중이면 wip_ 접두를 붙입니다.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()

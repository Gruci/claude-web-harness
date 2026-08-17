"""Stop hook — docs/tasks/mockup/ 에 목업이 남아있으면 세션 종료를 막는다.

목업은 사용자에게 보여주고 판단을 받는 게 존재 이유다. 판단이 끝나면 갈 곳이 정해지는데,
그 시점이 "다음에"로 밀리면 죽은 시안이 쌓인다(원류 프로젝트 실태 4건).

행선지는 채택 여부가 가른다 — 채택분은 `docs/tasks/archive/<작업>/` 로 옮겨 plan·research 와
같은 자리에 남기고, 반려분은 지운다. 채택된 시안은 "왜 이 화면이 이렇게 생겼나"의 유일한
기록이라 archive 가 받아야 한다.

추적 여부를 보지 않고 디렉토리를 직접 스캔한다. 목업은 대개 untracked 라 `git ls-files`
기반 게이트로는 잡히지 않는다.

예외: `wip_` 접두 파일은 차단하지 않는다 — 판단이 세션을 넘겨 이어지는 검토 중 시안까지
막으면 세션 종료가 불가능해진다. 전역 스위치가 아니라 파일 단위 명시라, 접두 없는 잔존
(판단 끝난 시안 방치)은 여전히 잡힌다. 채택 확정 시 접두를 떼고 archive 로 옮긴다.
"""
import sys
from pathlib import Path

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

MOCKUP_DIR = Path(__file__).resolve().parents[2] / "docs" / "tasks" / "mockup"


def main() -> None:
    if not MOCKUP_DIR.is_dir():
        sys.exit(0)

    residue = sorted(p for p in MOCKUP_DIR.rglob("*")
                     if p.is_file() and not p.name.startswith("wip_"))
    if not residue:
        sys.exit(0)

    # Stop 훅 차단 사유는 stderr 로 내보내야 Claude 에게 전달된다(stdout 은 무시됨).
    print(f"[MOCKUP RESIDUE] docs/tasks/mockup/ 에 목업 {len(residue)}건이 남아있습니다.", file=sys.stderr)
    for path in residue:
        print(f"  {path.relative_to(MOCKUP_DIR.parents[2]).as_posix()}", file=sys.stderr)
    print("판단이 끝난 목업은 비우고 종료하세요 — 채택분은 docs/tasks/archive/<작업>/ 로 옮기고", file=sys.stderr)
    print("반려분은 지웁니다. 검토가 세션을 넘겨 이어지면 wip_ 접두를 붙입니다.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()

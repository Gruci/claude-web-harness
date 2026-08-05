"""Stop hook — 코딩규칙 정적검사(static_check.py) 위반 시 세션 종료 차단.

세션이 끝나려 할 때 static_check.py 를 돌려 400줄·db/reads 클로저·db/reads 쓰기·축약어(net)
위반이 하나라도 있으면 exit 2 로 종료를 막고 위반 목록을 Claude 에게 돌려준다.
→ Claude 가 고친 뒤에야 세션이 끝나므로, 사용자에겐 '통과한 최종물'만 올라간다.

규칙을 MD 산문으로만 적어두면 세션마다 새로 들어온 Claude 가 제멋대로 짜서 드리프트한다.
이 훅이 검사가능한 규칙을 '강제 게이트'로 만든다. (정본 검사 로직: static_check.py)
"""
import subprocess
import sys
from pathlib import Path

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    checker = ROOT / "static_check.py"
    if not checker.exists():
        sys.exit(0)

    # 자식 stdout 을 UTF-8 로 강제(-X utf8). Windows 기본 cp949 출력 → 부모 utf-8 디코드 실패 방지.
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(checker)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        # Stop 훅 차단 사유는 stderr 로 내보내야 Claude 에게 전달된다(stdout 은 무시됨).
        print("[CODING RULES] static_check 위반 — 통과 전까지 세션 종료 불가. 아래를 고쳐라:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()

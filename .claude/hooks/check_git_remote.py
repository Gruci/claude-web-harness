"""Stop hook — GitHub 원격(origin) 미설정 시 세션 종료 차단.

초기 설정 ⓪은 git init이 아니라 GitHub 원격 연결까지다. 원격 없이 "완료"를
선언하면 커밋이 이 머신에만 남는다 — origin이 잡히기 전까지 종료를 막는다.
git 실행 실패도 통과가 아니라 차단(fail-closed).
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
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        print("[GIT REMOTE] git 실행 실패 — 원격 확인 불능 상태, 원인 확인 전 종료 불가 (fail-closed).", file=sys.stderr)
        sys.exit(2)

    if result.returncode != 0:
        # Stop 훅 차단 사유는 stderr로 내보내야 Claude에게 전달된다(stdout은 무시됨).
        print("[GIT REMOTE] GitHub 원격(origin)이 없다 — 초기 설정 ⓪ 미완료. 원격 연결 전까지 세션 종료 불가.", file=sys.stderr)
        print("`gh repo create <이름> --private --source . --push` 또는 `git remote add origin <url>` + `git push -u origin HEAD`까지 마쳐라.", file=sys.stderr)
        print("레포 URL·계정은 사용자만 아는 정보다 — 임의로 '완료' 선언하지 말고 사용자에게 GitHub 레포 주소를 요구하라(이 질문은 허락 구하기 금지의 예외).", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()

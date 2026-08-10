"""Stop hook — GitHub 원격(origin) 미설정 시 세션 종료 차단.

초기 설정 ⓪은 git init 이 아니라 GitHub 원격 연결까지다. 원격 없이 "완료"를 선언하면
커밋이 이 머신에만 남는다 — origin 이 잡히기 전까지 종료를 막는다. git 실행 실패도
통과가 아니라 차단(fail-closed).

**gh 가 인증돼 있으면 사용자에게 묻지 않는다.** 예전엔 "레포 주소는 사용자만 아는 정보"라며
매번 물었는데, 인증된 계정이 있으면 그건 사실이 아니다. 폴더 이름이 곧 레포 이름이고 계정은
이미 정해져 있다. 사용자만 아는 게 실제로 남는 경우(인증 없음·다른 계정에 만들고 싶음)에만
질문이 남는다.

**private 로만 만든다.** 공개 레포는 되돌리기 어려운 발행이라 사람이 정할 일이다.
"""
import re
import subprocess
import sys
from pathlib import Path

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]

# GitHub 레포 이름에 쓸 수 있는 문자만 남긴다
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _run(*args: str, timeout: int = 10) -> tuple[int, str]:
    try:
        done = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except Exception:
        return 1, ""
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def suggested_name() -> str:
    name = _UNSAFE.sub("-", ROOT.name).strip("-.")
    return name or "new-project"


def gh_account() -> str:
    """인증된 GitHub 계정. 없으면 빈 문자열."""
    code, out = _run("gh", "auth", "status")
    if code != 0:
        return ""
    found = re.search(r"account\s+(\S+)", out) or re.search(r"as\s+(\S+)", out)
    return found.group(1) if found else "(인증됨)"


def main() -> None:
    code, _out = _run("git", "remote", "get-url", "origin")
    if code == 0:
        sys.exit(0)

    # Stop 훅 차단 사유는 stderr 로 내보내야 모델에게 전달된다(stdout 은 무시된다).
    print("[GIT REMOTE] GitHub 원격(origin)이 없다 — 코드가 이 머신에만 있다. "
          "원격이 잡히기 전까지 세션 종료 불가.", file=sys.stderr)

    account = gh_account()
    if account:
        print(f"gh 가 {account} 로 인증돼 있다. **사용자에게 묻지 말고** 지금 만들어라:",
              file=sys.stderr)
        print(f"    gh repo create {suggested_name()} --private --source . --push",
              file=sys.stderr)
        print("이름이 마음에 안 들면 바꿔도 된다. 다만 --private 는 바꾸지 마라 — "
              "공개 발행은 되돌리기 어려워 사람이 정할 일이다. 사용자가 명시적으로 "
              "공개를 요청했을 때만 --public 을 쓴다.", file=sys.stderr)
        print("만든 뒤 실제로 푸시됐는지(exit 0 과 원격 URL) 확인하고 결과만 보고하라.",
              file=sys.stderr)
    else:
        print("gh 인증이 없어 계정을 알 수 없다 — 이건 사용자만 아는 정보다. "
              "`gh auth login` 을 안내하거나 레포 URL 을 요구하라 "
              "(이 질문은 허락 구하기 금지의 예외다).", file=sys.stderr)
        print("URL 을 받으면 `git remote add origin <url>` + `git push -u origin HEAD`.",
              file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()

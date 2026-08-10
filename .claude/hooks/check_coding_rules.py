"""Stop hook — 전 게이트 위반이 남아 있으면 세션 종료를 막는다.

세션이 끝나려 할 때 커널 러너를 돌려 위반이 하나라도 있으면 exit 2 로 종료를 막고 목록을
돌려준다. 고친 뒤에야 세션이 끝나므로 사용자에겐 '통과한 최종물'만 올라간다.

규칙을 MD 산문으로만 적어두면 세션마다 새로 들어온 모델이 제멋대로 짜서 드리프트한다.
이 훅이 검사 가능한 규칙을 부탁이 아니라 차단으로 만든다. (판정 정본: kernel/runner.py)
"""
import json
import subprocess
import sys
from pathlib import Path

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# 차단할 때마다 관찰을 남긴다 — 회고가 읽을 데이터다. 기록이 실패해도 차단은 계속돼야 한다.
try:
    from kernel.trace import record, record_runner_output
except Exception:
    def record(*_args: object, **_kwargs: object) -> None: ...
    def record_runner_output(*_args: object, **_kwargs: object) -> None: ...


def _sid() -> str:
    """stdin 페이로드의 session_id. 못 읽으면 빈 문자열 — 중복 제거만 느슨해진다."""
    try:
        return str(json.load(sys.stdin).get("session_id") or "")
    except Exception:
        return ""


def main() -> None:
    if not (ROOT / "kernel" / "runner.py").exists():
        sys.exit(0)
    sid = _sid()

    # 자식 stdout을 UTF-8로 강제(-X utf8). Windows 기본 cp949 출력 → 부모 utf-8 디코드 실패 방지.
    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "kernel.runner"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        record("check_coding_rules", "gate_error", sid=sid, msg="게이트 60초 타임아웃")
        print("[CODING RULES] 게이트가 60초 내 응답 없음 — 검사 불능 상태, 원인 확인 전 종료 불가.", file=sys.stderr)
        sys.exit(2)
    if result.returncode != 0:
        record_runner_output("check_coding_rules", sid, result.stdout)
        # Stop 훅 차단 사유는 stderr로 내보내야 Claude에게 전달된다(stdout은 무시됨).
        print("[CODING RULES] 게이트 위반 — 통과 전까지 세션 종료 불가. 아래를 고쳐라:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()

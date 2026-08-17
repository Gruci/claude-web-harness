"""PostToolUse hook — Edit/Write 직후 그 파일만 즉시 검사 (작성 시점 게이트).

Stop 훅(종료 시점 전체 검사)만으로는 "다 짜놓고 마지막에 몰아서 고치는" 잔 리팩터가 생긴다.
이 훅이 저장한 그 순간 위반을 돌려줘서 규칙 위반 코드가 애초에 쌓이지 않게 한다.
(전체 검사·종료 차단은 check_coding_rules.py 가 계속 담당 — 이중 게이트)
"""
import subprocess
import sys
from pathlib import Path

from _hookio import read_hook_payload

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
try:
    from kernel import profile as _profile
    LEGACY_PATHS = _profile.LEGACY_PATHS
except Exception:
    LEGACY_PATHS = ()

# 차단할 때마다 관찰을 남긴다 — 회고가 읽을 데이터다. 기록이 실패해도 차단은 계속돼야 한다.
try:
    from kernel.trace import record, record_runner_output
except Exception:
    def record(*_args: object, **_kwargs: object) -> None: ...
    def record_runner_output(*_args: object, **_kwargs: object) -> None: ...


def main() -> None:
    try:
        payload = read_hook_payload()
    except Exception as e:
        # fail-closed: 페이로드를 못 읽으면 검사 대상도 모른다 — 조용히 통과시키지 않는다
        record("check_file_rules", "gate_error", msg=f"페이로드 파싱 실패({e.__class__.__name__})")
        print(f"[WRITE-TIME GATE] 훅 페이로드 파싱 실패({e.__class__.__name__}) — 검사 불능. 원인 확인 전 통과 없음.", file=sys.stderr)
        sys.exit(2)

    sid = str(payload.get("session_id") or "")
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not file_path:
        sys.exit(0)
    p = Path(file_path)

    # 레거시 경로 편집 차단 — 규칙 정본은 프로파일 LEGACY_PATHS (기본 없음).
    # PostToolUse 라 쓰기 자체는 이미 일어났다 — 되돌리라는 즉시 피드백이 실효다.
    rel = str(p).replace("\\", "/")
    for fragment, suffix in LEGACY_PATHS:
        if fragment in rel and (suffix is None or p.suffix == suffix):
            record("check_file_rules", "legacy_path", sid=sid, file=rel,
                   msg=f"레거시 경로 편집 시도 — {fragment}")
            print(
                f"[WRITE-TIME GATE] 레거시 경로 편집 금지({fragment}) — 방금 변경을 되돌리고 "
                f"현행 경로로 구현하라. 이식·롤백 참고는 Read와 git 이력만.",
                file=sys.stderr,
            )
            sys.exit(2)

    if p.suffix not in (".py", ".ts", ".tsx", ".md"):
        sys.exit(0)

    if not (ROOT / "kernel" / "runner.py").exists():
        sys.exit(0)

    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "kernel.runner", "--file", str(p)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        record("check_file_rules", "gate_error", sid=sid, file=rel, msg="게이트 30초 타임아웃")
        print("[WRITE-TIME GATE] 게이트가 30초 내 응답 없음 — 검사 불능, 원인을 확인하라.", file=sys.stderr)
        sys.exit(2)
    if result.returncode != 0:
        record_runner_output("check_file_rules", sid, result.stdout)
        # exit 2 + stderr → Claude 에게 즉시 피드백 (작성한 그 턴 안에 수정)
        print(f"[WRITE-TIME GATE] 방금 저장한 파일이 코딩규칙 위반 — 지금 즉시 고쳐라 (Stop 훅에서도 차단됨):", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        # 검사기 자신이 크래시하면 트레이스백이 stderr로만 나온다. 이걸 안 실으면
        # "위반이라는데 목록이 비어 있는" 진단 불가 상태가 된다 (check_coding_rules와 동일 처리).
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()

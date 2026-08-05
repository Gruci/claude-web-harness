"""PostToolUse hook — Edit/Write 직후 해당 파일만 static_check 즉시 검사 (작성 시점 게이트).

Stop 훅(세션 종료 검사)만으로는 "다 짜놓고 마지막에 고치는" 잔 리팩토링이 생긴다.
이 훅이 파일을 저장한 그 순간 위반을 돌려줘서, 규칙 위반 코드가 애초에 쌓이지 않게 한다.
(전체 검사·종료 차단은 Stop 훅 check_coding_rules.py 가 계속 담당 — 이중 게이트.
 2026-07-20 harnes/claude-web-harness 템플릿에서 역이식.)
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


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        # fail-closed: 페이로드를 못 읽으면 검사 대상도 모른다 — 조용히 통과시키지 않는다
        print(f"[WRITE-TIME GATE] 훅 페이로드 파싱 실패({e.__class__.__name__}) — 검사 불능. 원인 확인 전 통과 없음.", file=sys.stderr)
        sys.exit(2)

    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not file_path:
        sys.exit(0)
    p = Path(file_path)

    # 레거시 UI 경로 편집 차단 — UI 신규·수정 결과물은 frontend/src/ React (CLAUDE.md 증거·경계 원칙 4).
    # web/static/*.css 는 React 가 현역 사용(base.css·admin.css·etf_ontology.css) — .js·템플릿만 금지.
    # lazy: PostToolUse 라 쓰기 자체는 이미 일어난다 — 되돌리라는 즉시 피드백이 실효. 사전 차단이
    # 필요해지면 PreToolUse 전용 훅으로 분리.
    rel = str(p).replace("\\", "/")
    legacy_dir = "/web/templates/" in rel or "/web/admin/templates/" in rel
    legacy_js = "/web/static/" in rel and p.suffix == ".js" and "/web/static/assets/" not in rel
    if legacy_dir or legacy_js:
        print(
            "[WRITE-TIME GATE] 레거시 UI 경로 편집 금지 — 방금 변경을 되돌리고 frontend/src/ React(.tsx)로 구현하라. "
            "이식·롤백 참고는 Read 와 git 이력만.",
            file=sys.stderr,
        )
        sys.exit(2)

    if p.suffix not in (".py", ".ts", ".tsx", ".md"):
        sys.exit(0)

    checker = ROOT / "static_check.py"
    if not checker.exists():
        sys.exit(0)

    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(checker), "--file", str(p)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("[WRITE-TIME GATE] static_check가 30초 내 응답 없음 — 검사 불능, 원인을 확인하라.", file=sys.stderr)
        sys.exit(2)
    if result.returncode != 0:
        # exit 2 + stderr → Claude 에게 즉시 피드백 (작성한 그 턴 안에 수정)
        print("[WRITE-TIME GATE] 방금 저장한 파일이 코딩규칙 위반 — 지금 즉시 고쳐라 (Stop 훅에서도 차단됨):", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()

"""setup_global_permissions.py — 글로벌 `~/.claude/settings.json` 에 하네스 권한을 병합한다.

  python -X utf8 setup_global_permissions.py

clone 직후 1회. 기존 설정(훅·플러그인 등)은 보존하고 permissions 만 병합한다.

⚠️ 이 스크립트는 **이 머신의 모든 프로젝트**에 대해 도구 승인 프롬프트를 끈다
   (`defaultMode: bypassPermissions`). 하네스의 차단은 훅과 게이트가 하고 승인 프롬프트는
   흐름만 끊는다는 판단이 근거다 — 그 판단에 동의할 때만 돌려라. 프로젝트 단위로만 켜려면
   이 파일 대신 그 프로젝트의 `.claude/settings.local.json` 에 같은 내용을 넣는다.
"""

from __future__ import annotations

import json
from pathlib import Path

ALLOW = [
    "Bash(*)", "PowerShell(*)", "Edit(*)", "Write(*)", "Read(*)",
    "Glob(*)", "Grep(*)", "WebFetch(*)", "WebSearch(*)",
    "Agent(*)", "Skill(*)", "NotebookEdit(*)",
    "TaskCreate(*)", "TaskUpdate(*)", "TaskGet(*)", "TaskList(*)",
    "TaskStop(*)", "TaskOutput(*)",
]


def main() -> int:
    path = Path.home() / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    settings: dict[str, object] = {}
    if path.exists():
        settings = json.loads(path.read_text(encoding="utf-8"))

    perm = settings.setdefault("permissions", {})
    if isinstance(perm, dict):
        perm["allow"] = sorted(set(perm.get("allow", [])) | set(ALLOW))
        perm["defaultMode"] = "bypassPermissions"
    settings["skipDangerousModePermissionPrompt"] = True

    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"글로벌 권한 설정 완료: {path}")
    print("다음 claude 세션부터 승인 프롬프트 없이 실행된다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

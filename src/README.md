# harness/src — 실사용 하네스 원본 사본

> 담는 것: 이 사본이 무엇이고 어떻게 다시 뜨는지. 담지 않는 것: 하네스 작동 원리(→ 상위 `harness/index.html` 이하 5쪽). 읽는 시점: 이 폴더를 다른 프로젝트로 옮기기 전.

옆 디렉토리의 HTML 5쪽은 하네스를 **사람 말로 푼 해설**이다. 이 폴더는 그 해설이 가리키는 **실물 파일 그대로**다. 해설만으로는 이식이 안 되기 때문에 원본을 함께 둔다.

## 이 사본의 성격

| 항목 | 값 |
|------|-----|
| 뜬 시점 | 2026-08-05 |
| 정본 | 레포 루트의 같은 상대경로 (`.claude/`·`static_check*.py`·`dev/`) |
| 갱신 | 자동 동기화 없음. 낡으면 그때 다시 복사한다 |
| 깃 | 추적 안 함 — `.gitignore` 의 `harness/` |

원본 구조를 그대로 미러링했다. `harness/src/.claude/hooks/check_file_rules.py` 는 레포의 `.claude/hooks/check_file_rules.py` 다.

## 다시 뜰 때

레포 루트에서 PowerShell 로 돌린다. `__pycache__` 만 빼고 나머지는 통째로 덮어쓴다.

```powershell
$dst = "harness\src"
Copy-Item ".claude\settings.json" "$dst\.claude\" -Force
Copy-Item ".claude\hooks", ".claude\agents", ".claude\skills" "$dst\.claude\" -Recurse -Force
Remove-Item "$dst\.claude\hooks\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item "static_check*.py", "CLAUDE.md", "HARNESS.md", "EDITING.md" "$dst\" -Force
Copy-Item "static_check*_baseline.txt", "md_ref_allowlist.txt" "$dst\" -Force
Copy-Item "dev\*.md" "$dst\dev\" -Force
```

래칫 파일(`static_check_tests_baseline.txt`·`static_check_schema_baseline.txt`·`static_check_api_array_baseline.txt`·`md_ref_allowlist.txt`)을 빼면 ⑫·⑭·⑮가 동결분을 전부 위반으로 뱉고 ④A 가 예외 없이 돈다. 게이트 코드와 짝이라 같이 뜬다. `static_check_md_baseline.txt` 는 레포에도 없는 게 정상이다 — ⑬ 유예 0건이라는 뜻이다.

## 이식할 때 걸리는 것

- `.claude/settings.json` 의 훅 command 는 **상대경로**다. 이 환경에서 `%CLAUDE_PROJECT_DIR%` 가 확장되지 않아 훅이 통째로 죽었던 게 이유다. 옮긴 쪽에서도 cwd 가 프로젝트 루트로 보장되는지 먼저 확인한다.
- `static_check*.py` 는 이 레포의 레이어 이름(`kofia/`·`db/`·`web/`·`frontend/src/`)을 하드코딩한 검사를 다수 담는다. 그대로 돌리면 대량 오탐이다 — 옮긴 프로젝트의 이름으로 바꾸거나 해당 검사를 뺀다.
- `dev/DATA_MODEL.md`·`dev/NAMING.md` 는 이 프로젝트의 도메인 지식이다. 하네스 골격이 아니라 내용물이라 이식 대상이 아니다.
- Codex 쪽 진입점(`AGENTS.md`·`.agents/`·`.codex/`)은 뺐다. 이 폴더는 Claude Code 하네스만이다.

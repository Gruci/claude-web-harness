"""Stop hook — EDITING.md 과업 보드에 '끝난' 잠금이 남아있으면 알린다.

멀티 세션 대응: 구버전은 잠금 행 전체를 차단해서, 다른 세션이 작업 중이면 이 세션이 영원히
종료 못 하는 데드락이 났다. 훅이 세션을 식별하지 못하는 게 원인이었다.

관례(정본: CLAUDE.md 편집 잠금) — 보드 행에 `#sid:<세션ID 앞8자>` 태그를 붙인다. 판정:
  - 내 sid 태그 행 중 **머지가 끝난 것** → 잔존이다. 완료 보고를 안 한 잠금이다.
  - 내 sid 태그 행이라도 **진행 중이면 통과** (아래).
  - 다른 sid 태그 행 → 다른 세션의 활성 잠금이라 건드리지 않는다.
  - 죽은 행(아래) → sid 와 무관하게 잔존이다. 주인이 없어진 행은 누가 지워도 된다.
  - session_id 를 못 읽으면 태그 없는 행만 본다. 전 행을 막으면 남의 행은 내가 지우면 안 되는
    것이라 종료할 방법이 사라진다 — 태그 없는 행이 내 것일 수 있는 유일한 후보다.

## 진행 중인 행은 막지 않는다

구버전은 내 sid 행이 **있기만 하면** 막았다. 그러면 "과업이 머지될 때까지 세션은 못 끝난다"가
되는데, 이 하네스는 반대로 **여러 세션에 걸치는 작업을 전제**한다(`wip_` 접두·파일 핸드오프·
`/clear` 후 이어받기). 커밋만 하고 push 승인을 기다리던 세션이 그래서 종료 불능에 빠졌고,
모델이 할 수 있는 일이 없어 연속차단 상한이 훅을 무시하고 턴을 끝냈다.

차단은 **모델이 지금 고칠 수 있는 것**에만 건다. 머지가 끝났는데 남은 행은 지우면 되지만,
머지 전 행은 지우는 것이 곧 거짓 완료 보고라 고칠 수단이 없다. `stop_hook_active` 로 재차단만
빠져나가는 방법도 있지만 그건 조건은 그대로 둔 채 입만 막는 것이라 쓰지 않는다 — 훅이 도는 건
조건이 참이기 때문이고, 조건이 틀렸으면 조건을 고친다.

## 단계 = 경고(exit 1), 차단(2) 아님

조건을 좁혀도 판정 근거는 여전히 **git 상태 추론**이다(머지 커밋 제목 매칭·ref 유무). squash
머지나 포크 워크플로처럼 흔적이 다른 경우가 있어 오탐 여지가 남는다. 검출은 계속하되 문은
안 잠근다 — 정본은 `HARNESS.md` 「단계」다.

원격 조회는 remote-tracking ref 로 한다(`git ls-remote` 아님). Stop 훅은 매 턴 끝에 도므로
네트워크를 타면 안 된다. ref 신선도는 SessionStart 의 `git_staleness.py` 가 맡는다.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hookio import default_branch, git_output as _git, read_hook_payload  # noqa: E402

# Windows 기본 cp949 → 하네스(utf-8)에서 한글 깨짐 방지
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
EDITING_MD = ROOT / "EDITING.md"
HEADER_PAIRS = (("세션 ID", "편집 파일"), ("과업", "스코프"))
BRANCH_PATTERN = re.compile(r"\b((?:feat|fix|perf|chore|docs|refactor)/[A-Za-z0-9._/-]+)")

sys.path.insert(0, str(ROOT))

# 알릴 때마다 관찰을 남긴다 — 회고가 읽을 데이터다. 기록이 실패해도 판정은 계속돼야 한다.
try:
    from kernel.trace import record
except Exception:
    def record(*_args: object, **_kwargs: object) -> None: ...


def _my_sid8() -> str | None:
    """Stop 훅 stdin JSON의 session_id 앞 8자. 파싱 실패 시 None."""
    try:
        payload = read_hook_payload()
        session_id = str(payload.get("session_id") or "")
        return session_id[:8] if len(session_id) >= 8 else None
    except Exception:
        return None


def branch_of(row: str) -> str | None:
    """행 첫 칸의 브랜치명. 스코프 서술에 섞인 경로를 집지 않도록 첫 칸만 본다."""
    cells = [cell.strip() for cell in row.strip("|").split("|")]
    found = BRANCH_PATTERN.search(cells[0]) if cells else None
    return found.group(1) if found else None


def is_merged(branch: str, base: str) -> bool:
    """기본 브랜치에 이 브랜치의 PR 머지 커밋이 있는가 — "이 과업은 끝났다"의 무모호 신호.

    reachability 로는 '갓 판 브랜치'와 '머지된 브랜치'를 못 가른다. 둘 다 기본 브랜치의
    조상이고 자기 커밋이 0개다. 머지 커밋 **제목**에는 그 모호함이 없다 — `Merge pull request
    #N from <소유자>/<브랜치>` 는 브랜치가 소스일 때만 나온다. 충돌 해소로 기본 브랜치를
    가져온 `Merge remote-tracking branch '...' into <브랜치>` 는 같은 이름이 들어가도 형태가
    달라 안 걸린다 — 그래서 이름 substring 이 아니라 전체 형태로 맞춘다.

    squash 머지는 이 흔적을 안 남긴다. 그때는 통과하고 정리가 끝난 뒤 `is_dead` 가 받는다.
    미탐을 택하는 이유는 오탐이 곧 종료 방해이기 때문이다.
    """
    log = _git("log", f"origin/{base}", "--merges", "--format=%s")
    if log is None:
        return False
    merged = re.compile(rf"^Merge pull request #\d+ from [^/\s]+/{re.escape(branch)}$")
    return any(merged.match(line.strip()) for line in log.splitlines())


def is_dead(branch: str, base: str) -> bool:
    """주인이 없어진 행인지 — 머지가 끝났고 브랜치 실물이 **어디에도** 없을 때만 참이다.

    "브랜치가 없다"만으로 판정하면 안 된다. 이 하네스는 단일 세션이면 브랜치 없이 메인
    체크아웃에서 작업하는 것을 정본 경로로 둔다(`EDITING.md`). 그래서 행이 적어둔 브랜치가
    아직 실물이 아닌 것이 정상이고, 그것을 잔해로 읽으면 **착수하자마자 자기 행이 잔해가 된다.**

    머지 커밋이 그 브랜치가 실재했다는 유일한 증거다 — 없으면 애초에 만들어진 적이 없는
    이름이라 정리할 잔해도 없다. squash 머지는 그 흔적을 안 남겨 여기서 미탐이 된다.
    오탐이 곧 지울 권한 없는 행으로 인한 종료 방해라, 이 훅 전체가 미탐을 택한다.
    """
    if not is_merged(branch, base):
        return False
    if _git("show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}") is not None:
        return False
    return _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}") is None


def _is_stale(row: str, base: str | None) -> bool:
    """내 행 중 지금 지워도 되는 것인가 — 머지가 끝났거나 브랜치명이 없는 행이다.

    브랜치명 없는 행도 대상이다. `git worktree list` 와 조인되는 것이 `#sid` 접미의 존재
    이유라 이름 없는 행은 서식 위반이고, 내 행이니 내가 고칠 수 있다.
    기본 브랜치를 모르면 머지 판정이 불능이라 통과시킨다.
    """
    branch = branch_of(row)
    if branch is None:
        return True
    return bool(base) and is_merged(branch, base)


def _active_edit_rows(text: str) -> list[str]:
    """과업 보드의 데이터 행만 추출 (주석 블록·헤더·구분선 제외).

    헤더는 **구분선(`|---|`) 앞** 이라는 위치로 가른다. 문구로 가르던 구버전은 서식이 바뀌면
    헤더를 데이터 행으로 세어, sid 불명 경로에서 헤더 하나만으로 영영 막혔다. 구 문구 조건은
    남겨둔다 — 위치 판정에 포함되지만 지우면 옛 보드 파일에서 갈린다.
    """
    in_active = False
    in_comment = False
    seen_separator = False
    data_rows: list[str] = []
    for line in text.splitlines():
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line:
            if "-->" not in line:
                in_comment = True
            continue
        # 섹션 제목에 이모지·한글 부연이 붙어도 매칭되도록 substring 검사
        if line.startswith("##") and "Active Edits" in line:
            in_active = True
            continue
        if in_active:
            if line.startswith("##"):
                break
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            if re.match(r"^\|[\s\-|]+\|$", stripped):
                seen_separator = True
                continue
            if not seen_separator:
                continue                      # 구분선 앞 = 헤더
            if any(a in stripped and b in stripped for a, b in HEADER_PAIRS):
                continue
            data_rows.append(stripped)
    return data_rows


def _report(label: str, rows: list[str], guidance: str) -> None:
    # Stop 훅의 사유는 stderr로 내보내야 Claude에게 전달된다(stdout은 무시된다).
    print(f"[EDITING LOCK] {label} {len(rows)}건", file=sys.stderr)
    for row in rows:
        print(f"  {row}", file=sys.stderr)
    print(guidance, file=sys.stderr)


def main() -> None:
    if not EDITING_MD.exists():
        sys.exit(0)

    rows = _active_edit_rows(EDITING_MD.read_text(encoding="utf-8"))
    if not rows:
        sys.exit(0)

    sid8 = _my_sid8()
    if sid8:
        mine = [row for row in rows if f"#sid:{sid8}" in row]
    else:
        # 세션 식별 불가 — 태그 없는 행만 내 것일 수 있다. 남의 sid 행까지 보면 지울 권한이
        # 없는 행 때문에 종료가 영영 불가능해진다.
        mine = [row for row in rows if "#sid:" not in row]

    base = default_branch()
    others = [row for row in rows if row not in mine]
    mine = [row for row in mine if _is_stale(row, base)]
    dead = [row for row in others
            if base and (branch := branch_of(row)) and is_dead(branch, base)]

    if not mine and not dead:
        sys.exit(0)

    for row in mine + dead:
        record("check_editing_lock", "editing_lock", sid=sid8 or "", msg=row)
    if mine:
        reason = "이 세션의" if sid8 else "(세션 식별 불가 — 태그 없는 행만 검사)"
        _report(f"{reason} 과업 보드 행이 머지 후에도 남아 있습니다 —", mine,
                "머지가 끝난 과업이거나 브랜치명이 없는 행입니다. 보드에서 제거하세요.")
    if dead:
        _report("주인이 없어진 행 —", dead,
                "브랜치가 origin 에도 로컬에도 없습니다. 끝난 과업의 잔해라 어느 세션이든 지웁니다.")
    print("⚠️ 다른 세션의 진행 중 행은 절대 지우지 말 것.", file=sys.stderr)
    # 경고(1)지 차단(2)이 아니다 — 판정 근거가 git 상태 추론이라서다. HARNESS.md 「단계」 참조.
    sys.exit(1)


if __name__ == "__main__":
    main()

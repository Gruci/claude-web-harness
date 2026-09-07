"""kernel/baseline.py — 설치 시점 위반 동결(래칫)의 읽기·적용.

하네스를 기존 레포에 끼운 첫 실행이 수백 건을 뱉으면 사람은 게이트를 통째로 끈다. 그게
하네스가 죽는 실제 경로다. 그래서 설치는 현재 위반을 (slug, 파일)로 얼리고 초록불에서
출발한다. 줄번호로 얼리지 않는 이유는 코드가 한 줄만 밀려도 동결이 풀리기 때문이다.

러너(적용)·설치 스크립트(생성)·trace(위반 경로 파싱)가 같은 판정을 쓰므로 러너 밖으로
갈랐다 — 러너의 파일 400줄 상한 준수도 이 분리의 이유다.
"""

from __future__ import annotations

from kernel.context import READ_ENC, ROOT

BASELINE_FILE = ROOT / "harness_baseline.txt"


def violation_path(violation: str) -> str | None:
    """위반 문자열 앞머리의 파일 경로. 파일에 귀속되지 않는 전역 위반이면 None."""
    head = violation.split(":", 1)[0].strip()
    if not head or " " in head or ("/" not in head and "." not in head):
        return None
    return head


def load_baseline() -> set[tuple[str, str]]:
    if not BASELINE_FILE.exists():
        return set()
    frozen: set[tuple[str, str]] = set()
    for line in BASELINE_FILE.read_text(encoding=READ_ENC).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        slug, _tab, path = line.partition("\t")
        if path.strip():
            frozen.add((slug.strip(), path.strip()))
    return frozen


def apply_baseline(sections: list) -> list:
    """동결된 (slug, 파일) 쌍의 위반을 걸러낸다. Section 형태의 정본은 runner 다."""
    frozen = load_baseline()
    if not frozen:
        return sections
    kept = []
    for slug, title, violations, skipped in sections:
        live = [v for v in violations
                if (slug, violation_path(v) or "") not in frozen]
        kept.append((slug, title, live, skipped))
    return kept

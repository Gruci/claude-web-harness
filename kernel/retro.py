"""kernel/retro.py — 관찰 기록을 패턴으로 채굴한다. 판정은 하지 않는다.

  python -X utf8 -m kernel.retro                전 기간
  python -X utf8 -m kernel.retro --since 2026-08-10

"게이트 X 가 파일 Y 에서 6번 걸렸다"까지가 여기 몫이다. 그게 규칙 위반인지 게이트 오탐인지
규칙 자체가 이 프로젝트에 안 맞는 건지는 사람이 정한다.

**왜 판정을 자동화하지 않나.** 이 하네스엔 "더 좋아졌다"를 재는 적합도 함수가 없다. 골든
대조는 회귀만 잡지 개선을 못 잰다. 적합도 없이 제안과 수용을 자동화하면 가장 싼 통과 경로 —
면제 목록 늘리기 — 로 수렴한다. 그 문은 `harness_gates/edit_surface.py` 가 닫는다.
"""

from __future__ import annotations

import sys

from kernel import trace

HOT_SPOT_HITS = 3          # 같은 게이트가 같은 파일에서 이만큼 반복되면 지목한다


def since(stamped: str) -> list[dict[str, str]]:
    """마지막 회고 다음 날부터의 기록. 회고 당일 것은 이미 읽은 것으로 본다."""
    items = trace.records()
    if not stamped:
        return items
    return [r for r in items if r.get("ts", "")[:10] > stamped]


def count_since(stamped: str) -> int:
    """정비 판정이 쓰는 수. 마지막 회고 후 훅이 몇 번 막았는가."""
    return len(since(stamped))


def by_gate(items: list[dict[str, str]]) -> list[tuple[str, int, int, str, str]]:
    """(게이트, 건수, 파일 수, 최초, 최근) — 건수 내림차순."""
    groups: dict[str, list[dict[str, str]]] = {}
    for item in items:
        if item.get("kind") == "gate":
            groups.setdefault(item.get("gate") or "?", []).append(item)
    rows = [(gate,
             len(hits),
             len({hit.get("file", "") for hit in hits if hit.get("file")}),
             min(hit.get("ts", "") for hit in hits)[:10],
             max(hit.get("ts", "") for hit in hits)[:10])
            for gate, hits in groups.items()]
    return sorted(rows, key=lambda row: (-row[1], row[0]))


def hot_spots(items: list[dict[str, str]]) -> list[tuple[str, str, int]]:
    """같은 게이트가 같은 파일에서 반복된 지점 — 관례가 안 정해졌거나 게이트가 오탐이다."""
    counts: dict[tuple[str, str], int] = {}
    for item in items:
        if item.get("kind") == "gate" and item.get("file"):
            key = (item.get("gate") or "?", item["file"])
            counts[key] = counts.get(key, 0) + 1
    return sorted(((gate, path, n) for (gate, path), n in counts.items() if n >= HOT_SPOT_HITS),
                  key=lambda row: (-row[2], row[0], row[1]))


def by_kind(items: list[dict[str, str]]) -> list[tuple[str, int]]:
    """게이트 밖 마찰 — 통읽기·반환 비만·잠금 잔존·원격 미설정·검사 불능."""
    counts: dict[str, int] = {}
    for item in items:
        kind = item.get("kind") or "?"
        if kind != "gate":
            counts[kind] = counts.get(kind, 0) + 1
    return sorted(counts.items(), key=lambda row: (-row[1], row[0]))


def _print_report(items: list[dict[str, str]]) -> None:
    sessions = len({item.get("sid", "") for item in items})
    first = min(item.get("ts", "") for item in items)[:10]
    last = max(item.get("ts", "") for item in items)[:10]
    print(f"[회고] 관찰 {len(items)}건 · 세션 {sessions}개 · {first} ~ {last}\n")

    gates = by_gate(items)
    if gates:
        print("게이트별")
        for gate, hits, files, gate_first, gate_last in gates:
            print(f"  {hits:>4}  {gate:<20} 파일 {files}개   {gate_first} ~ {gate_last}")
        print()

    spots = hot_spots(items)
    if spots:
        print(f"반복 지점 (같은 게이트·같은 파일 {HOT_SPOT_HITS}회 이상)")
        for gate, path, hits in spots:
            print(f"  {hits:>4}  {gate:<20} {path}")
        print()

    kinds = by_kind(items)
    if kinds:
        print("게이트 밖 마찰")
        for kind, hits in kinds:
            print(f"  {hits:>4}  {kind}")
        print()


def main(argv: list[str]) -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(errors="replace")
    stamped = ""
    if "--since" in argv:
        index = argv.index("--since") + 1
        if index >= len(argv):
            print("--since 뒤에 날짜가 없다 (예: --since 2026-08-10)")
            return 2
        stamped = argv[index]

    items = since(stamped)
    if not items:
        print("관찰 없음 — 훅이 아직 아무것도 막지 않았거나 기록이 비어 있다.")
        return 0

    _print_report(items)
    print("판정은 여기서 하지 않는다. 각 패턴이 규칙 위반인지, 게이트 오탐인지, "
          "규칙 자체가 이 프로젝트에 안 맞는지는 사람이 정한다.")
    print("면제 목록을 늘리는 것은 조치가 아니다 — 그 문은 편집 표면 래칫이 닫아뒀다.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

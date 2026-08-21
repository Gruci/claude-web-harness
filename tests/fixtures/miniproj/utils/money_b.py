"""픽스처: 정본 재구현 — 이름만 갈린 같은 본문(짝은 money_a)."""


def won_signed(value: int) -> str:
    sign = "+" if value > 0 else "-"
    magnitude = abs(value)
    return f"{sign}{magnitude:,}"

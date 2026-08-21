"""픽스처: 개명에서 소비처를 놓친 모듈 상수."""
PAGE_SIZE = 50


def bounded(offset: int) -> dict:
    return {"limit": DEFAULT_LIMIT, "offset": offset, "page": PAGE_SIZE}

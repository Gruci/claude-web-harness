"""픽스처: 소비 화면이 없는 라우트와 있는 라우트."""


@router.get("/api/used")
def used() -> dict:
    return {"ok": True}


@router.get("/api/nobody-consumes-this")
def orphan() -> dict:
    return {"ok": True}

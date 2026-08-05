"""픽스처: 라우트의 에러 응답 형식."""


def fail():
    return JSONResponse({"detail": "no"}, status_code=404)

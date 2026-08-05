"""픽스처: 커넥션 블록 안에서 중첩 루프로 집계."""


def agg():
    with get_db() as conn:
        for row in conn.execute("SELECT 1").fetchall():
            for cell in row:
                print(cell)

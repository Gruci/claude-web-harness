"""픽스처: 적재 직전 반올림 절삭."""


def store(conn: object, value: float) -> None:
    conn.execute("INSERT INTO metric VALUES (?)", (round(value, 2),))

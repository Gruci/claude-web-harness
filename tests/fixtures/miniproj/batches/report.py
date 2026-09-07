"""픽스처: 배치 안 직접 SELECT."""


def rows(conn: object) -> list:
    return conn.execute("SELECT value FROM metric").fetchall()

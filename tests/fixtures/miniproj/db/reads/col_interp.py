"""픽스처: 읽기 레이어의 컬럼 식별자 raw 보간."""


def series(conn: object, column: str) -> list:
    sql = f'SELECT "{column}" FROM metric'
    return conn.execute(sql).fetchall()

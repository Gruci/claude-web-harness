"""픽스처: 읽기 레이어의 쓰기 SQL."""


def wipe(conn):
    conn.execute("DELETE FROM cache")

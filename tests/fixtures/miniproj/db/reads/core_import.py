"""픽스처: 커넥션 헬퍼를 core 경유로 import."""
from db.core import get_db


def rows():
    return get_db()

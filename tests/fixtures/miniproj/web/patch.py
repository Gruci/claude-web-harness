"""픽스처: 전역 SSL 패치를 진입점 밖에서 호출."""
from utils.ssl_utils import bypass_ssl_verification

bypass_ssl_verification()

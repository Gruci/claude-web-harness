"""픽스처: 중첩 def."""


def outer():
    def inner():
        return 1
    return inner()

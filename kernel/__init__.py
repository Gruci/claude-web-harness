"""하네스 커널 — 프로젝트 무관 판정 로직과 훅.

KERNEL_VERSION 은 배포 정체다. clone 해 간 프로젝트가 `harness_install.py --check-update` 로 원류의
같은 상수와 대조하고, `--upgrade` 는 커널·훅·프리셋만 갈아끼운다. PROFILE_SCHEMA 는 커널이 요구하는
프로파일 서식 세대다 — 프로파일의 선언이 이보다 오래됐으면 세션 시작 훅이 새 항목을 고지한다.
"""

KERNEL_VERSION = "3.5.0"
PROFILE_SCHEMA = 1
UPSTREAM = "https://github.com/Gruci/claude-web-harness"
UPSTREAM_BRANCH = "master"

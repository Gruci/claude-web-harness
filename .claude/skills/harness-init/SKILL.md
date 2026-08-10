---
name: harness-init
description: >
  Bootstrap this harness onto a project so the gates run from day one. Picks a
  profile preset, fills the layer names to match what actually exists, runs the
  install script, and confirms no gate is silently skipped. Use when the user
  says "새 프로젝트 시작", "하네스 깔아줘", "harness-init", "/harness-init",
  "set up the harness", "start a new project", or when a session begins and
  harness_profile.py does not exist.
---

# harness-init

> 담는 것: 프로젝트를 하네스에 연결하는 절차. 담지 않는 것: 게이트 각각의 판정 근거(→ `HARNESS.md`)·앱 코드 작성(→ 기능 작업 스킬). 읽는 시점: 새 프로젝트를 시작하거나 `harness_profile.py` 가 없을 때.

프로젝트를 하네스에 **연결**한다. 커널은 `harness_profile.py` 하나로만 프로젝트를 알기
때문에, 이 절차의 실질은 "그 파일을 실물에 맞게 채우는 것"이다.

목표는 게이트를 켜는 게 아니라 **꺼져 있는 게이트를 없애는 것**이다. 끝났을 때
`[SKIP]` 이 남아 있다면 그건 통과가 아니라 "이 부분은 안 지켜준다"는 뜻이고, 남겨둘
거라면 그 이유를 사용자가 알고 남겨야 한다.

## 절차

### 1. 실물을 먼저 본다

프로파일을 쓰기 전에 레포에 무엇이 있는지 본다. 추측해서 채우면 선언과 실물이
어긋나고, 그 상태의 게이트는 대상 0개로 [SKIP] 이 된다.

- 최상위 디렉토리와 각 디렉토리의 파일 확장자
- 백엔드 프레임워크·DB·프론트 프레임워크 (`requirements.txt`·`package.json`)
- 이미 코드가 있는가, 빈 폴더인가

빈 폴더면 사용자에게 무엇을 만들 건지 묻는다. 스택이 정해져야 프리셋을 고른다.

### 2. 프리셋을 고르고 설치한다

```bash
python -X utf8 harness_install.py --list
python -X utf8 harness_install.py --preset <프리셋>
```

`_template` 은 아무것도 안 채워진 중립 프리셋이다. 스택이 프리셋과 다르면
`_template` 으로 깔고 3단계에서 직접 채운다.

첫 실행은 프로파일만 만들고 멈춘다 — 채우기 전 상태를 동결하면 안 되기 때문이다.

### 3. 레이어 이름을 실물에 맞춘다

`harness_profile.py` 를 열어 1단계에서 본 실물로 고친다. **모르는 건 비워둔다.**
비우면 그 게이트는 `[SKIP]` 으로 사유와 함께 찍히고, 채우면 켜진다. 억지로 채우면
엉뚱한 경로를 검사해서 오탐만 나온다.

우선순위는 이 순서다. 위쪽이 아래쪽 게이트의 전제다.

1. `LAYERS` — 특히 `ui`. 이게 없으면 프론트 게이트가 통째로 죽는다
2. `FILES["settings"]` — 환경변수 게이트의 기준점
3. `SYMBOLS` — 프레임워크마다 다른 이름들
4. `HUBS` · `LESSONS_DOC` — 문서 게이트
5. `VOCAB` · `ALLOWLIST` — 비워서 출발하는 게 정상이다

### 4. 동결하고 초록불을 만든다

```bash
python -X utf8 harness_install.py
```

기존 코드의 현재 위반을 (게이트, 파일) 단위로 얼린다. 이후로는 신규 위반만 걸린다.
`harness_baseline.txt` 를 커밋한다 — 동결이 세션 간 공유돼야 래칫이 성립한다.

### 5. 꺼진 게이트를 센다

```bash
python -X utf8 -m kernel.runner
```

출력의 `[SKIP]` 을 전부 읽는다. 각각에 대해 판단한다.

- **채울 수 있다** → 프로파일을 고치고 다시 돌린다
- **이 프로젝트엔 해당 없다** → 그대로 둔다. 프론트가 없으면 프론트 게이트는 꺼진 게 맞다
- **나중에 채운다** → 사용자에게 무엇이 안 지켜지는 상태인지 말한다

이 단계를 건너뛰면 하네스를 깔았다는 사실만 남고 무엇이 지켜지는지는 아무도 모른다.

### 6. 사용자에게 보고한다

켜진 게이트 수, 꺼진 게이트와 그 이유, 동결 건수를 말한다. 숫자만 나열하지 말고
**무엇이 지금부터 막히는지**를 한 줄로 요약한다.

## 경계

프로파일과 설치까지만 한다. 앱 코드는 만들지 않는다 — 그건 기능 작업 스킬의 몫이다.
`git init` 과 원격 연결이 안 돼 있으면 그것부터 처리한다. 게이트가 `git ls-files` 로
대상을 모으기 때문에, 저장소가 아니면 전 게이트가 대상 0개로 무력화된다.

배포 워크플로우 — git push 완료 후 서버 반영까지 단계별로 안내한다.

> 담는 것: push 이후 서버 반영까지의 단계와 컨테이너 취급 주의. 담지 않는 것: Docker 구성·이미지 빌드 정본(→ `docker/DEPLOY.md`). 읽는 시점: "배포해줘"·"서버에 반영해줘" 요청 시.

## 트리거 조건
- "배포해줘", "서버에 반영해줘", "올려줘"
- git push 완료 후 서버 업데이트 필요 시
- Docker 컨테이너 재기동 필요 시

## 구성

서버 구성 (상세: `memory/project_server.md`):
- 컨테이너 3개: `db` (PostgreSQL) / `web` (FastAPI) / `batch` (스케줄러)
- 코드 배포: git pull → docker compose 재빌드
- DB 배포: 스키마 변경 시 별도 마이그레이션 실행

## Phase 1: 로컬 준비

1. `git status` — 미커밋 변경 없는지 확인
2. `git push origin main` — 원격 반영
3. push 성공 확인 후 Phase 2 진행

## Phase 2: 서버 반영 (사용자가 직접 실행)

Claude는 서버에 직접 SSH 접근 불가 — 아래 명령을 사용자에게 전달한다.

```bash
# 서버에서 실행
git pull
docker compose up -d --build
```

컨테이너별 선택적 재기동:
```bash
docker compose up -d --build web    # 웹 서버만
docker compose up -d --build batch  # 배치 스케줄러만
```

## Phase 3: 배포 후 확인

사용자가 확인할 항목:
1. `docker compose ps` — 3개 컨테이너 모두 `Up` 상태
2. 브라우저로 관리자 페이지 접속 → 정상 로드 확인
3. 배치 로그: `docker compose logs batch --tail=50`

## DB 스키마 변경 포함 시

코드 배포 **전** 마이그레이션 실행:
```bash
# 서버에서
python db/schema.py   # 또는 해당 스크립트
git pull
docker compose up -d --build
```

## 주의사항
- `db` 컨테이너는 데이터 손실 위험 — `--build` 옵션만 사용, `down` 금지
- 배치 중단 위험 시간대(영업일 오전 9시 전후) 배포 지양

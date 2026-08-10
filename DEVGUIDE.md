# DEVGUIDE.md — 개발 가이드 허브

> 담는 것: 백엔드 작업의 라우팅 허브, 레이어별 역할 경계, 프론트 빌드 명령, 배치 스케줄과 `.env` 키 목록. 담지 않는 것: 상세 규칙(→ `dev/` 서브MD)·디자인(→ `DESIGN_GUIDE.md`). 읽는 시점: `.py` 파일을 만지기 전, 그리고 어느 `dev/` MD를 읽을지 고를 때.

---

## 라우팅 테이블

작업 시작 전 해당 MD를 on-demand로 Read한다.

| 작업 대상 | 읽어야 할 MD |
|-----------|-------------|
| 함수 명명 (`_fetch_*` / `_format_*` / `get_*`) · 3-레이어 분리 | `dev/ARCHITECTURE.md` |
| 변수명·dict 키·사용자 노출 텍스트 명명 | `dev/NAMING.md` |
| DB 연결·테이블 구조 | `dev/DATA_MODEL.md` — 설계 표준 절차 + 테이블 목록 |
| React 프론트엔드 (Vite·TS·컴포넌트·빌드) | `frontend/FRONTEND.md` (프론트 스캐폴딩 시 생성) |
| 테스트 전략 | `dev/TESTING.md` |
| 관례 갈림길·공용 헬퍼 | `dev/CONVENTIONS.md` |

---

## 모듈 구조

> 아직 코드가 없다. 첫 스캐폴딩 때 새 모듈을 여기와 `CLAUDE.md` 라우팅 테이블에 등재한다. 파일 목록의 정본은 Glob이라 적지 않는다 — 아래는 **역할 경계**만이다.

| 경로 | 역할 경계 |
|------|----------|
| `db/reads/` | SELECT 전용. 쓰기 SQL과 commit이 들어가면 게이트가 막는다 |
| `db/writes/` | INSERT·UPDATE·DELETE 전용 |
| `db/connection.py` · `db/schema.py` | 연결 풀과 라이프사이클. 동시 편집 금지 |
| `web/app.py` | 앱 부트스트랩과 SPA 서빙. 페이지 라우트는 전부 여기서 index.html을 반환한다 |
| `web/routes/` | `/api/*` 엔드포인트만. 응답 가공은 여기, 커넥션 점유 중 가공은 금지 |
| `frontend/src/constants/` | 색상과 차트 기본값의 TS 정본. 컴포넌트에 리터럴을 박으면 게이트가 막는다 |
| `frontend/src/hooks/` | `useApi` 등 데이터 접근 단일 창구. raw fetch 직접 호출 금지 |
| `frontend/src/charts/` | 차트 래퍼. raw 차트 직생성 금지 |
| `utils/` | 공용 헬퍼. 재구현 금지이고 정본 목록은 `dev/CONVENTIONS.md` 헬퍼 표 |
| `settings.py` | 환경변수 단일 출처. 다른 모듈의 `os.getenv` 직접 호출은 게이트가 막는다 |

> **400줄 분할 헬퍼 패턴**: 400줄을 넘으면 비공개 계산 헬퍼를 `<원본>_helpers.py`로 분리하고 원본이 재노출해 import 경로를 유지한다. **검사가능 규칙은 MD 산문이 아니라 `kernel/runner.py`가 강제한다.**

**의존성 방향**: 도메인 패키지 ← `db/` ← `web/` (역방향 import 절대 금지)

---

## 프론트엔드 빌드·라우팅 (React SPA)

**빌드** (Node는 빌드 시점에만 필요):
```bash
cd frontend
npm install
npm run build      # → web/static/index.html + web/static/assets/*
npm run typecheck  # tsc --noEmit (strict)
npm run dev        # dev 서버, /api·/static → FastAPI 프록시
```
- 빌드 산출물(`web/static/`)의 커밋 여부는 배포 방식 확정 시 결정 → 결정되면 여기 기록.

**라우팅** (React Router): 경로↔페이지 매핑의 **정본은 `frontend/src/App.tsx`** (손사본 표는 상시 drift하므로 만들지 않는다). FastAPI 측 페이지 라우트는 전부 `_serve_spa()`(index.html 반환).

---

## 배치 스케줄

> 배치가 생기면 아래 표를 채운다. 스케줄 상수는 코드가 정본, 이 표는 개요만.

| 환경 | 작업 | 시간 |
|------|------|------|
| (없음) | | |

---

## .env 키 목록

```
(없음)
```

> **`settings.py`가 생기는 턴에 이 목록을 채운다.** 검사 25가 양방향 대조하므로, 여기 적힌 키는 `settings.py`에 실재해야 하고 그 반대도 같다. 코드보다 먼저 적으면 게이트가 막는다.
> `.env`는 절대 git 커밋 금지.
> 모든 환경변수 접근은 `settings.py`로 응집. 각 모듈에서 `os.getenv` 직접 호출 금지 — `from settings import X` 사용 (게이트가 검사).
> 새 키 추가 시 이 목록도 그 턴 안에 갱신.

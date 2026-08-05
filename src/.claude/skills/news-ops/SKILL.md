뉴스 모니터링 운영 스킬 — null 소급 분석·dedup 정리·DB 머지·배치 점검을 단계적으로 수행한다.

> 담는 것: 뉴스 배치 이상 상황별 액션 결정과 실행 명령. 담지 않는 것: 4층 dedup 구조와 rate limit 특성(→ `news/NEWS.md`). 읽는 시점: 뉴스 배치 이상·중복 정리·DB 머지 요청 시.

## 트리거 조건
- "뉴스 배치 이상", "기사가 안 들어옴", "importance null이 많음"
- "중복 기사 정리해줘", "dedup 돌려줘"
- "로컬/서버 DB 동기화"
- "뉴스 배치 수동 실행"

## Phase 1: 현황 파악

직접 확인:
1. DB에서 `importance IS NULL` 건수: `SELECT COUNT(*) FROM news_articles WHERE importance IS NULL`
2. 최근 배치 실행 여부: 배치 로그 또는 `SELECT MAX(batch_date) FROM news_articles`
3. Gemini rate limit 중단 여부: 로그에서 `429` 확인

## Phase 2: 액션 결정

| 상황 | 권장 액션 |
|------|----------|
| `importance IS NULL` 다수 | `--fill-nulls` 소급 재분석 |
| dedup 기준 변경 후 기존 중복 잔존 | `news_dedup_retro.py --apply` |
| 로컬↔서버 AI 분석 불일치 | `news_merge.py export/import` |
| 일반 배치 미실행 | `news_batch.py` 수동 실행 |
| 관리자 페이지 키워드 이상 | `/admin` → "뉴스 설정" 탭 편집 |

## Phase 3: 실행 명령

### null importance 소급 분석
```bash
python batches/news_batch.py --fill-nulls --fill-limit 150
```
- Gemini 15초 대기 내장 → 강제 중단 금지
- UPSERT는 `summary IS NULL OR summary = ''` 조건부 — 기존 요약 보존

### 소급 중복 정리
```bash
# dry-run 먼저
python scripts/news_dedup_retro.py --days 30
# 확인 후 실제 삭제
python scripts/news_dedup_retro.py --days 30 --apply
```
- `user_rating` 있는 행은 무조건 보존 — 삭제 대상에서 제외

### 로컬↔서버 DB 머지
```bash
# 로컬에서 export
python scripts/news_merge.py export news_local.json
# 서버에서 import
docker compose exec web python scripts/news_merge.py import news_local.json
```
- `news_*.json`은 `.gitignore` 포함 — git 커밋 금지

### 수동 배치 실행
```bash
python batches/news_batch.py
# AI 분석 제외 (빠름, importance=null 저장됨)
python batches/news_batch.py --no-ai
```

## Phase 4: 확인

1. `SELECT COUNT(*), importance FROM news_articles GROUP BY importance ORDER BY importance` — null 해소 확인
2. `/news` 페이지 접속 → 최신 기사 정상 표시 확인
3. Notion 동기화 여부 (중요도 6 이상 기사 대상)
4. Dooray DM: 현재 토큰 만료 상태 — 이상 있어도 배치 오류 아님

## 주의사항
- `--no-ai` 실행 시 `importance=null` 저장 → 이후 `--fill-nulls`로 보완 필요
- Gemini 429 발생 시 30s→60s→120s 자동 재시도 내장 — 수동 중단 금지
- dedup 기준 변경 없이 `news_dedup_retro.py` 남발 금지 — 멀쩡한 기사 삭제 위험

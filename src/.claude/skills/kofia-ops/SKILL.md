KOFIA 데이터 운영 스킬 — 무결성 점검·갭 백필·agg 재집계를 단계적으로 수행한다.

> 담는 것: 백필 범위 결정 기준과 실행·후처리 순서. 담지 않는 것: KOFIA API 특성과 테이블 불변 규칙(→ `kofia/KOFIA.md`·`db/DB.md`). 읽는 시점: kofia 점검·백필 요청 시. 재실행·재점검·추가 백필 요청 때도 다시 호출한다.

## 트리거 조건
다음 중 하나 이상에 해당할 때 사용한다:
- "kofia 점검", "kofia 무결성", "kofia 백필", "갭 채우기" 관련 요청
- 특정 config의 날짜 지연 발견 또는 비교
- NAV / 설정원본 행 수 불일치 발견 후 수정
- 백필 완료 후 agg 이상 보고
- 관리자 페이지 무결성 점검 결과 해석 요청

## Phase 1: 현황 파악

아래를 직접 확인한다 (전수조사급 대량 분석만 `data` 에이전트 위임):
1. `/api/admin/kofia-status` 응답에서 config별 `days_behind` 확인
2. 가장 지연된 config vs 평균 지연 비교
3. `/api/admin/kofia-integrity` 결과에서 `nav_mismatch` 확인

## Phase 2: 백필 범위 결정

| 상황 | from_date | from_year | 대상 config |
|------|-----------|-----------|------------|
| 단일 config 지연 | 해당 config의 `latest_date` | — | 해당 1개 |
| 여러 config 지연 | — | 2020 (기본) | 전체 또는 선택 |
| 데이터 없는 config | — | 2015 | 해당 config |
| 전체 초기 수집 | — | 2015 | 전체 18개 |

## Phase 3: 백필 실행 방법

**단일 config catch-up** (관리자 페이지 권장):
- KOFIA 상세 테이블 → 해당 행의 '백필' 버튼 클릭
- `from_date` = `latest_date` 자동 적용, SSE 스트림으로 실시간 확인

**코드로 직접 실행**:
```python
from batches.kofia_batch import fill_gaps_stream
for item in fill_gaps_stream(from_date="2026-05-13", config_names=["사모_국내_설정원본"]):
    print(item)
```

**전체 백필** (관리자 페이지):
- KOFIA DB 무결성 → 시작 연도 입력 → '누락 데이터 백필' 버튼

## Phase 4: 후처리 판단

백필 완료 후 순서대로 확인한다:
1. `check_agg_consistency()` 호출 → 불일치 config 목록 확인
2. 불일치 있으면 `rebuild_agg_table()` 실행 (`db/schema.py`)
3. `/api/admin/kofia-integrity` 재점검 → `nav_mismatch` 해소 확인
4. 캐시 이상 의심 시 관리자 페이지 캐시 초기화

## 주의사항
- `kofia_empty_dates` 등록 날짜는 재백필 불필요 (KOFIA 미제공 확인분)
- KOFIA API 쿼터: 100콜마다 30초 자동 대기 — 강제 중단 금지
- 백필 후 순위 차트 이상 시 `kofia_agg` 재집계가 원인인 경우가 많음

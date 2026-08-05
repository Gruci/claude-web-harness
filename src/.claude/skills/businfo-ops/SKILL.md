경영공시 운영 스킬 — 월별 bas_ym 갱신·배치 실행·데이터 확인을 단계적으로 수행한다.

> 담는 것: 경영공시 배치를 돌릴 때 밟는 기준월 판단·실행·검증 순서. 담지 않는 것: API 응답 구조와 임직원·재무 코드의 의미(→ `businfo/BUSINFO.md`). 읽는 시점: 경영공시 배치 실행이나 월초 bas_ym 갱신 요청 시.

## 트리거 조건
- "경영공시 배치 돌려줘", "businfo 갱신"
- "이번 달 임직원/재무 데이터 안 들어옴"
- "businfo 최신 기준월 뭐야"
- 월초 신규 bas_ym 갱신 시점

## Phase 1: 현황 파악

최신 수집 기준월과 API 제공 기준월 비교:
```sql
SELECT bas_ym, COUNT(*) FROM businfo_general GROUP BY bas_ym ORDER BY bas_ym DESC LIMIT 5;
SELECT bas_ym, COUNT(*) FROM businfo_finance GROUP BY bas_ym ORDER BY bas_ym DESC LIMIT 5;
```

API 기준월 판단 기준 (`memory/project_disclosure_calendar.md` 참조):
- 금융위 API는 전월 말 기준 데이터를 다음 달 초에 제공
- 예: 5월 초 → `bas_ym=202504` 가 최신

## Phase 2: 배치 실행

```bash
# 최신 bas_ym 자동 탐지 후 수집
python batches/business_batch.py

# 특정 기준월 지정
python batches/business_batch.py --bas-ym 202504
```

- API: `data.go.kr GetAsseManaCompInfoService`
- `verify=False` (사내 방화벽 SSL 우회) — 경고 메시지 정상
- 임직원: `xcsmDcd=C` (총임직원) 포함 여부 확인

## Phase 3: 확인

```sql
-- 수집된 회사 수 확인
SELECT bas_ym, COUNT(DISTINCT fnco_cd) FROM businfo_general GROUP BY bas_ym ORDER BY bas_ym DESC LIMIT 3;

-- 재무 데이터 확인
SELECT bas_ym, COUNT(*) FROM businfo_finance GROUP BY bas_ym ORDER BY bas_ym DESC LIMIT 3;
```

- peers 페이지 → 경영 탭 → 최신 기준월 정상 표시 확인
- 임직원 합계 검증: `A(임원) + B(직원) = C(총임직원)`

## 주의사항
- API 갱신은 월 1회 (매월 초) — 중간에 돌려도 동일 데이터
- `crno` (법인등록번호) 기준 API 조회 — DB의 `fnco_cd`와 별도 관리
- `businfo_general`과 `businfo_finance` 모두 같은 `bas_ym`으로 맞춰야 함
- SSL 검증 비활성화는 의도적 설정 (`verify=False`) — 변경 금지

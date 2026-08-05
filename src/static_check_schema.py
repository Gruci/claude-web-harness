"""static_check 확장 게이트 ⑭ — DDL 저장 타입 잘림 금지 (래칫).

kofia_data·kofia_agg 금액 20컬럼이 REAL(float4)이라 원 단위 AUM 이 유효 8자리로 잘려 저장돼 왔다.
엑셀 다운로드·화면 수치·CAGR·브리핑이 전부 뭉개진 값을 썼다. 같은 감사에서 us_fundamentals.
shares_short(REAL·주식수)와 etf_pdf.contracts(NUMERIC(18,1)·소스는 소수 2자리)도 확인됐다.

⑭A REAL/FLOAT4/FLOAT(n<=24) 선언 금지 — float4 는 2^24(16,777,216) 초과 정수를 표현하지 못한다.
    비율·점수라도 DOUBLE PRECISION 을 쓴다. 4바이트를 아껴서 얻는 것이 없고, "이건 비율이니 REAL
    이어도 된다"는 판단이 매번 끼어드는 것 자체가 새는 지점이다.
⑭B NUMERIC(p,s) 의 s>0 은 같은 줄에 소스 정밀도 근거 주석 필수 — 스케일은 소스를 실제로 본
    사람만 정할 수 있다. `# any-ok: 사유` 와 같은 계약이며, 주석 문구가 아니라 확인 행위를 강제한다.

기존 선언은 static_check_schema_baseline.txt 에 `경로:컬럼명` 으로 동결 — 줄어들기만 해야 한다.
줄 번호가 아니라 컬럼명을 키로 쓰는 이유는 줄 번호가 무관한 편집에도 밀리기 때문이다.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE_FILE = ROOT / "static_check_schema_baseline.txt"

TARGET_PREFIX = "db/schema"

# `"합계" REAL` · `shares_short REAL` · `x FLOAT(24)` — 한 줄에 여러 컬럼이 오므로 finditer.
LOSSY_FLOAT = re.compile(
    r'"?([\w가-힣]+)"?\s+(REAL|FLOAT4|FLOAT\s*\(\s*(?:[1-9]|1[0-9]|2[0-4])\s*\))(?=[\s,)])',
    re.IGNORECASE,
)
SCALED_NUMERIC = re.compile(r'"?([\w가-힣]+)"?\s+NUMERIC\s*\(\s*\d+\s*,\s*[1-9]', re.IGNORECASE)


def _load_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    lines = BASELINE_FILE.read_text(encoding="utf-8").splitlines()
    return {ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")}


def check_ddl_lossy_types(py_files: list[Path]) -> list[str]:
    """게이트 ⑭: DDL 에서 소스 정밀도를 담지 못하는 타입 선언 검출."""
    baseline = _load_baseline()
    bad: list[str] = []
    for f in py_files:
        rel = f.relative_to(ROOT).as_posix()
        if not rel.startswith(TARGET_PREFIX):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for m in LOSSY_FLOAT.finditer(line):
                if f"{rel}:{m.group(1)}" in baseline:
                    continue
                bad.append(
                    f"{rel}:{i}: {m.group(1)} {m.group(2)} — DOUBLE PRECISION(실수)·"
                    f"BIGINT(정수)·NUMERIC(고정소수) 중 하나로. float4 는 2^24 초과 정수를 못 담는다"
                )
            if "--" in line or "#" in line:   # 같은 줄에 소스 정밀도 근거가 있으면 통과
                continue
            for m in SCALED_NUMERIC.finditer(line):
                if f"{rel}:{m.group(1)}" in baseline:
                    continue
                bad.append(
                    f"{rel}:{i}: {m.group(1)} NUMERIC 소수 스케일에 소스 정밀도 근거 주석 없음 — "
                    f"같은 줄에 `-- <소스> 소수 N자리` 를 달 것 (스케일은 소스를 본 사람만 정한다)"
                )
    return bad

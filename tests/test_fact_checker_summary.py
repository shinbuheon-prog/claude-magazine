from __future__ import annotations

from pipeline import fact_checker


def test_parse_verdicts_accepts_confirmed_variants():
    text = """
| claim 1 | 확인됨(메타) | - | - |
| claim 2 | 확인됨(자기고지) | - | - |
| claim 3 | 출처 불충분 | - | note |
"""
    verdicts = fact_checker.parse_verdicts(text)
    summary = fact_checker.calculate_summary(verdicts)
    assert summary["confirmed_count"] == 2
    assert summary["insufficient_source_count"] == 1
    assert summary["confirmed_ratio"] == 2 / 3

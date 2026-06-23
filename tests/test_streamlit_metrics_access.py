import pandas as pd

from ui.metrics_display import (
    LATENCY_COST_RAW_COLUMNS,
    latency_cost_column_keys,
    strip_latency_cost_raw_columns,
)


def test_latency_cost_column_keys() -> None:
    keys = latency_cost_column_keys(lambda key: key)
    assert keys == [
        "col_e2e_latency",
        "col_transcription_delay",
        "col_estimated_cost",
        "col_pricing_mode",
    ]


def test_strip_latency_cost_raw_columns_removes_sensitive_fields() -> None:
    df = pd.DataFrame(
        [
            {
                "caller_number": "+15149474976",
                "latency_metrics": {"summary": {}},
                "estimated_cost_usd": 0.12,
                "cost_breakdown": {"mode": "grok_realtime"},
            }
        ]
    )
    stripped = strip_latency_cost_raw_columns(df)
    assert list(stripped.columns) == ["caller_number"]
    for col in LATENCY_COST_RAW_COLUMNS:
        assert col not in stripped.columns
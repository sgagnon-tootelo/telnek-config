import pandas as pd

from call_metrics import (
    aggregate_call_metrics,
    enrich_calls_dataframe,
    has_latency_metrics,
    latency_e2e_avg,
    latency_playback_avg,
    latency_primary_avg,
    latency_user_turns,
)


def test_latency_e2e_avg_from_flat_dict() -> None:
    metrics = {
        "user_turns": 2,
        "e2e_latency": {"count": 2, "avg": 1.6683, "min": 0.88, "max": 2.45},
    }
    assert latency_e2e_avg(metrics) == 1.668


def test_latency_e2e_avg_from_summary_dict() -> None:
    metrics = {
        "turns": [{"role": "assistant", "playback_latency": 0.0019}],
        "summary": {
            "user_turns": 0,
            "assistant_turns": 1,
            "e2e_latency": None,
            "transcription_delay": None,
        },
    }
    assert latency_e2e_avg(metrics) is None
    assert latency_user_turns(metrics) == 0
    assert latency_playback_avg(metrics) == 0.0019
    assert latency_primary_avg(metrics) == 0.0019
    assert has_latency_metrics(metrics) is True


def test_enrich_calls_dataframe_adds_columns() -> None:
    df = pd.DataFrame(
        [
            {
                "latency_metrics": {
                    "summary": {
                        "e2e_latency": {"avg": 1.5},
                        "transcription_delay": {"avg": 0.2},
                        "user_turns": 1,
                        "assistant_turns": 2,
                    },
                    "turns": [{"role": "assistant", "playback_latency": 0.01}],
                },
                "estimated_cost_usd": 0.0805,
                "cost_breakdown": {
                    "pricing_mode": "elevenlabs_hybrid",
                    "cost_per_second_usd": 0.001275,
                    "breakdown": {"infrastructure": {"usd": 0.0279}},
                },
            }
        ]
    )
    enriched = enrich_calls_dataframe(df)
    assert enriched["_e2e_latency_avg"].iloc[0] == 1.5
    assert enriched["_primary_latency_avg"].iloc[0] == 1.5
    assert bool(enriched["_has_latency"].iloc[0]) is True
    assert enriched["_estimated_cost_usd"].iloc[0] == 0.0805
    assert enriched["_pricing_mode"].iloc[0] == "elevenlabs_hybrid"


def test_aggregate_call_metrics_counts_playback_only_calls() -> None:
    df = enrich_calls_dataframe(
        pd.DataFrame(
            [
                {
                    "latency_metrics": {
                        "summary": {
                            "user_turns": 0,
                            "assistant_turns": 5,
                            "e2e_latency": None,
                        },
                        "turns": [
                            {"role": "assistant", "playback_latency": 0.002},
                            {"role": "assistant", "playback_latency": 0.004},
                        ],
                    },
                    "estimated_cost_usd": 0.08,
                },
                {
                    "latency_metrics": {
                        "summary": {"e2e_latency": {"avg": 3.0}, "user_turns": 1},
                    },
                    "estimated_cost_usd": 0.10,
                },
            ]
        )
    )
    summary = aggregate_call_metrics(df)
    assert summary["calls_with_latency"] == 2
    assert summary["avg_e2e_latency_s"] == 3.0
    assert summary["avg_primary_latency_s"] == 1.502
    assert summary["total_cost_usd"] == 0.18
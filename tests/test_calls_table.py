from datetime import datetime, timezone

import pandas as pd

from ui.calls_table import (
    ISSUE_ABANDONED,
    ISSUE_APPOINTMENT,
    ISSUE_DONE,
    ISSUE_MESSAGE,
    ISSUE_TRANSFER,
    build_calls_display_dataframe,
    call_detail_text,
    call_issue_type,
    prepare_calls_table_dataframe,
    filter_calls_dataframe,
    issue_badge_label,
    sort_calls_dataframe,
    status_badge_label,
)


def _t(key: str, **kwargs) -> str:
    labels = {
        "badge_appointment": "RDV",
        "badge_message": "Message",
        "badge_transfer": "Transfert",
        "badge_abandoned": "Abandon",
        "badge_done": "Terminé",
        "status_badge_completed": "● Terminé",
        "status_badge_abandoned": "● Abandonné",
        "status_badge_in_progress": "● En cours",
        "col_date": "Date",
        "col_time": "Heure",
        "col_caller": "Appelant",
        "col_audio": "Audio",
        "col_status": "Statut",
        "result_action": "Résultat",
        "detail": "Détail",
        "transfer_ext_label": "poste",
        "col_appointment_start": "RDV prévu",
        "col_appointment_name": "Nom RDV",
        "col_appointment_status": "Conf. RDV",
        "col_duration": "Durée",
        "col_transcript_preview": "Transcription (aperçu)",
        "audio_available": "Oui",
    }
    if key in labels:
        return labels[key]
    return key


def test_call_detail_text_includes_transfer_phone_ext() -> None:
    row = {
        "transfer_success": True,
        "transfer_department": "Ventes",
        "transfer_to_number": "+15149474976",
        "transfer_phone_ext": "201",
    }
    assert call_detail_text(row, t_fn=_t) == "Ventes (+15149474976, poste 201)"


def test_call_detail_text_transfer_without_ext() -> None:
    row = {
        "transfer_success": True,
        "transfer_department": "Ventes",
        "transfer_to_number": "+15149474976",
        "transfer_phone_ext": None,
    }
    assert call_detail_text(row, t_fn=_t) == "Ventes (+15149474976)"


def test_call_issue_type_prioritizes_appointment() -> None:
    row = {
        "appointment_booked": True,
        "message_taken": True,
        "transfer_success": True,
        "status": "completed",
    }
    assert call_issue_type(row) == ISSUE_APPOINTMENT


def test_call_issue_type_detects_abandoned() -> None:
    row = {"appointment_booked": False, "message_taken": False, "status": "abandoned"}
    assert call_issue_type(row) == ISSUE_ABANDONED


def test_issue_and_status_badges_are_text_only() -> None:
    assert issue_badge_label(ISSUE_MESSAGE, _t) == "Message"
    assert status_badge_label("completed", _t) == "● Terminé"
    assert "📅" not in issue_badge_label(ISSUE_APPOINTMENT, _t)


def test_filter_calls_dataframe_by_period_and_issue() -> None:
    now = datetime(2026, 6, 22, tzinfo=timezone.utc)
    df = pd.DataFrame(
        [
            {
                "started_at": pd.Timestamp("2026-06-21T12:00:00Z"),
                "status": "completed",
                "_issue_type": ISSUE_MESSAGE,
            },
            {
                "started_at": pd.Timestamp("2026-05-01T12:00:00Z"),
                "status": "completed",
                "_issue_type": ISSUE_DONE,
            },
        ]
    )
    filtered = filter_calls_dataframe(
        df,
        period_days="7",
        status_filter="all",
        issue_filter=ISSUE_MESSAGE,
        now=now,
    )
    assert len(filtered) == 1
    assert filtered.iloc[0]["_issue_type"] == ISSUE_MESSAGE


def test_build_calls_display_dataframe_uses_translated_headers() -> None:
    enriched = prepare_calls_table_dataframe(
        pd.DataFrame(
            [
                {
                    "call_date": "2026-06-21",
                    "call_time": "09:30",
                    "caller_number": "+15145551234",
                    "status": "completed",
                    "appointment_booked": False,
                    "message_taken": False,
                    "transfer_success": False,
                    "statut_rdv": "—",
                    "duration_formatted": "2m 10s",
                    "transcript": "Bonjour",
                }
            ]
        ),
        t_fn=_t,
    )
    display = build_calls_display_dataframe(enriched, t_fn=_t, is_admin=False, latency_column_keys=[])
    assert list(display.columns) == [
        "Date",
        "Heure",
        "Appelant",
        "Audio",
        "Statut",
        "Résultat",
        "Conf. RDV",
        "Détail",
        "Durée",
        "Transcription (aperçu)",
    ]
    assert display.iloc[0]["Résultat"] == "Terminé"
    assert display.iloc[0]["Statut"] == "● Terminé"


def test_build_calls_display_shows_appointment_confirmation_status() -> None:
    enriched = prepare_calls_table_dataframe(
        pd.DataFrame(
            [
                {
                    "call_date": "2026-06-25",
                    "call_time": "16:40",
                    "caller_number": "+15149474976",
                    "status": "completed",
                    "appointment_booked": True,
                    "message_taken": False,
                    "transfer_success": False,
                    "statut_rdv": "✅ Confirmé",
                    "duration_formatted": "3m 00s",
                }
            ]
        ),
        t_fn=_t,
    )
    display = build_calls_display_dataframe(enriched, t_fn=_t, is_admin=False, latency_column_keys=[])
    assert display.iloc[0]["Statut"] == "● Terminé"
    assert display.iloc[0]["Conf. RDV"] == "✅ Confirmé"


def test_sort_calls_dataframe_newest_first() -> None:
    df = pd.DataFrame(
        {
            "started_at": pd.to_datetime(
                ["2026-06-20T10:00:00Z", "2026-06-21T10:00:00Z"],
                utc=True,
            )
        }
    )
    sorted_df = sort_calls_dataframe(df, newest_first=True)
    assert sorted_df.iloc[0]["started_at"].day == 21
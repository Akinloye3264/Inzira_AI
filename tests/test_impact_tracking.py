from datetime import date

import pytest

from src.inzira.impact_tracking import (
    create_case_record,
    impact_summary,
    records_from_csv,
    records_to_csv,
    update_case_record,
)


def test_case_record_contains_no_direct_identity_fields():
    record = create_case_record(
        opportunity_id="rab_twigire_muhinzi",
        opportunity_title="Twigire Muhinzi",
        provider="RAB",
        household_size=6,
        today=date(2026, 10, 25),
    )
    assert record.case_id.startswith("IA-20261025-")
    assert record.household_size_band == "6+"
    assert not hasattr(record, "name")
    assert not hasattr(record, "phone")
    assert not hasattr(record, "national_id")


def test_update_and_impact_summary():
    record = create_case_record(
        opportunity_id="kora_job_portal",
        opportunity_title="Kora",
        provider="MIFOTRA",
        next_followup="2026-10-24",
        today=date(2026, 10, 20),
    )
    updated = update_case_record(
        record,
        status="application_started",
        outcome="interview",
        barrier="documents",
        next_followup="2026-10-24",
        today=date(2026, 10, 23),
    )
    summary = impact_summary([updated], today=date(2026, 10, 25))
    assert summary == {
        "total": 1,
        "contacted": 1,
        "applications": 1,
        "positive_outcomes": 1,
        "followups_due": 1,
    }


def test_csv_round_trip():
    record = create_case_record(
        opportunity_id="rtb_imyuga",
        opportunity_title="IMYUGA",
        provider="RTB",
        today=date(2026, 10, 25),
    )
    restored = records_from_csv(records_to_csv([record]))
    assert restored == [record]


def test_csv_rejects_wrong_schema():
    with pytest.raises(ValueError, match="schema"):
        records_from_csv("name,phone\nA,123\n")

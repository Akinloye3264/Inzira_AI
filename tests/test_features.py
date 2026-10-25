from __future__ import annotations

import math

from src.inzira.features import build_assessment_features, validate_household_counts


INPUT_FEATURES = [
    "province",
    "ur",
    "household_members",
    "children_count",
    "working_age_count",
    "elderly_count",
    "sleeping_rooms",
    "crowding_ratio",
    "dependency_ratio",
    "floor_material",
    "electricity_access",
    "livestock_ownership",
    "log_livestock_count",
    "mobile_phone",
    "recent_internet_use",
    "insured_share",
    "agricultural_activity",
    "wage_employment",
    "nonfarm_business",
]


def complete_answers() -> dict[str, object]:
    return {
        "province": 1,
        "ur": 1,
        "household_members": 6,
        "children_count": 2,
        "elderly_count": 1,
        "sleeping_rooms": 2,
        "floor_material": 5,
        "electricity_access": 1,
        "livestock_range": "3_5",
        "mobile_phone": 1,
        "recent_internet_use": 0,
        "insured_members": 3,
        "agricultural_activity": 1,
        "wage_employment": 0,
        "nonfarm_business": 1,
    }


def test_feature_derivation_and_completeness() -> None:
    assessment = build_assessment_features(complete_answers(), INPUT_FEATURES)
    row = assessment.frame.iloc[0]

    assert assessment.completeness == 1.0
    assert row["working_age_count"] == 3
    assert row["crowding_ratio"] == 3
    assert row["dependency_ratio"] == 1
    assert row["insured_share"] == 0.5
    assert row["livestock_ownership"] == 1
    assert math.isclose(row["log_livestock_count"], math.log1p(4))


def test_unknown_answers_are_missing_and_reduce_completeness() -> None:
    answers = complete_answers()
    answers["recent_internet_use"] = None
    answers["sleeping_rooms"] = None
    assessment = build_assessment_features(answers, INPUT_FEATURES)

    assert assessment.completeness == 10 / 12
    assert math.isnan(assessment.frame.iloc[0]["crowding_ratio"])


def test_invalid_counts_are_detected() -> None:
    answers = complete_answers()
    answers["children_count"] = 5
    answers["elderly_count"] = 2
    assert validate_household_counts(answers) == "composition"

    answers = complete_answers()
    answers["insured_members"] = 7
    assert validate_household_counts(answers) == "insurance"

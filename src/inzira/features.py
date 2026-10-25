from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


QUESTION_GROUPS = (
    "location",
    "household_composition",
    "sleeping_rooms",
    "floor_material",
    "electricity",
    "livestock",
    "mobile_phone",
    "internet",
    "insurance",
    "agriculture",
    "wage_employment",
    "business",
)


@dataclass(frozen=True)
class AssessmentFeatures:
    frame: pd.DataFrame
    answered_groups: tuple[str, ...]
    completeness: float
    household_size: float | None


def _known(value: Any) -> bool:
    if value is None:
        return False
    try:
        return not bool(pd.isna(value))
    except (TypeError, ValueError):
        return True


def _number(value: Any) -> float:
    return float(value) if _known(value) else np.nan


def _category(value: Any) -> object:
    if not _known(value):
        return np.nan
    numeric = float(value)
    return f"{numeric:.1f}"


def _group_answered(group: str, answers: dict[str, Any]) -> bool:
    rules = {
        "location": ("province", "ur"),
        "household_composition": (
            "household_members",
            "children_count",
            "elderly_count",
        ),
        "sleeping_rooms": ("sleeping_rooms",),
        "floor_material": ("floor_material",),
        "electricity": ("electricity_access",),
        "livestock": ("livestock_range",),
        "mobile_phone": ("mobile_phone",),
        "internet": ("recent_internet_use",),
        "insurance": ("insured_members", "household_members"),
        "agriculture": ("agricultural_activity",),
        "wage_employment": ("wage_employment",),
        "business": ("nonfarm_business",),
    }
    return all(_known(answers.get(field)) for field in rules[group])


def build_assessment_features(
    answers: dict[str, Any], input_features: list[str]
) -> AssessmentFeatures:
    members = _number(answers.get("household_members"))
    children = _number(answers.get("children_count"))
    elderly = _number(answers.get("elderly_count"))
    rooms = _number(answers.get("sleeping_rooms"))
    insured = _number(answers.get("insured_members"))

    if all(np.isfinite(value) for value in (members, children, elderly)):
        working_age = max(members - children - elderly, 0.0)
    else:
        working_age = np.nan

    crowding = members / rooms if np.isfinite(members) and rooms > 0 else np.nan
    if np.isfinite(children) and np.isfinite(elderly) and working_age > 0:
        dependency = (children + elderly) / working_age
    else:
        dependency = np.nan

    livestock_range = answers.get("livestock_range")
    livestock_counts = {
        "none": 0.0,
        "1_2": 1.5,
        "3_5": 4.0,
        "6_plus": 6.0,
    }
    livestock_count = livestock_counts.get(livestock_range, np.nan)
    livestock_ownership = (
        float(livestock_count > 0) if np.isfinite(livestock_count) else np.nan
    )
    log_livestock = (
        float(np.log1p(livestock_count)) if np.isfinite(livestock_count) else np.nan
    )

    insured_share = (
        min(max(insured / members, 0.0), 1.0)
        if np.isfinite(insured) and members > 0
        else np.nan
    )

    row = {
        "province": _category(answers.get("province")),
        "ur": _category(answers.get("ur")),
        "household_members": members,
        "children_count": children,
        "working_age_count": working_age,
        "elderly_count": elderly,
        "sleeping_rooms": rooms,
        "crowding_ratio": crowding,
        "dependency_ratio": dependency,
        "floor_material": _category(answers.get("floor_material")),
        "electricity_access": _number(answers.get("electricity_access")),
        "livestock_ownership": livestock_ownership,
        "log_livestock_count": log_livestock,
        "mobile_phone": _number(answers.get("mobile_phone")),
        "recent_internet_use": _number(answers.get("recent_internet_use")),
        "insured_share": insured_share,
        "agricultural_activity": _number(answers.get("agricultural_activity")),
        "wage_employment": _number(answers.get("wage_employment")),
        "nonfarm_business": _number(answers.get("nonfarm_business")),
    }

    missing = [feature for feature in input_features if feature not in row]
    if missing:
        raise ValueError(f"The app did not create required model features: {missing}")

    answered = tuple(
        group for group in QUESTION_GROUPS if _group_answered(group, answers)
    )
    frame = pd.DataFrame([{feature: row[feature] for feature in input_features}])
    size = float(members) if np.isfinite(members) else None
    return AssessmentFeatures(
        frame=frame,
        answered_groups=answered,
        completeness=len(answered) / len(QUESTION_GROUPS),
        household_size=size,
    )


def validate_household_counts(answers: dict[str, Any]) -> str | None:
    members = answers.get("household_members")
    children = answers.get("children_count")
    elderly = answers.get("elderly_count")
    if all(_known(value) for value in (members, children, elderly)):
        if float(children) + float(elderly) > float(members):
            return "composition"

    insured = answers.get("insured_members")
    if _known(insured) and _known(members) and float(insured) > float(members):
        return "insurance"
    return None

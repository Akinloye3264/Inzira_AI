from __future__ import annotations

from dataclasses import dataclass

from .features import AssessmentFeatures
from .resources import RuntimeBundle


@dataclass(frozen=True)
class ScreeningResult:
    score: float
    threshold: float
    elevated_risk: bool
    completeness: float
    limited_information: bool
    small_household: bool


def run_screening(
    bundle: RuntimeBundle, assessment: AssessmentFeatures
) -> ScreeningResult:
    minimum = float(bundle.configuration["minimum_answered_fraction"])
    if assessment.completeness < minimum:
        raise ValueError("Insufficient answered questions for a screening result.")

    processed = bundle.preprocessor.transform(assessment.frame)
    score = float(bundle.model.predict_proba(processed)[0, 1])
    threshold = float(bundle.configuration["threshold"])
    standard = float(bundle.configuration["standard_result_answered_fraction"])

    return ScreeningResult(
        score=score,
        threshold=threshold,
        elevated_risk=score >= threshold,
        completeness=assessment.completeness,
        limited_information=assessment.completeness < standard,
        small_household=(
            assessment.household_size is not None
            and assessment.household_size <= 3
        ),
    )

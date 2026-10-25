"""Load the packaged artifacts and run one end-to-end prediction."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inzira.features import build_assessment_features
from src.inzira.inference import run_screening
from src.inzira.resources import load_runtime_bundle


def main() -> None:
    bundle = load_runtime_bundle(PROJECT_ROOT)
    answers = {
        "province": 1,
        "ur": 2,
        "household_members": 6,
        "children_count": 3,
        "elderly_count": 1,
        "sleeping_rooms": 2,
        "floor_material": 1,
        "electricity_access": 1,
        "livestock_range": "1_2",
        "mobile_phone": 1,
        "recent_internet_use": 0,
        "insured_members": 3,
        "agricultural_activity": 1,
        "wage_employment": 0,
        "nonfarm_business": 0,
    }
    assessment = build_assessment_features(
        answers, bundle.configuration["input_features"]
    )
    processed = bundle.preprocessor.transform(assessment.frame)
    result = run_screening(bundle, assessment)

    assert processed.shape == (1, bundle.configuration["processed_feature_count"])
    assert 0 <= result.score <= 1
    assert assessment.completeness == 1
    print(
        "Inference smoke test passed:",
        {
            "processed_shape": processed.shape,
            "score": round(result.score, 4),
            "threshold": result.threshold,
            "elevated_risk": result.elevated_risk,
        },
    )


if __name__ == "__main__":
    main()

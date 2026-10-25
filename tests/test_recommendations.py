from src.inzira.recommendations import suggest_support


def test_recommendations_are_limited_and_profile_based() -> None:
    answers = {
        "household_members": 5,
        "children_count": 3,
        "elderly_count": 0,
        "sleeping_rooms": 1,
        "insured_members": 2,
        "electricity_access": 0,
        "mobile_phone": 0,
        "recent_internet_use": 0,
        "agricultural_activity": 1,
        "livestock_range": "none",
        "wage_employment": 0,
        "nonfarm_business": 0,
    }
    recommendations = suggest_support(answers, "en", elevated_risk=True)

    assert len(recommendations) == 3
    assert len({item.theme for item in recommendations}) == 3
    assert recommendations[0].title
    assert recommendations[0].reason

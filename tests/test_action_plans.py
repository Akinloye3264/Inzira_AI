from src.inzira.action_plans import build_action_plans
from src.inzira.recommendations import Recommendation


def test_action_plan_has_steps_preparation_and_official_link() -> None:
    recommendation = Recommendation(
        theme="Health-insurance inclusion",
        title="Health insurance",
        action="Check cover",
        reason="Some members lack cover",
    )
    plan = build_action_plans([recommendation], "en")[0]

    assert len(plan.steps) == 3
    assert len(plan.prepare) >= 2
    assert plan.links
    assert plan.links[0].url.startswith("https://")


def test_action_plans_are_available_in_kinyarwanda() -> None:
    recommendation = Recommendation(
        theme="Agricultural resilience",
        title="Agriculture",
        action="Extension",
        reason="Agricultural activity",
    )
    plan = build_action_plans([recommendation], "rw")[0]

    assert plan.title == "Ubufasha bw'umujyanama mu buhinzi"

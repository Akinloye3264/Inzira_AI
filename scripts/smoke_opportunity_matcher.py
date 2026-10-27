"""Exercise the opportunity matcher through Streamlit's testing runtime."""

from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    app = AppTest.from_file(PROJECT_ROOT / "app.py").run(timeout=30)
    app.button_group(key="main_page").set_value("opportunities").run(timeout=30)
    assert not app.exception, [exception.message for exception in app.exception]

    app.multiselect(key="opp_goals").select("agriculture")
    app.button(key="opp_goal_continue").click().run(timeout=30)
    app.multiselect(key="opp_participant_profiles").select("farmer")
    app.multiselect(key="opp_skills").select("agriculture")
    app.button(key="opp_profile_continue").click().run(timeout=30)
    app.multiselect(key="opp_support_types").select("extension").select("market_linkage")
    app.radio(key="opp_access_mode").set_value("local")
    app.button(key="opp_match_submit").click().run(timeout=30)

    assert not app.exception, [exception.message for exception in app.exception]
    rendered_text = "\n".join(
        item.value
        for group in (app.title, app.subheader, app.markdown, app.caption)
        for item in group
    )
    assert "Twigire Muhinzi" in rendered_text
    assert app.download_button, "The opportunity plan download did not render."
    shortlist_controls = [checkbox for checkbox in app.checkbox if checkbox.key.startswith("opp_shortlist_")]
    assert len(shortlist_controls) == 3, "The first result view must show exactly three matches."
    print(
        "Opportunity matcher UI passed:",
        {"matches_rendered": len(shortlist_controls), "downloads": len(app.download_button)},
    )


if __name__ == "__main__":
    main()

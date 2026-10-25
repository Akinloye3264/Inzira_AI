"""Render the Streamlit app with Streamlit's built-in testing runtime."""

from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    app = AppTest.from_file(PROJECT_ROOT / "app.py").run(timeout=30)
    assert not app.exception, [exception.message for exception in app.exception]
    assert app.button, "The landing page did not render its start button."
    assert app.button_group(key="language"), "The bilingual language selector did not render."

    start_button = next(
        button
        for button in app.button
        if button.label in {"Tangira isuzuma ryihuse", "Begin quick check"}
    )
    start_button.click().run(timeout=30)
    assert not app.exception, [exception.message for exception in app.exception]
    assert app.progress and app.progress[0].value > 0

    def continue_with(label: str = "Komeza →") -> None:
        next(button for button in app.button if button.label == label).click().run(
            timeout=30
        )
        assert not app.exception, [exception.message for exception in app.exception]

    app.selectbox(key="q_province").select(1)
    app.selectbox(key="q_ur").select(2)
    continue_with()

    app.selectbox(key="q_household_members").select(6)
    app.selectbox(key="q_children_count").select(3)
    app.selectbox(key="q_elderly_count").select(1)
    continue_with()

    app.selectbox(key="q_sleeping_rooms").select(2)
    app.selectbox(key="q_floor_material").select(1)
    app.radio(key="q_electricity_access").set_value(1)
    continue_with()

    app.radio(key="q_mobile_phone").set_value(1)
    app.radio(key="q_recent_internet_use").set_value(0)
    app.selectbox(key="q_insured_members").select(3)
    continue_with()

    app.selectbox(key="q_livestock_range").select("1_2")
    app.radio(key="q_agricultural_activity").set_value(1)
    app.radio(key="q_wage_employment").set_value(0)
    app.radio(key="q_nonfarm_business").set_value(0)
    continue_with("Suzuma ibisubizo →")

    assert app.progress[0].value == 100
    continue_with("Reba ibyavuye mu isuzuma")

    assert app.download_button, "The completed assessment did not render a result."
    print(
        "Full UI journey passed:",
        {
            "result_downloads": len(app.download_button),
            "result_cards": len(app.markdown),
        },
    )


if __name__ == "__main__":
    main()

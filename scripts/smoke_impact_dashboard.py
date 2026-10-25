"""Exercise referral creation and follow-up in Streamlit's testing runtime."""

from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def errors(app: AppTest) -> list[str]:
    return [exception.message for exception in app.exception]


def main() -> None:
    app = AppTest.from_file(PROJECT_ROOT / "scripts" / "admin_test_app.py").run(timeout=30)
    assert not app.exception, errors(app)

    app.button_group(key="staff_section").set_value("new").run(timeout=30)
    app.selectbox(key="case_create_opportunity").set_value("rab_twigire_muhinzi")
    next(button for button in app.button if button.label == "Kora referral itarangwamo amazina").click().run(timeout=30)
    assert not app.exception, errors(app)
    assert app.session_state["case_records"], "No anonymous case was created."

    app.button_group(key="staff_section").set_value("update").run(timeout=30)
    app.selectbox(key="case_update_status").set_value("application_started")
    app.selectbox(key="case_update_outcome").set_value("interview")
    app.selectbox(key="case_update_barrier").set_value("documents")
    next(button for button in app.button if button.label == "Bika amakuru yo gukurikirana").click().run(timeout=30)
    assert not app.exception, errors(app)

    record = app.session_state["case_records"][0]
    assert record.status == "application_started"
    assert record.outcome == "interview"

    app.button_group(key="staff_section").set_value("dashboard").run(timeout=30)
    rendered_text = "\n".join(item.value for item in app.markdown)
    assert "metric-grid" in rendered_text

    app.button_group(key="staff_section").set_value("data").run(timeout=30)
    assert app.download_button, "Anonymous case CSV did not render."
    print(
        "Impact dashboard UI passed:",
        {"case_id": record.case_id, "status": record.status, "dashboard": "rendered"},
    )


if __name__ == "__main__":
    main()

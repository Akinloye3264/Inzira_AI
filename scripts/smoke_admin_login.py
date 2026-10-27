"""Render the real admin entry point through the Firebase login screen."""

from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    app = AppTest.from_file(PROJECT_ROOT / "admin_app.py").run(timeout=30)
    assert not app.exception, [item.message for item in app.exception]
    assert len(app.text_input) >= 2, "The Firebase login form did not render."
    assert any(button.label == "Sign in securely" for button in app.button)
    rendered = "\n".join(item.value for item in app.markdown)
    assert "Inzira AI Admin" in rendered
    print("Admin login UI passed")


if __name__ == "__main__":
    main()

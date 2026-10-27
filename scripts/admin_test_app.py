"""UI-only admin harness. This file is never used by the deployed application."""

from pathlib import Path

from src.inzira.admin_dashboard import render_admin_dashboard


render_admin_dashboard(
    actor="test-admin@inzira.local",
    store=None,
    project_root=Path(__file__).resolve().parents[1],
)

"""UI-only admin harness. This file is never used by the deployed application."""

import streamlit as st

from app import (
    get_opportunities,
    initialize_state,
    inject_styles,
    render_staff_create,
    render_staff_dashboard,
    render_staff_data,
    render_staff_update,
)
from src.inzira.copy import IMPACT_COPY


inject_styles()
initialize_state()
language = "rw"
copy = IMPACT_COPY[language]
opportunities = get_opportunities()
opportunities_by_id = {item.id: item for item in opportunities}
actor = "test-admin@inzira.local"

section_labels = {
    "new": copy["tab_new"],
    "update": copy["tab_update"],
    "dashboard": copy["tab_dashboard"],
    "data": copy["tab_data"],
}
if st.session_state.staff_section not in section_labels:
    st.session_state.staff_section = "new"
section = st.segmented_control(
    "Staff workspace",
    list(section_labels),
    format_func=lambda value: section_labels[value],
    selection_mode="single",
    label_visibility="collapsed",
    key="staff_section",
)

if section == "new":
    render_staff_create(
        language, copy, opportunities, opportunities_by_id, None, actor
    )
elif section == "update":
    render_staff_update(copy, None, actor)
elif section == "dashboard":
    render_staff_dashboard(language, copy)
else:
    render_staff_data(copy, None, actor)

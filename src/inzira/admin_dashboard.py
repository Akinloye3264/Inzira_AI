from __future__ import annotations

from datetime import date, timedelta
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.inzira.case_store import CaseStoreError, NeonCaseStore
from src.inzira.copy import IMPACT_COPY
from src.inzira.impact_tracking import (
    ALLOWED_BARRIERS,
    ALLOWED_OUTCOMES,
    ALLOWED_STATUSES,
    CaseRecord,
    count_by,
    create_case_record,
    impact_summary,
    records_from_csv,
    records_to_csv,
    update_case_record,
)
from src.inzira.opportunity_matching import Opportunity, load_catalogue


PROVINCES = ("City of Kigali", "Eastern", "Northern", "Southern", "Western", "Unknown")


def inject_admin_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --wine:#741f3d; --wine-dark:#4c1027; --rose:#f7e9ed;
            --cream:#f7f2ea; --paper:#fffdf9; --ink:#292421;
            --muted:#716761; --line:#e6d9d4; --sage:#71836d;
        }
        #MainMenu, footer, [data-testid="stHeader"], [data-testid="stToolbar"],
        [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
            display:none !important;
        }
        [data-testid="stAppViewContainer"] { background:var(--cream); color:var(--ink); }
        .block-container { max-width:1320px; padding-top:1.2rem; padding-bottom:4rem; }
        h1,h2,h3 { color:var(--ink); letter-spacing:-.025em; }
        .admin-topbar { display:flex; align-items:center; justify-content:space-between; gap:1rem;
            background:var(--wine-dark); color:white; border-radius:20px; padding:1rem 1.2rem;
            margin-bottom:1rem; box-shadow:0 16px 40px rgba(76,16,39,.14); }
        .admin-brand { display:flex; align-items:center; gap:.8rem; }
        .admin-mark { width:42px; height:42px; border-radius:13px; display:grid; place-items:center;
            background:#d7a33b; color:var(--wine-dark); font-weight:900; }
        .admin-title { font-size:1.05rem; font-weight:800; }
        .admin-subtitle { color:#e9d9df; font-size:.78rem; letter-spacing:.06em; }
        .admin-user { color:#f7e9ed; font-size:.82rem; text-align:right; }
        .admin-hero { background:linear-gradient(135deg,var(--wine) 0%,var(--wine-dark) 100%);
            border-radius:24px; padding:1.7rem; color:white; margin:.5rem 0 1.25rem; overflow:hidden; }
        .admin-hero h1 { color:white; margin:.2rem 0 .35rem; font-size:clamp(1.8rem,4vw,3rem); }
        .admin-hero p { color:#f4e7eb; margin:0; max-width:760px; }
        .eyebrow { color:#e3b95e; font-size:.74rem; font-weight:800; letter-spacing:.14em; }
        .metric-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.8rem; margin:1rem 0 1.2rem; }
        .metric-card { background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:1rem;
            box-shadow:0 8px 24px rgba(70,44,39,.05); }
        .metric-value { color:var(--wine); font-size:1.65rem; font-weight:850; }
        .metric-label { color:var(--muted); font-size:.8rem; margin-top:.2rem; }
        .status-pill { display:inline-flex; border-radius:999px; background:var(--rose); color:var(--wine);
            padding:.35rem .7rem; font-size:.76rem; font-weight:750; }
        [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {
            background:var(--paper); border-color:var(--line) !important; border-radius:18px !important; }
        .stButton > button[kind="primary"], .stFormSubmitButton > button {
            background:var(--wine) !important; border-color:var(--wine) !important; color:white !important; }
        .stButton > button, .stDownloadButton > button, .stLinkButton > a { min-height:44px; border-radius:12px !important; }
        [data-testid="stButtonGroup"] { background:var(--paper); border:1px solid var(--line); border-radius:14px; padding:.2rem; }
        [data-testid="stButtonGroup"] button[aria-pressed="true"] { background:var(--wine) !important; color:white !important; }
        @media (max-width:900px) {
            .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
            .admin-topbar { align-items:flex-start; }
        }
        @media (max-width:600px) {
            .block-container { padding:.7rem .75rem 5rem; }
            .metric-grid { grid-template-columns:1fr; }
            .admin-user { display:none; }
            .admin-hero { padding:1.2rem; border-radius:18px; }
            [data-testid="stButtonGroup"] { overflow-x:auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_grid(items: list[tuple[str, str | int]]) -> None:
    cards = "".join(
        f"<div class='metric-card'><div class='metric-value'>{escape(str(value))}</div>"
        f"<div class='metric-label'>{escape(label)}</div></div>"
        for label, value in items
    )
    st.markdown(f"<div class='metric-grid'>{cards}</div>", unsafe_allow_html=True)


def _load_records(store: NeonCaseStore | None) -> list[CaseRecord]:
    if store is None:
        return list(st.session_state.setdefault("admin_records", []))
    records = store.list_records()
    st.session_state.admin_records = records
    return records


def _save_created(store: NeonCaseStore | None, record: CaseRecord, actor: str) -> None:
    if store is None:
        st.session_state.admin_records = [record, *_load_records(None)]
    else:
        store.create_record(record, actor=actor)
        st.session_state.admin_records = store.list_records()


def _save_updated(store: NeonCaseStore | None, record: CaseRecord, actor: str) -> None:
    if store is None:
        st.session_state.admin_records = [
            record if item.case_id == record.case_id else item for item in _load_records(None)
        ]
    else:
        store.update_record(record, actor=actor)
        st.session_state.admin_records = store.list_records()


def render_overview(records: list[CaseRecord], language: str) -> None:
    copy = IMPACT_COPY[language]
    summary = impact_summary(records)
    _metric_grid(
        [
            (copy["total"], summary["total"]),
            (copy["contacted"], summary["contacted"]),
            (copy["applications"], summary["applications"]),
            (copy["positive"], summary["positive_outcomes"]),
            (copy["due"], summary["followups_due"]),
        ]
    )
    if not records:
        st.info(copy["empty"])
        return
    left, right = st.columns(2)
    with left:
        st.subheader(copy["status_chart"])
        status = pd.DataFrame(
            [{"Status": copy["statuses"].get(key, key), "Cases": value} for key, value in count_by(records, "status").items()]
        ).set_index("Status")
        st.bar_chart(status, horizontal=True, color="#741f3d")
    with right:
        st.subheader(copy["pathway_chart"])
        pathways = pd.DataFrame(
            [{"Pathway": key, "Cases": value} for key, value in count_by(records, "opportunity_title").items()]
        ).set_index("Pathway")
        st.bar_chart(pathways, horizontal=True, color="#71836d")
    due = [
        item for item in records
        if item.next_followup and item.next_followup <= date.today().isoformat()
        and item.status not in {"closed", "accepted"}
    ]
    st.subheader(copy["due_title"])
    if due:
        st.dataframe(
            [{copy["case_id"]: item.case_id, copy["opportunity"]: item.opportunity_title,
              copy["status"]: copy["statuses"].get(item.status, item.status), copy["followup"]: item.next_followup}
             for item in due],
            width="stretch", hide_index=True,
        )
    else:
        st.caption("No overdue follow-ups." if language == "en" else "Nta dosiye yarengeje igihe cyo gukurikiranwa.")
    st.caption(copy["impact_note"])


def render_referrals(records: list[CaseRecord], store: NeonCaseStore | None, actor: str, language: str) -> None:
    copy = IMPACT_COPY[language]
    st.subheader(copy["tab_update"])
    if not records:
        st.info(copy["empty"])
        return
    search = st.text_input("Search by case ID, pathway or provider", key="admin_case_search").lower().strip()
    filtered = [
        item for item in records
        if not search or search in " ".join((item.case_id, item.opportunity_title, item.provider)).lower()
    ]
    st.dataframe(
        [{copy["case_id"]: item.case_id, copy["opportunity"]: item.opportunity_title,
          copy["status"]: copy["statuses"].get(item.status, item.status),
          copy["outcome"]: copy["outcomes"].get(item.outcome, item.outcome), copy["followup"]: item.next_followup}
         for item in filtered],
        width="stretch", hide_index=True,
    )
    selected_id = st.selectbox(
        copy["select_case"], [item.case_id for item in filtered],
        format_func=lambda value: next(f"{item.case_id} · {item.opportunity_title}" for item in filtered if item.case_id == value),
        key="case_update_id",
    )
    selected = next(item for item in records if item.case_id == selected_id)
    with st.form("case_update_form"):
        status = st.selectbox(copy["status"], sorted(ALLOWED_STATUSES), index=sorted(ALLOWED_STATUSES).index(selected.status),
                              format_func=lambda value: copy["statuses"].get(value, value), key="case_update_status")
        outcome = st.selectbox(copy["outcome"], sorted(ALLOWED_OUTCOMES), index=sorted(ALLOWED_OUTCOMES).index(selected.outcome),
                               format_func=lambda value: copy["outcomes"].get(value, value), key="case_update_outcome")
        barrier = st.selectbox(copy["barrier"], sorted(ALLOWED_BARRIERS), index=sorted(ALLOWED_BARRIERS).index(selected.barrier),
                               format_func=lambda value: copy["barriers"].get(value, value), key="case_update_barrier")
        followup = st.date_input(copy["followup"], value=date.fromisoformat(selected.next_followup) if selected.next_followup else None,
                                 key="case_update_followup")
        submitted = st.form_submit_button(copy["save"], width="stretch")
    if submitted:
        updated = update_case_record(
            selected, status=status, outcome=outcome, barrier=barrier,
            next_followup=followup.isoformat() if followup else "",
        )
        try:
            _save_updated(store, updated, actor)
            st.success(copy["saved"])
            st.rerun()
        except CaseStoreError as exc:
            st.error(str(exc))


def render_create(opportunities: list[Opportunity], store: NeonCaseStore | None, actor: str, language: str) -> None:
    copy = IMPACT_COPY[language]
    st.subheader(copy["tab_new"])
    st.write(copy["create_intro"])
    with st.form("create_case_form"):
        opportunity_id = st.selectbox(
            copy["opportunity"], [item.id for item in opportunities],
            format_func=lambda value: next(item.title(language) for item in opportunities if item.id == value),
            key="case_create_opportunity",
        )
        province = st.selectbox("Province", PROVINCES, key="case_create_province")
        household_band = st.selectbox("Household size", ["Unknown", "1–3", "4–5", "6+"])
        followup = st.date_input(copy["followup"], value=date.today() + timedelta(days=7), key="case_create_followup")
        consent = st.checkbox(
            "The applicant requested assistance and no direct identifiers are being entered.",
            key="case_create_consent",
        )
        submitted = st.form_submit_button(copy["create"], width="stretch")
    if submitted:
        if not consent:
            st.error("Confirm applicant consent before creating a referral.")
            return
        opportunity = next(item for item in opportunities if item.id == opportunity_id)
        size_map = {"Unknown": None, "1–3": 3, "4–5": 5, "6+": 6}
        record = create_case_record(
            opportunity_id=opportunity.id,
            opportunity_title=opportunity.title(language),
            provider=opportunity.provider,
            province=province,
            household_size=size_map[household_band],
            screening_route="staff_assisted_referral",
            next_followup=followup.isoformat(),
        )
        try:
            _save_created(store, record, actor)
            st.success(f"{copy['created']}: {record.case_id}")
        except CaseStoreError as exc:
            st.error(str(exc))


def render_opportunities(opportunities: list[Opportunity], language: str) -> None:
    st.subheader("Reviewed opportunity directory")
    st.caption("Administrators verify the route and source. Providers—not Inzira AI—decide eligibility and acceptance.")
    st.dataframe(
        [{"ID": item.id, "Provider": item.provider, "Opportunity": item.title(language),
          "Official route": item.apply_url, "Source": item.source_url} for item in opportunities],
        width="stretch", hide_index=True,
        column_config={"Official route": st.column_config.LinkColumn("Official route"), "Source": st.column_config.LinkColumn("Source")},
    )
    st.info("Opportunity catalogue changes remain code-reviewed in this release so public links cannot be silently replaced.")


def render_data(records: list[CaseRecord], store: NeonCaseStore | None, actor: str, language: str) -> None:
    copy = IMPACT_COPY[language]
    st.subheader(copy["tab_data"])
    st.write(copy["data_note"])
    st.download_button(copy["download"], records_to_csv(records).encode("utf-8"),
                       "inzira_anonymous_case_records.csv", "text/csv", width="stretch")
    with st.form("import_case_form"):
        upload = st.file_uploader(copy["upload"], type=["csv"])
        submitted = st.form_submit_button(copy["import"])
    if submitted and upload is not None:
        try:
            imported = records_from_csv(upload.getvalue().decode("utf-8-sig"))
            if store is None:
                st.session_state.admin_records = imported
            else:
                store.import_records(imported, actor=actor)
            st.success(f"{copy['imported']}: {len(imported)}")
            st.rerun()
        except (UnicodeDecodeError, ValueError, CaseStoreError) as exc:
            st.error(f"{copy['import_error']}: {exc}")


def render_settings(store: NeonCaseStore | None, actor: str) -> None:
    st.subheader("Administration")
    _metric_grid([
        ("Signed-in administrator", actor),
        ("Database", "Connected" if store and store.health() else "Test mode"),
        ("Data scope", "Anonymous referrals"),
    ])
    if store:
        st.subheader("Recent admin activity")
        activity = store.recent_audit()
        if activity:
            st.dataframe(activity, width="stretch", hide_index=True)
        else:
            st.caption("No administrator activity has been recorded yet.")
    if st.button("Sign out", width="stretch", key="admin_logout"):
        st.session_state.pop("firebase_session", None)
        st.rerun()


def render_admin_dashboard(
    *,
    actor: str,
    store: NeonCaseStore | None,
    project_root: Path,
) -> None:
    inject_admin_styles()
    # The protected operations workspace is intentionally English-only. The
    # public screening and opportunity experiences remain bilingual.
    language = "en"
    copy = IMPACT_COPY[language]
    opportunities = load_catalogue(project_root / "data" / "opportunities.json")
    try:
        records = _load_records(store)
    except CaseStoreError as exc:
        st.error(str(exc))
        return
    st.markdown(
        f"<div class='admin-topbar'><div class='admin-brand'><div class='admin-mark'>IA</div>"
        f"<div><div class='admin-title'>Inzira AI Admin</div><div class='admin-subtitle'>REFERRALS · FOLLOW-UP · OUTCOMES</div></div>"
        f"</div><div class='admin-user'>Authenticated administrator<br><strong>{escape(actor)}</strong></div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='admin-hero'><div class='eyebrow'>PROTECTED OPERATIONS WORKSPACE</div>"
        "<h1>Referral command centre</h1><p>Help applicants reach verified providers, track follow-ups and record provider-reported outcomes.</p></div>",
        unsafe_allow_html=True,
    )
    sections = {
        "overview": copy["tab_dashboard"], "referrals": copy["tab_update"], "create": copy["tab_new"],
        "opportunities": copy["tab_opportunities"], "data": copy["tab_data"], "settings": copy["tab_settings"],
    }
    section = st.pills(
        "Admin navigation", list(sections), format_func=lambda value: sections[value],
        selection_mode="single", default="overview", key="staff_section", label_visibility="collapsed",
    ) or "overview"
    st.warning(copy["role_notice"])
    if section == "overview":
        render_overview(records, language)
    elif section == "referrals":
        render_referrals(records, store, actor, language)
    elif section == "create":
        render_create(opportunities, store, actor, language)
    elif section == "opportunities":
        render_opportunities(opportunities, language)
    elif section == "data":
        render_data(records, store, actor, language)
    else:
        render_settings(store, actor)

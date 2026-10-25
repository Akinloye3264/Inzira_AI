from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.inzira.action_plans import ActionPlan, build_action_plans
from src.inzira.case_store import CaseStoreError, MongoCaseStore
from src.inzira.copy import EXTRA_COPY, IMPACT_COPY, OPPORTUNITY_COPY
from src.inzira.features import (
    QUESTION_GROUPS,
    build_assessment_features,
    validate_household_counts,
)
from src.inzira.inference import ScreeningResult, run_screening
from src.inzira.impact_tracking import (
    CaseRecord,
    count_by,
    create_case_record,
    impact_summary,
    records_from_csv,
    records_to_csv,
    update_case_record,
)
from src.inzira.opportunity_matching import (
    MatchProfile,
    OpportunityMatch,
    load_catalogue,
    rank_opportunities,
)
from src.inzira.recommendations import suggest_support
from src.inzira.resources import RuntimeBundle, load_runtime_bundle


PROJECT_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Inzira AI",
    page_icon="🟠",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource(show_spinner=False)
def get_bundle() -> RuntimeBundle:
    return load_runtime_bundle(PROJECT_ROOT)


@st.cache_data(show_spinner=False)
def get_opportunities():
    return load_catalogue(PROJECT_ROOT / "data" / "opportunities.json")


@st.cache_resource(show_spinner=False)
def get_case_store(uri: str, database: str) -> MongoCaseStore:
    return MongoCaseStore(uri, database)


def _secret_section(name: str) -> dict[str, Any]:
    try:
        return dict(st.secrets[name]) if name in st.secrets else {}
    except (FileNotFoundError, KeyError):
        return {}


def require_admin_access(language: str) -> tuple[str, MongoCaseStore | None] | None:
    """Authenticate and authorize one of the explicitly allowlisted admins."""
    auth_config = _secret_section("auth")
    admin_config = _secret_section("admin")
    database_config = _secret_section("mongodb")
    if not auth_config:
        st.subheader("Admin sign-in" if language == "en" else "Kwinjira kwa admin")
        st.info(
            "Admin authentication is not configured yet. Add the Google OIDC and MongoDB values from `.streamlit/secrets.example.toml` to the app's Streamlit secrets."
            if language == "en"
            else "Kwinjira kwa admin ntikurashyirwaho. Shyira Google OIDC na MongoDB biri muri `.streamlit/secrets.example.toml` muri Streamlit secrets z'iyi porogaramu."
        )
        return None

    if not st.user.is_logged_in:
        st.markdown("### Admin sign-in" if language == "en" else "### Kwinjira kwa admin")
        st.write(
            "Use an approved Google account to open the protected referral workspace."
            if language == "en"
            else "Koresha konti ya Google yemewe kugira ngo winjire ahakurikiranwa referral."
        )
        st.button(
            "Continue with Google" if language == "en" else "Komeza ukoresheje Google",
            type="primary",
            use_container_width=True,
            on_click=st.login,
        )
        return None

    email = str(st.user.get("email", "")).lower().strip()
    allowed_emails = {
        str(item).lower().strip() for item in admin_config.get("allowed_emails", [])
    }
    if st.user.get("email_verified") is False or not email or email not in allowed_emails:
        st.error(
            "This Google account is signed in but is not authorized as an Inzira administrator."
            if language == "en"
            else "Iyi konti ya Google yinjiye ariko ntiyemerewe kuba admin wa Inzira."
        )
        st.button("Sign out" if language == "en" else "Sohoka", on_click=st.logout)
        return None

    uri = str(database_config.get("uri", "")).strip()
    database = str(database_config.get("database", "inzira_ai")).strip()
    if not uri:
        st.error(
            "MongoDB is not configured. Add the `[mongodb]` section to Streamlit secrets."
            if language == "en"
            else "MongoDB ntirashyirwaho. Ongeramo igice cya `[mongodb]` muri Streamlit secrets."
        )
        st.button("Sign out" if language == "en" else "Sohoka", on_click=st.logout)
        return None

    try:
        return email, get_case_store(uri, database)
    except CaseStoreError:
        st.error(
            "The admin database is temporarily unavailable. Check the MongoDB URI and Atlas network access."
            if language == "en"
            else "Ububiko bwa admin ntiburi kuboneka. Reba MongoDB URI n'uburenganzira bwa Atlas network."
        )
        return None


def render_metric_grid(items: list[tuple[str, str | int]]) -> None:
    cards = "".join(
        (
            "<div class='metric-card'>"
            f"<div class='metric-value'>{escape(str(value))}</div>"
            f"<div class='metric-label'>{escape(label)}</div>"
            "</div>"
        )
        for label, value in items
    )
    st.markdown(f"<div class='metric-grid'>{cards}</div>", unsafe_allow_html=True)


def render_page_intro(kicker: str, title: str, body: str) -> None:
    st.markdown(
        f"<div class='question-kicker'>{escape(kicker)}</div>",
        unsafe_allow_html=True,
    )
    st.title(title)
    st.write(body)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #f7f3ea;
            --muted: #aaa59b;
            --gold: #e2a52b;
            --gold-dark: #f1b63d;
            --gold-soft: rgba(226,165,43,.14);
            --ivory: #090908;
            --white: #151513;
            --line: #302e29;
            --success: #7fc8a7;
            --shadow: 0 18px 48px rgba(0,0,0,.28);
        }
        html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .stApp { background: var(--ivory); color: var(--ink); font-size:16px; }
        .block-container { max-width: 1020px; padding: 3.75rem 1.25rem 3rem; }
        h1, h2, h3 { color:var(--ink); letter-spacing:-.025em; }
        h1 { font-size:clamp(2rem,5vw,3.45rem) !important; line-height:1.04 !important; }
        h2 { font-size:clamp(1.55rem,3vw,2.15rem) !important; }
        h3 { font-size:clamp(1.12rem,2vw,1.35rem) !important; }
        p, label, .stMarkdown { line-height:1.55; }
        .topbar { display:flex; align-items:center; gap:.72rem; min-height:52px; }
        .brand-mark { display:grid; place-items:center; width:42px; height:42px; border-radius:14px;
            background:linear-gradient(145deg,#f5c65e,var(--gold)); color:#17140e; font-weight:900;
            box-shadow:0 7px 18px rgba(168,111,13,.18); }
        .brand-name { font-size:1.2rem; font-weight:850; color:var(--ink); }
        .brand-caption { color:var(--muted); font-size:.68rem; font-weight:700; letter-spacing:.09em; }
        .hero { background:radial-gradient(circle at 50% 115%,rgba(226,165,43,.18),transparent 42%),linear-gradient(145deg,#0b0b0a,#11110f);
            border:1px solid var(--line); border-radius:20px; padding:clamp(1.45rem,5vw,3.25rem);
            box-shadow:var(--shadow); overflow:hidden; position:relative; }
        .hero-grid { display:grid; grid-template-columns:1fr; max-width:780px; margin:0 auto; text-align:center; }
        .hero .eyebrow { color:var(--gold-dark); font-size:.73rem; font-weight:850; letter-spacing:.13em; }
        .hero h1 { max-width:660px; margin:.55rem 0 .8rem; }
        .hero p { max-width:640px; margin:0 auto; font-size:1.05rem; color:var(--muted); }
        .trust-row { display:flex; justify-content:center; flex-wrap:wrap; gap:.5rem; margin-top:1.15rem; }
        .trust-chip { display:inline-flex; align-items:center; gap:.35rem; padding:.46rem .7rem;
            border:1px solid #5c4820; border-radius:999px; background:#1a1916;
            color:#f2c35b; font-size:.78rem; font-weight:750; }
        .path-mark { display:none; }
        .path-orbit { width:160px; height:160px; border-radius:50%; border:22px solid rgba(226,165,43,.18);
            position:relative; box-shadow:inset 0 0 0 1px rgba(168,111,13,.12); }
        .path-orbit:before { content:""; position:absolute; inset:21px; border-radius:50%;
            background:linear-gradient(145deg,#f7c75f,var(--gold)); box-shadow:0 16px 28px rgba(168,111,13,.2); }
        .path-orbit:after { content:"→"; position:absolute; inset:0; display:grid; place-items:center;
            color:var(--ink); font-size:2.3rem; font-weight:900; transform:rotate(-18deg); }
        .section-card, [data-testid="stVerticalBlockBorderWrapper"] { background:var(--white);
            border-color:var(--line) !important; border-radius:18px !important; box-shadow:0 7px 24px rgba(74,53,17,.045); }
        .section-card { padding:clamp(1rem,3vw,1.6rem); margin:.7rem 0; }
        .question-kicker { color:var(--gold-dark); text-transform:uppercase; letter-spacing:.1em;
            font-size:.75rem; font-weight:800; margin-bottom:.4rem; }
        .result-card { border-radius:20px; padding:clamp(1.25rem,4vw,2.25rem); margin:.8rem 0 1.1rem;
            border:1px solid var(--line); background:linear-gradient(145deg,#151513,#11110f); box-shadow:var(--shadow); }
        .result-card.elevated { border-color:#74561e; background:linear-gradient(145deg,#1e1a11,#121210); }
        .result-card h2 { margin:.3rem 0 .7rem; }
        .support-card { background:var(--white); border:1px solid var(--line); border-left:4px solid var(--gold);
            border-radius:16px; padding:1rem 1.1rem; }
        .support-card h4 { color:var(--ink); margin:.1rem 0 .55rem; font-size:1.08rem; }
        .support-card p { font-size:.94rem; }
        .support-reason, .metric-note { color:var(--muted); }
        .notice { border-radius:13px; padding:.85rem 1rem; background:#1d1910;
            border:1px solid #5c4820; margin:.65rem 0; }
        .metric-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(145px,1fr)); gap:.7rem; margin:.8rem 0 1rem; }
        .metric-card { background:var(--white); border:1px solid var(--line); border-radius:15px; padding:.9rem; min-height:92px; }
        .metric-value { color:var(--ink); font-size:1.5rem; font-weight:850; line-height:1.15; }
        .metric-label { color:var(--muted); font-size:.78rem; line-height:1.25; margin-top:.35rem; }
        [data-testid="stMetric"] { background:var(--white); border:1px solid var(--line); padding:.85rem; border-radius:14px; }
        .stButton > button, .stDownloadButton > button, .stLinkButton > a {
            border-radius:12px !important; min-height:44px; padding:.58rem 1rem; font-weight:760;
            border:1px solid var(--gold); transition:transform .12s ease, box-shadow .12s ease, border-color .12s ease;
        }
        .stButton > button[kind="primary"] { background:var(--gold); color:#2d210f; }
        .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
            border-color:var(--gold-dark); color:var(--gold-dark); transform:translateY(-1px); box-shadow:0 8px 18px rgba(168,111,13,.12); }
        button:focus-visible, a:focus-visible, input:focus-visible { outline:3px solid var(--gold) !important; outline-offset:2px; }
        div[role="radiogroup"] { gap:.35rem; }
        .st-key-main_page { position:sticky; top:.5rem; z-index:100; margin:.35rem 0 1rem; }
        .st-key-main_page [data-testid="stButtonGroup"] { background:rgba(18,18,16,.94); border:1px solid var(--line);
            border-radius:15px; padding:.35rem; box-shadow:0 8px 24px rgba(74,53,17,.07); backdrop-filter:blur(12px); }
        .st-key-main_page button { min-height:44px; border-radius:11px !important; font-weight:760; }
        .st-key-language [data-testid="stButtonGroup"] { background:#11110f; border:1px solid var(--line);
            border-radius:12px; padding:.25rem; }
        .st-key-language button { min-height:40px; border-radius:9px !important; font-weight:720; }
        .st-key-start_assessment { max-width:360px; margin:1rem auto 0; }
        .st-key-staff_section [data-testid="stButtonGroup"] { background:var(--white); border:1px solid var(--line);
            border-radius:14px; padding:.3rem; margin:.6rem 0 1rem; flex-wrap:wrap; }
        .st-key-staff_section button { min-height:44px; border-radius:10px !important; }
        .staff-badge { display:inline-flex; gap:.4rem; align-items:center; padding:.42rem .68rem; border-radius:999px;
            background:#211c10; border:1px solid #664e1c; color:#f2c35b; font-size:.78rem; font-weight:760; }
        [data-testid="stForm"] { background:var(--white); border:1px solid var(--line); border-radius:18px; padding:clamp(.9rem,3vw,1.35rem); }
        [data-testid="stExpander"] { border-color:var(--line) !important; border-radius:14px !important; background:rgba(21,21,19,.72); }
        hr { border-color:var(--line); }
        .app-footer { margin-top:2rem; padding-top:1rem; border-top:1px solid var(--line);
            color:var(--muted); font-size:.8rem; }
        @media (max-width: 900px) {
            .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
            [data-testid="stHorizontalBlock"]:has([data-testid="stVegaLiteChart"]) { flex-wrap:wrap !important; }
            [data-testid="stHorizontalBlock"]:has([data-testid="stVegaLiteChart"]) > [data-testid="stColumn"] {
                flex:1 1 100% !important; min-width:100% !important; }
        }
        @media (max-width: 720px) {
            .block-container { padding:3.65rem .85rem calc(6.4rem + env(safe-area-inset-bottom)); }
            .topbar { min-height:46px; }
            .brand-mark { width:38px; height:38px; border-radius:12px; }
            .brand-caption { display:none; }
            .hero { border-radius:17px; padding:1.35rem 1.05rem; }
            .hero-grid { grid-template-columns:1fr; gap:.75rem; }
            .path-mark { display:none; }
            .hero p { font-size:1rem; }
            .trust-row { gap:.38rem; }
            .trust-chip { font-size:.73rem; padding:.38rem .58rem; }
            .st-key-main_page { position:fixed; top:auto; left:0; right:0; bottom:0; z-index:999;
                margin:0; padding:.45rem .55rem calc(.45rem + env(safe-area-inset-bottom));
                background:rgba(9,9,8,.96); border-top:1px solid var(--line); }
            .st-key-main_page [data-testid="stButtonGroup"] { border:0; box-shadow:0 -8px 24px rgba(74,53,17,.08);
                padding:.25rem; width:100%; }
            .st-key-main_page button { min-height:48px; padding:.35rem .25rem !important; font-size:.76rem !important;
                white-space:normal !important; line-height:1.15 !important; }
            .st-key-language button { min-height:40px; padding:.3rem .45rem !important; font-size:.7rem !important; }
            .st-key-start_assessment { max-width:none; }
            [data-testid="stHorizontalBlock"]:not(:has(.topbar)):not(:has([data-testid="stMetric"])) {
                flex-wrap:wrap !important; gap:.65rem !important; }
            [data-testid="stHorizontalBlock"]:not(:has(.topbar)):not(:has([data-testid="stMetric"])) > [data-testid="stColumn"] {
                flex:1 1 100% !important; min-width:100% !important; }
            .metric-grid { grid-template-columns:1fr; }
            [data-testid="stForm"] { padding:.8rem; }
            .app-footer { margin-bottom:.5rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    defaults = {
        "language": "rw",
        "assessment_started": False,
        "assessment_step": 0,
        "assessment_result": None,
        "assessment_answers": {},
        "completion_mode": "self",
        "opportunity_profile": None,
        "opportunity_step": 0,
        "opportunity_draft": {
            "goals": (),
            "participant_profiles": (),
            "skills": (),
            "support_types": (),
            "access_mode": "either",
            "readiness": "within_30_days",
        },
        "case_records": [],
        "case_opportunity_id": None,
        "staff_section": "dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_assessment() -> None:
    for key in list(st.session_state):
        if key.startswith("q_") or key.startswith("action_"):
            del st.session_state[key]
    st.session_state.assessment_started = False
    st.session_state.assessment_step = 0
    st.session_state.assessment_result = None
    st.session_state.assessment_answers = {}


def persist_widget_answer(field: str) -> None:
    """Copy a widget value into state that survives when its step is hidden."""
    st.session_state.assessment_answers[field] = st.session_state.get(f"q_{field}")


def persist_visible_answers() -> None:
    for key, value in st.session_state.items():
        if key.startswith("q_"):
            st.session_state.assessment_answers[key.removeprefix("q_")] = value


def restore_widget_answer(field: str) -> None:
    widget_key = f"q_{field}"
    if widget_key not in st.session_state and field in st.session_state.assessment_answers:
        st.session_state[widget_key] = st.session_state.assessment_answers[field]


def get_answers() -> dict[str, Any]:
    fields = (
        "province",
        "ur",
        "household_members",
        "children_count",
        "elderly_count",
        "sleeping_rooms",
        "floor_material",
        "electricity_access",
        "livestock_range",
        "mobile_phone",
        "recent_internet_use",
        "insured_members",
        "agricultural_activity",
        "wage_employment",
        "nonfarm_business",
    )
    answers = {
        field: st.session_state.assessment_answers.get(field) for field in fields
    }
    for field in fields:
        widget_key = f"q_{field}"
        if widget_key in st.session_state:
            answers[field] = st.session_state[widget_key]
    return answers


def count_select(label: str, key: str, minimum: int = 0, maximum: int = 30) -> None:
    values: list[int | None] = [None, *range(minimum, maximum + 1)]
    restore_widget_answer(key)
    st.selectbox(
        label,
        values,
        format_func=lambda value: unknown_label() if value is None else str(value),
        key=f"q_{key}",
        on_change=persist_widget_answer,
        args=(key,),
    )


def unknown_label() -> str:
    language = st.session_state.language
    return "Simbizi" if language == "rw" else "I don't know"


def yes_no_select(label: str, key: str) -> None:
    copy = EXTRA_COPY[st.session_state.language]
    labels = {None: copy["unknown"], 1: copy["yes"], 0: copy["no"]}
    restore_widget_answer(key)
    st.radio(
        label,
        [None, 1, 0],
        format_func=lambda value: labels[value],
        horizontal=True,
        key=f"q_{key}",
        on_change=persist_widget_answer,
        args=(key,),
    )


def code_select(label: str, key: str, options: list[tuple[Any, str]]) -> None:
    values = [None, *(value for value, _ in options)]
    labels = {None: unknown_label(), **dict(options)}
    restore_widget_answer(key)
    st.selectbox(
        label,
        values,
        format_func=lambda value: labels[value],
        key=f"q_{key}",
        on_change=persist_widget_answer,
        args=(key,),
    )


def render_sidebar(bundle: RuntimeBundle) -> str:
    brand_column, language_column = st.columns([3, 1.4])
    with brand_column:
        st.markdown(
            """
            <div class="topbar">
              <div class="brand-mark">IA</div>
              <div><div class="brand-name">Inzira AI</div><div class="brand-caption">SCREEN · MATCH · SUPPORT</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with language_column:
        st.segmented_control(
            "Ururimi / Language",
            ["rw", "en"],
            format_func=lambda code: "Ikinyarwanda" if code == "rw" else "English",
            selection_mode="single",
            key="language",
            label_visibility="collapsed",
        )
    return st.session_state.language


def render_header_navigation(copy: dict[str, str]) -> str:
    opportunity_copy = OPPORTUNITY_COPY[st.session_state.language]
    impact_copy = IMPACT_COPY[st.session_state.language]
    labels = {
        "check": copy["nav_check"],
        "opportunities": opportunity_copy["nav"],
        "impact": impact_copy["nav"],
        "about": copy["nav_about"],
    }
    if "main_page" not in st.session_state:
        st.session_state.main_page = "check"
    elif st.session_state.main_page not in labels:
        st.session_state.main_page = "about"
    return st.pills(
        "Navigation",
        list(labels),
        format_func=lambda value: labels[value],
        selection_mode="single",
        label_visibility="collapsed",
        key="main_page",
    )


def render_progress(copy: dict[str, str], step: int) -> None:
    names = [
        copy["step_location"],
        copy["step_household"],
        copy["step_home"],
        copy["step_access"],
        copy["step_livelihood"],
        copy["step_review"],
    ]
    st.progress((step + 1) / len(names), text=f"{step + 1}/{len(names)} · {names[step]}")


def navigation_buttons(
    back_label: str,
    next_label: str,
    *,
    on_next: Any | None = None,
    next_type: str = "primary",
) -> None:
    left, _, right = st.columns([1, 2, 1])
    with left:
        if st.button("← " + back_label, use_container_width=True):
            persist_visible_answers()
            if st.session_state.assessment_step == 0:
                st.session_state.assessment_started = False
            else:
                st.session_state.assessment_step -= 1
            st.rerun()
    with right:
        if st.button(next_label + " →", type=next_type, use_container_width=True):
            persist_visible_answers()
            if on_next is None or on_next():
                st.session_state.assessment_step += 1
                st.rerun()


def render_step(
    bundle: RuntimeBundle,
    language: str,
    base: dict[str, Any],
    copy: dict[str, str],
) -> None:
    step = st.session_state.assessment_step
    render_progress(copy, step)
    with st.container(border=True):
        st.caption(copy["optional_hint"])
        render_step_content(bundle, language, base, copy)


def render_step_content(
    bundle: RuntimeBundle,
    language: str,
    base: dict[str, Any],
    copy: dict[str, str],
) -> None:
    step = st.session_state.assessment_step
    questions = base["questions"]
    fields = base["field_labels"]
    options = base["options"]

    if step == 0:
        st.markdown('<div class="question-kicker">01 · LOCATION</div>', unsafe_allow_html=True)
        st.subheader(questions["location"])
        col1, col2 = st.columns(2)
        with col1:
            code_select(
                fields["province"],
                "province",
                [(code, options[f"province_{code}"]) for code in range(1, 6)],
            )
        with col2:
            code_select(
                fields["residence"],
                "ur",
                [(1, options["urban"]), (2, options["rural"])],
            )
        navigation_buttons(base["general"]["back"], base["general"]["continue"])

    elif step == 1:
        st.markdown('<div class="question-kicker">02 · HOUSEHOLD</div>', unsafe_allow_html=True)
        st.subheader(questions["household_composition"])
        col1, col2, col3 = st.columns(3)
        with col1:
            count_select(fields["household_members"], "household_members", 1, 30)
        with col2:
            count_select(fields["children_count"], "children_count", 0, 20)
        with col3:
            count_select(fields["elderly_count"], "elderly_count", 0, 20)

        def validate() -> bool:
            if validate_household_counts(get_answers()) == "composition":
                st.error(copy["composition_error"])
                return False
            return True

        navigation_buttons(
            base["general"]["back"], base["general"]["continue"], on_next=validate
        )

    elif step == 2:
        st.markdown('<div class="question-kicker">03 · HOME</div>', unsafe_allow_html=True)
        st.subheader(copy["step_home"])
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**{questions['sleeping_rooms']}**")
            count_select(fields["sleeping_rooms"], "sleeping_rooms", 1, 15)
        with col2:
            st.markdown(f"**{questions['floor_material']}**")
            code_select(
                fields.get("floor_material", questions["floor_material"]),
                "floor_material",
                [(code, options[f"floor_{code}"]) for code in (1, 2, 3, 4, 5, 6, 8)],
            )
        st.markdown(f"**{questions['electricity']}**")
        yes_no_select(questions["electricity"], "electricity_access")
        navigation_buttons(base["general"]["back"], base["general"]["continue"])

    elif step == 3:
        st.markdown('<div class="question-kicker">04 · ACCESS</div>', unsafe_allow_html=True)
        st.subheader(copy["step_access"])
        col1, col2 = st.columns(2)
        with col1:
            yes_no_select(questions["mobile_phone"], "mobile_phone")
        with col2:
            yes_no_select(questions["internet"], "recent_internet_use")
        st.markdown(f"**{questions['insurance']}**")
        count_select(fields["insured_members"], "insured_members", 0, 30)

        def validate() -> bool:
            if validate_household_counts(get_answers()) == "insurance":
                st.error(copy["insurance_error"])
                return False
            return True

        navigation_buttons(
            base["general"]["back"], base["general"]["continue"], on_next=validate
        )

    elif step == 4:
        st.markdown('<div class="question-kicker">05 · LIVELIHOOD</div>', unsafe_allow_html=True)
        st.subheader(copy["step_livelihood"])
        code_select(
            questions["livestock"],
            "livestock_range",
            [
                ("none", options["livestock_0"]),
                ("1_2", options["livestock_1_2"]),
                ("3_5", options["livestock_3_5"]),
                ("6_plus", options["livestock_6_plus"]),
            ],
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            yes_no_select(questions["agriculture"], "agricultural_activity")
        with col2:
            yes_no_select(questions["wage_employment"], "wage_employment")
        with col3:
            yes_no_select(questions["business"], "nonfarm_business")
        navigation_buttons(base["general"]["back"], base["general"]["review"])

    else:
        render_review(bundle, language, base, copy)


def render_review(
    bundle: RuntimeBundle,
    language: str,
    base: dict[str, Any],
    copy: dict[str, str],
) -> None:
    st.markdown('<div class="question-kicker">06 · REVIEW</div>', unsafe_allow_html=True)
    st.subheader(copy["review_title"])
    st.write(copy["review_body"])
    assessment = build_assessment_features(
        get_answers(), bundle.configuration["input_features"]
    )
    answered = len(assessment.answered_groups)
    st.progress(
        assessment.completeness,
        text=f"{answered}/{len(QUESTION_GROUPS)} {copy['answered']} · {assessment.completeness:.0%}",
    )
    if assessment.completeness < bundle.configuration["minimum_answered_fraction"]:
        st.warning(base["results"]["insufficient_message"])
    elif assessment.completeness < bundle.configuration["standard_result_answered_fraction"]:
        st.warning(base["results"]["limited_message"])
    else:
        st.success(base["safeguards"]["screening_warning"])

    left, _, right = st.columns([1, 2, 1])
    with left:
        if st.button("← " + base["general"]["back"], use_container_width=True):
            st.session_state.assessment_step -= 1
            st.rerun()
    with right:
        if st.button(
            base["general"]["submit"], type="primary", use_container_width=True
        ):
            if assessment.completeness < bundle.configuration["minimum_answered_fraction"]:
                st.error(base["results"]["insufficient_title"])
            else:
                try:
                    result = run_screening(bundle, assessment)
                    st.session_state.assessment_result = {
                        "score": result.score,
                        "threshold": result.threshold,
                        "elevated_risk": result.elevated_risk,
                        "completeness": result.completeness,
                        "limited_information": result.limited_information,
                        "small_household": result.small_household,
                    }
                    st.rerun()
                except Exception:
                    st.error(
                        "The model could not complete this screening. Please try again or request an assisted assessment."
                        if language == "en"
                        else "Model ntiyashoboye kurangiza iri suzuma. Ongera ugerageze cyangwa usabe ubufasha."
                    )


def summary_text(
    result: ScreeningResult,
    plans: list[ActionPlan],
    base: dict[str, Any],
    copy: dict[str, str],
) -> str:
    title = (
        base["results"]["positive_title"]
        if result.elevated_risk
        else base["results"]["negative_title"]
    )
    lines = [
        "INZIRA AI — QUICK SCREENING SUMMARY",
        "",
        title,
        f"{base['results']['screening_score']}: {result.score:.0%}",
        f"{base['results']['data_completeness']}: {result.completeness:.0%}",
        "",
        base["safeguards"]["screening_warning"],
        base["safeguards"]["human_review"],
        "",
        base["results"]["suggested_support"] + ":",
    ]
    for index, plan in enumerate(plans, start=1):
        lines.extend(
            [
                "",
                f"{copy['priority']} {index}: {plan.title}",
                f"{copy['target_outcome']}: {plan.outcome}",
                f"{copy['official_route']}: {plan.service}",
                copy["steps_this_week"] + ":",
                *(f"  {step_index}. {step}" for step_index, step in enumerate(plan.steps, start=1)),
                copy["prepare_label"] + ": " + "; ".join(plan.prepare),
                *(f"{link.label}: {link.url}" for link in plan.links),
            ]
        )
    lines.extend(["", copy["eligibility_note"], copy["complete_route"]])
    return "\n".join(lines)


def render_result(
    bundle: RuntimeBundle,
    language: str,
    base: dict[str, Any],
    copy: dict[str, str],
) -> None:
    data = st.session_state.assessment_result
    result = ScreeningResult(**data)
    positive = result.elevated_risk
    title = base["results"]["positive_title" if positive else "negative_title"]
    message = base["results"]["positive_message" if positive else "negative_message"]
    card_class = "result-card elevated" if positive else "result-card"
    st.markdown(
        f"""
        <div class="{card_class}">
          <div class="question-kicker">{copy['result_overline']}</div>
          <h2>{title}</h2>
          <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result.limited_information:
        st.warning(
            f"**{base['results']['limited_title']}** — {base['results']['limited_message']}"
        )
    if result.small_household:
        st.markdown(
            f"<div class='notice'><strong>{base['results']['small_household_title']}</strong><br>{base['results']['small_household_message']}</div>",
            unsafe_allow_html=True,
        )

    details_label = (
        "View screening details" if language == "en" else "Reba ibisobanuro by'isuzuma"
    )
    with st.expander(details_label):
        render_metric_grid(
            [
                (base["results"]["screening_score"], f"{result.score:.0%}"),
                (base["results"]["data_completeness"], f"{result.completeness:.0%}"),
                (
                    "Assessment route" if language == "en" else "Inzira y'isuzuma",
                    "Complete assessment" if language == "en" else "Isuzuma rirambuye",
                ),
            ]
        )
        st.caption(copy["score_explainer"])

    st.info(base["safeguards"]["screening_warning"] + " " + base["safeguards"]["human_review"])
    st.subheader(copy["plan_title"])
    st.write(copy["plan_intro"])
    recommendations = suggest_support(get_answers(), language, positive)
    plans = build_action_plans(recommendations, language)
    plan_by_theme = {plan.theme: plan for plan in plans}
    recommendation_by_theme = {item.theme: item for item in recommendations}
    priority_theme = st.selectbox(
        copy["priority_question"],
        [plan.theme for plan in plans],
        format_func=lambda theme: plan_by_theme[theme].title,
        key="action_priority_theme",
    )
    ordered_plans = [plan_by_theme[priority_theme], *[plan for plan in plans if plan.theme != priority_theme]]

    primary_plan = ordered_plans[0]
    recommendation = recommendation_by_theme[primary_plan.theme]
    with st.container(border=True):
        st.caption(copy["priority"] + " 1")
        st.subheader(primary_plan.title)
        st.write(primary_plan.outcome)
        st.caption(f"{copy['reason_label']}: {recommendation.reason}")
        st.markdown(f"**{copy['official_route']}:** {primary_plan.service}")
        for step_index, step in enumerate(primary_plan.steps, start=1):
            st.checkbox(step, key=f"action_done_{primary_plan.theme}_{step_index}")
        with st.expander(copy["prepare_label"]):
            for item in primary_plan.prepare:
                st.markdown(f"- {item}")
        link_columns = st.columns(len(primary_plan.links))
        for link_column, link in zip(link_columns, primary_plan.links):
            with link_column:
                st.link_button(link.label, link.url, use_container_width=True)

    alternatives_label = "Other support options" if language == "en" else "Izindi nzira z'ubufasha"
    with st.expander(alternatives_label):
        for plan in ordered_plans[1:]:
            st.markdown(f"**{plan.title}** — {plan.outcome}")
            st.caption(f"{copy['official_route']}: {plan.service}")

    st.caption(copy["eligibility_note"])
    st.markdown(f"<div class='notice'>{copy['complete_route']}</div>", unsafe_allow_html=True)

    def open_opportunities() -> None:
        st.session_state.main_page = "opportunities"

    opportunity_copy = OPPORTUNITY_COPY[language]
    st.button(
        opportunity_copy["screening_cta"],
        type="primary",
        use_container_width=True,
        on_click=open_opportunities,
    )

    summary = summary_text(result, ordered_plans, base, copy)
    left, right = st.columns(2)
    with left:
        st.download_button(
            base["results"]["download_summary"],
            data=summary.encode("utf-8"),
            file_name="inzira_screening_summary.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with right:
        if st.button(
            base["general"]["restart"], type="primary", use_container_width=True
        ):
            reset_assessment()
            st.rerun()


def render_landing(base: dict[str, Any], copy: dict[str, str]) -> None:
    language = st.session_state.language
    trust_labels = (
        ("Bilingual", "No name or ID", "3–5 minutes")
        if language == "en"
        else ("Indimi ebyiri", "Nta zina cyangwa indangamuntu", "Iminota 3–5")
    )
    trust_html = "".join(
        f"<span class='trust-chip'>✓ {escape(label)}</span>" for label in trust_labels
    )
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-grid">
            <div>
              <div class="eyebrow">{copy['hero_eyebrow']}</div>
              <h1>{copy['hero_title']}</h1>
              <p>{copy['hero_body']}</p>
              <div class="trust-row">{trust_html}</div>
            </div>
            <div class="path-mark" aria-hidden="true"><div class="path-orbit"></div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        copy["hero_cta"],
        type="primary",
        use_container_width=True,
        key="start_assessment",
    ):
        st.session_state.assessment_started = True
        st.session_state.assessment_step = 0
        st.rerun()
    st.caption(base["safeguards"]["screening_warning"])


def render_check(
    bundle: RuntimeBundle,
    language: str,
    base: dict[str, Any],
    copy: dict[str, str],
) -> None:
    if st.session_state.assessment_result is not None:
        render_result(bundle, language, base, copy)
    elif st.session_state.assessment_started:
        render_step(bundle, language, base, copy)
    else:
        render_landing(base, copy)


def render_evidence(
    bundle: RuntimeBundle, language: str, base: dict[str, Any], copy: dict[str, str]
) -> None:
    st.title(copy["evidence_title"])
    st.write(copy["evidence_intro"])
    metrics = bundle.test_results["clean_test_metrics"]
    cols = st.columns(4)
    values = [
        (copy["metric_macro"], metrics["macro_f1"]),
        (copy["metric_auc"], metrics["roc_auc"]),
        (copy["metric_recall"], metrics["vulnerable_recall"]),
        (copy["metric_accuracy"], metrics["accuracy"]),
    ]
    for column, (label, value) in zip(cols, values):
        with column:
            st.metric(label, f"{value:.1%}")
    st.caption(
        "Locked test set: 2,259 households · 95% CI for macro F1: 0.661–0.704 · 95% CI for ROC AUC: 0.773–0.813"
    )

    image_path = bundle.root / "evaluation" / "inzira_lite_final_test_evaluation.png"
    if image_path.exists():
        st.image(image_path, caption="Locked-test evaluation and missing-answer robustness")

    col1, col2, col3 = st.columns(3)
    cards = [
        (copy["robust_title"], copy["robust_body"]),
        (copy["fairness_title"], copy["fairness_body"]),
        (copy["role_title"], copy["role_body"]),
    ]
    for column, (title, body) in zip((col1, col2, col3), cards):
        with column:
            st.markdown(
                f"<div class='support-card'><h4>{title}</h4><p>{body}</p></div>",
                unsafe_allow_html=True,
            )

    with st.expander("Fairness audit details"):
        for limitation in bundle.fairness_policy["known_limitations"]:
            st.markdown(f"**{limitation['dimension']} — {limitation['severity']}**")
            st.write(limitation["finding"])
            st.caption(limitation["ui_response"])

    model_card = (bundle.root / "docs" / "MODEL_CARD.md").read_bytes()
    st.download_button(
        "Download model card",
        data=model_card,
        file_name="INZIRA_LITE_MODEL_CARD.md",
        mime="text/markdown",
    )


def render_about(
    bundle: RuntimeBundle,
    language: str,
    base: dict[str, Any],
    copy: dict[str, str],
) -> None:
    st.title(copy["about_title"])
    st.write(copy["about_body"])
    metrics = bundle.test_results["clean_test_metrics"]
    render_metric_grid(
        [
            ("Simple question groups" if language == "en" else "Ibyiciro by'ibibazo", "12"),
            (copy["metric_auc"], f"{metrics['roc_auc']:.1%}"),
            ("Direct identifiers" if language == "en" else "Amakuru aranga umuntu", "0"),
        ]
    )

    journey_title = "One connected journey" if language == "en" else "Urugendo rumwe ruhujwe"
    journey_body = (
        "A household can complete a quick screen, find relevant official pathways and track a referral without entering a name or national ID."
        if language == "en"
        else "Urugo rushobora gukora isuzuma ryihuse, kubona inzira zemewe no gukurikirana referral rudatanze izina cyangwa indangamuntu."
    )
    st.markdown(f"<div class='section-card'><h3>{journey_title}</h3><p>{journey_body}</p></div>", unsafe_allow_html=True)

    with st.expander(copy["evidence_title"]):
        st.write(copy["evidence_intro"])
        evidence_columns = st.columns(3)
        for column, (label, value) in zip(
            evidence_columns,
            [
                (copy["metric_macro"], metrics["macro_f1"]),
                (copy["metric_recall"], metrics["vulnerable_recall"]),
                (copy["metric_accuracy"], metrics["accuracy"]),
            ],
        ):
            with column:
                st.metric(label, f"{value:.1%}")
        model_card = (bundle.root / "docs" / "MODEL_CARD.md").read_bytes()
        st.download_button(
            "Download model card" if language == "en" else "Bika model card",
            data=model_card,
            file_name="INZIRA_LITE_MODEL_CARD.md",
            mime="text/markdown",
        )

    safeguards_title = "Safeguards and limits" if language == "en" else "Uburinzi n'imbogamizi"
    with st.expander(safeguards_title):
        st.write(copy["role_body"])
        st.write(copy["fairness_body"])
        st.caption(copy["draft_translation"])


def opportunity_plan_text(
    matches: list[OpportunityMatch], language: str, copy: dict[str, Any]
) -> str:
    heading = "INZIRA AI — OPPORTUNITY PLAN" if language == "en" else "INZIRA AI — GAHUNDA Y'AMAHIRWE"
    lines = [heading, "", copy["results_intro"], copy["verified"]]
    for rank, match in enumerate(matches, start=1):
        opportunity = match.opportunity
        lines.extend(
            [
                "",
                f"{rank}. {opportunity.title(language)} — {copy['fit']}: {match.score}/100",
                f"{copy['provider']}: {opportunity.provider}",
                opportunity.summary(language),
                "",
                copy["why"] + ":",
                *(f"- {reason}" for reason in match.reasons),
                copy["check"] + ":",
                *(f"- {item}" for item in opportunity.eligibility(language)),
                copy["availability"] + ": " + opportunity.availability(language),
                copy["next"] + ":",
                *(f"  {index}. {step}" for index, step in enumerate(opportunity.next_steps(language), start=1)),
                f"{copy['official']}: {opportunity.apply_url}",
                f"{copy['source']}: {opportunity.source_url}",
            ]
        )
    return "\n".join(lines)


def _restore_opportunity_widget(field: str) -> None:
    widget_key = f"opp_{field}"
    if widget_key not in st.session_state:
        value = st.session_state.opportunity_draft[field]
        st.session_state[widget_key] = list(value) if isinstance(value, tuple) else value


def _save_opportunity_draft(fields: tuple[str, ...]) -> None:
    draft = dict(st.session_state.opportunity_draft)
    for field in fields:
        value = st.session_state.get(f"opp_{field}", draft[field])
        draft[field] = tuple(value) if isinstance(value, list) else value
    st.session_state.opportunity_draft = draft


def render_opportunity_matcher(language: str) -> None:
    copy = OPPORTUNITY_COPY[language]
    render_page_intro(copy["kicker"], copy["title"], copy["body"])
    st.caption(copy["catalogue_note"] + " " + copy["verified"])

    step = st.session_state.opportunity_step
    if step < 3:
        step_names = (
            ("Goal", "Profile and skills", "Support and access")
            if language == "en"
            else ("Intego", "Icyiciro n'ubumenyi", "Ubufasha n'uko wabugeraho")
        )
        st.progress((step + 1) / 3, text=f"{step + 1}/3 · {step_names[step]}")

    if step == 0:
        _restore_opportunity_widget("goals")
        with st.container(border=True):
            st.subheader(copy["goal_label"])
            st.multiselect(
                copy["goal_label"],
                list(copy["goals"]),
                format_func=lambda value: copy["goals"][value],
                key="opp_goals",
                label_visibility="collapsed",
            )
            if st.button(
                "Continue →" if language == "en" else "Komeza →",
                type="primary",
                use_container_width=True,
                key="opp_goal_continue",
            ):
                if not st.session_state.opp_goals:
                    st.error(copy["required"])
                else:
                    _save_opportunity_draft(("goals",))
                    st.session_state.opportunity_step = 1
                    st.rerun()
        return

    if step == 1:
        _restore_opportunity_widget("participant_profiles")
        _restore_opportunity_widget("skills")
        with st.container(border=True):
            st.subheader(copy["profile_label"])
            st.multiselect(
                copy["profile_label"],
                list(copy["profiles"]),
                format_func=lambda value: copy["profiles"][value],
                key="opp_participant_profiles",
            )
            st.multiselect(
                copy["skills_label"],
                list(copy["skills"]),
                format_func=lambda value: copy["skills"][value],
                key="opp_skills",
            )
            back_column, next_column = st.columns(2)
            with back_column:
                if st.button(
                    "← Back" if language == "en" else "← Subira inyuma",
                    use_container_width=True,
                    key="opp_profile_back",
                ):
                    _save_opportunity_draft(("participant_profiles", "skills"))
                    st.session_state.opportunity_step = 0
                    st.rerun()
            with next_column:
                if st.button(
                    "Continue →" if language == "en" else "Komeza →",
                    type="primary",
                    use_container_width=True,
                    key="opp_profile_continue",
                ):
                    if not st.session_state.opp_participant_profiles:
                        st.error(copy["required"])
                    else:
                        _save_opportunity_draft(("participant_profiles", "skills"))
                        st.session_state.opportunity_step = 2
                        st.rerun()
        return

    if step == 2:
        for field in ("support_types", "access_mode", "readiness"):
            _restore_opportunity_widget(field)
        with st.container(border=True):
            st.subheader(copy["support_label"])
            st.multiselect(
                copy["support_label"],
                list(copy["supports"]),
                format_func=lambda value: copy["supports"][value],
                key="opp_support_types",
            )
            st.radio(
                copy["access_label"],
                list(copy["access"]),
                format_func=lambda value: copy["access"][value],
                key="opp_access_mode",
            )
            st.radio(
                copy["readiness_label"],
                list(copy["readiness"]),
                format_func=lambda value: copy["readiness"][value],
                key="opp_readiness",
            )
            back_column, submit_column = st.columns(2)
            with back_column:
                if st.button(
                    "← Back" if language == "en" else "← Subira inyuma",
                    use_container_width=True,
                    key="opp_support_back",
                ):
                    _save_opportunity_draft(("support_types", "access_mode", "readiness"))
                    st.session_state.opportunity_step = 1
                    st.rerun()
            with submit_column:
                if st.button(
                    copy["match_button"],
                    type="primary",
                    use_container_width=True,
                    key="opp_match_submit",
                ):
                    _save_opportunity_draft(("support_types", "access_mode", "readiness"))
                    draft = st.session_state.opportunity_draft
                    st.session_state.opportunity_profile = {
                        "goals": tuple(draft["goals"]),
                        "participant_profiles": tuple(draft["participant_profiles"]),
                        "skills": tuple(draft["skills"]),
                        "support_types": tuple(draft["support_types"]),
                        "access_mode": draft["access_mode"],
                        "readiness": draft["readiness"],
                    }
                    st.session_state.opportunity_step = 3
                    st.rerun()
        return

    saved_profile = st.session_state.opportunity_profile
    if not saved_profile:
        st.session_state.opportunity_step = 0
        st.rerun()

    edit_label = "Edit answers" if language == "en" else "Hindura ibisubizo"
    if st.button(edit_label, key="opp_edit_answers"):
        st.session_state.opportunity_step = 0
        st.rerun()

    profile = MatchProfile(**saved_profile)
    household_answers = get_answers()
    has_household_context = any(
        household_answers.get(field) is not None
        for field in ("agricultural_activity", "wage_employment", "nonfarm_business")
    )
    matches = rank_opportunities(
        get_opportunities(),
        profile,
        household_answers if has_household_context else None,
        language,
    )
    visible_matches = [match for match in matches if match.score >= 30][:3]
    if not visible_matches:
        visible_matches = matches[:3]

    st.subheader(copy["results_title"])
    st.write(copy["results_intro"])
    st.info(copy["application_note"])
    st.caption(copy["context_used"] if has_household_context else copy["context_not_used"])

    def open_case_tracker(opportunity_id: str) -> None:
        st.session_state.case_opportunity_id = opportunity_id
        st.session_state.case_create_opportunity = opportunity_id
        st.session_state.staff_section = "new"
        st.session_state.main_page = "impact"

    for rank, match in enumerate(visible_matches, start=1):
        opportunity = match.opportunity
        with st.container(border=True):
            st.markdown(
                (
                    "<div style='display:flex;justify-content:space-between;gap:1rem;align-items:flex-start'>"
                    "<div>"
                    f"<div class='question-kicker'>#{rank} · {escape(opportunity.provider)}</div>"
                    f"<h3 style='margin:.15rem 0 .4rem'>{escape(opportunity.title(language))}</h3>"
                    f"<p style='margin:0;color:var(--muted)'>{escape(opportunity.summary(language))}</p>"
                    "</div>"
                    f"<span class='trust-chip' style='white-space:nowrap'>{escape(copy['fit'])} {match.score}/100</span>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            with st.expander(copy["why"], expanded=rank == 1):
                for reason in match.reasons:
                    st.markdown(f"- {reason}")
                st.markdown(f"**{copy['check']}**")
                for item in opportunity.eligibility(language):
                    st.markdown(f"- {item}")
                st.caption(f"{copy['availability']}: {opportunity.availability(language)}")
            with st.expander(copy["next"]):
                for index, next_step in enumerate(opportunity.next_steps(language), start=1):
                    st.markdown(f"{index}. {next_step}")
                st.markdown(f"**{copy['caution']}**")
                for caution in match.cautions:
                    st.markdown(f"- {caution}")

            link_one, link_two = st.columns(2)
            with link_one:
                st.link_button(copy["official"], opportunity.apply_url, use_container_width=True)
            with link_two:
                st.link_button(copy["source"], opportunity.source_url, use_container_width=True)
            shortlist, tracker = st.columns(2)
            with shortlist:
                st.checkbox(copy["shortlist"], key=f"opp_shortlist_{opportunity.id}")
            with tracker:
                st.button(
                    IMPACT_COPY[language]["track"],
                    key=f"track_{opportunity.id}",
                    use_container_width=True,
                    on_click=open_case_tracker,
                    args=(opportunity.id,),
                )

    shortlisted = [
        match
        for match in visible_matches
        if st.session_state.get(f"opp_shortlist_{match.opportunity.id}")
    ]
    plan_matches = shortlisted or visible_matches[:3]
    st.download_button(
        copy["download"],
        data=opportunity_plan_text(plan_matches, language, copy).encode("utf-8"),
        file_name="inzira_opportunity_plan.txt",
        mime="text/plain",
        use_container_width=True,
    )


def _case_screening_route(language: str) -> str:
    result = st.session_state.assessment_result
    if not result:
        return "not_completed"
    if result["elevated_risk"]:
        return "complete_assessment_recommended"
    return "screened_lower_risk_complete_assessment_still_available"


def render_staff_create(
    language: str,
    copy: dict[str, Any],
    opportunities: list[Any],
    opportunities_by_id: dict[str, Any],
    store: MongoCaseStore | None,
    actor: str,
) -> None:
    records: list[CaseRecord] = st.session_state.case_records
    st.write(copy["create_intro"])
    selected_id = st.session_state.case_opportunity_id
    if selected_id not in opportunities_by_id:
        selected_id = opportunities[0].id
    if st.session_state.get("case_create_opportunity") not in opportunities_by_id:
        st.session_state.case_create_opportunity = selected_id
    with st.form("create_case_form"):
        opportunity_id = st.selectbox(
            copy["opportunity"],
            [item.id for item in opportunities],
            format_func=lambda value: opportunities_by_id[value].title(language),
            key="case_create_opportunity",
        )
        next_followup = st.date_input(
            copy["followup"],
            value=date.today() + timedelta(days=7),
            key="case_create_followup",
        )
        create_submitted = st.form_submit_button(
            copy["create"], type="primary", use_container_width=True
        )
    screening_route = _case_screening_route(language)
    st.caption(
        copy["screening_context"]
        if screening_route != "not_completed"
        else copy["no_screening"]
    )
    if create_submitted:
        opportunity = opportunities_by_id[opportunity_id]
        answers = get_answers()
        record = create_case_record(
            opportunity_id=opportunity.id,
            opportunity_title=opportunity.title(language),
            provider=opportunity.provider,
            province=str(answers.get("province") or "unknown"),
            household_size=answers.get("household_members"),
            screening_route=screening_route,
            next_followup=next_followup.isoformat(),
        )
        try:
            if store is not None:
                store.create_record(record, actor=actor)
            st.session_state.case_records = [record, *records]
            st.success(f"{copy['created']}: {record.case_id}")
        except CaseStoreError as exc:
            st.error(str(exc))


def render_staff_update(
    copy: dict[str, Any], store: MongoCaseStore | None, actor: str
) -> None:
    records: list[CaseRecord] = st.session_state.case_records
    if not records:
        st.info(copy["empty"])
        return

    st.caption(copy["decision_note"])
    record_ids = [record.case_id for record in records]

    def sync_case_form() -> None:
        case_id = st.session_state.case_update_id
        record = next(item for item in records if item.case_id == case_id)
        st.session_state.case_update_status = record.status
        st.session_state.case_update_outcome = record.outcome
        st.session_state.case_update_barrier = record.barrier
        st.session_state.case_update_followup = (
            datetime.strptime(record.next_followup, "%Y-%m-%d").date()
            if record.next_followup
            else date.today() + timedelta(days=7)
        )

    selected_case_id = st.selectbox(
        copy["select_case"],
        record_ids,
        key="case_update_id",
        on_change=sync_case_form,
    )
    selected_case = next(record for record in records if record.case_id == selected_case_id)
    st.caption(f"{selected_case.opportunity_title} · {selected_case.provider}")
    with st.form("update_case_form"):
        status_options = list(copy["statuses"])
        status = st.selectbox(
            copy["status"],
            status_options,
            index=status_options.index(selected_case.status),
            format_func=lambda value: copy["statuses"][value],
            key="case_update_status",
        )
        outcome_options = list(copy["outcomes"])
        outcome = st.selectbox(
            copy["outcome"],
            outcome_options,
            index=outcome_options.index(selected_case.outcome),
            format_func=lambda value: copy["outcomes"][value],
            key="case_update_outcome",
        )
        barrier_options = list(copy["barriers"])
        barrier = st.selectbox(
            copy["barrier"],
            barrier_options,
            index=barrier_options.index(selected_case.barrier),
            format_func=lambda value: copy["barriers"][value],
            key="case_update_barrier",
        )
        current_followup = (
            datetime.strptime(selected_case.next_followup, "%Y-%m-%d").date()
            if selected_case.next_followup
            else date.today() + timedelta(days=7)
        )
        next_followup = st.date_input(
            copy["followup"], value=current_followup, key="case_update_followup"
        )
        update_submitted = st.form_submit_button(
            copy["save"], type="primary", use_container_width=True
        )
    if update_submitted:
        updated = update_case_record(
            selected_case,
            status=status,
            outcome=outcome,
            barrier=barrier,
            next_followup=next_followup.isoformat(),
        )
        try:
            if store is not None:
                store.update_record(updated, actor=actor)
            st.session_state.case_records = [
                updated if item.case_id == selected_case_id else item for item in records
            ]
            st.success(copy["saved"])
        except CaseStoreError as exc:
            st.error(str(exc))


def render_staff_dashboard(language: str, copy: dict[str, Any]) -> None:
    records: list[CaseRecord] = st.session_state.case_records
    summary = impact_summary(records)
    render_metric_grid(
        [
            (copy["total"], summary["total"]),
            (copy["contacted"], summary["contacted"]),
            (copy["applications"], summary["applications"]),
            (copy["positive"], summary["positive_outcomes"]),
            (copy["due"], summary["followups_due"]),
        ]
    )
    st.caption(copy["impact_note"])

    if not records:
        st.info(copy["empty"])
        return

    status_column, pathway_column = st.columns(2)
    with status_column:
        st.subheader(copy["status_chart"])
        status_counts = count_by(records, "status")
        status_frame = pd.DataFrame(
            {
                copy["status"]: [copy["statuses"][key] for key in status_counts],
                copy["total"]: list(status_counts.values()),
            }
        ).set_index(copy["status"])
        st.bar_chart(status_frame)
    with pathway_column:
        st.subheader(copy["pathway_chart"])
        pathway_counts = count_by(records, "opportunity_title")
        st.bar_chart(
            pd.DataFrame(
                {copy["total"]: list(pathway_counts.values())},
                index=list(pathway_counts),
            )
        )

    due_records = [
        record
        for record in records
        if record.next_followup
        and record.next_followup <= date.today().isoformat()
        and record.status not in {"closed", "accepted"}
    ]
    if due_records:
        st.subheader(copy["due_title"])
        st.dataframe(
            [
                {
                    copy["case_id"]: record.case_id,
                    copy["opportunity"]: record.opportunity_title,
                    copy["followup"]: record.next_followup,
                    copy["status"]: copy["statuses"][record.status],
                }
                for record in due_records
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("All referrals" if language == "en" else "Referral zose")
    search = st.text_input(
        "Search by case ID, pathway or provider"
        if language == "en"
        else "Shakisha nomero ya dosiye, inzira cyangwa urwego",
        key="admin_case_search",
        placeholder="IA-2026...",
    ).lower().strip()
    filtered_records = [
        record
        for record in records
        if not search
        or search
        in " ".join(
            (record.case_id, record.opportunity_title, record.provider)
        ).lower()
    ]
    st.dataframe(
        [
            {
                copy["case_id"]: record.case_id,
                copy["opportunity"]: record.opportunity_title,
                copy["status"]: copy["statuses"][record.status],
                copy["outcome"]: copy["outcomes"][record.outcome],
                copy["followup"]: record.next_followup,
            }
            for record in filtered_records
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_staff_data(
    copy: dict[str, Any], store: MongoCaseStore | None, actor: str
) -> None:
    records: list[CaseRecord] = st.session_state.case_records
    st.write(copy["data_note"])
    st.download_button(
        copy["download"],
        data=records_to_csv(records).encode("utf-8"),
        file_name="inzira_anonymous_case_records.csv",
        mime="text/csv",
        use_container_width=True,
    )
    with st.form("import_case_form"):
        upload = st.file_uploader(copy["upload"], type=["csv"], key="case_import_upload")
        import_submitted = st.form_submit_button(copy["import"])
    if import_submitted and upload is not None:
        try:
            imported = records_from_csv(upload.getvalue().decode("utf-8-sig"))
            if store is not None:
                store.import_records(imported, actor=actor)
                st.session_state.case_records = store.list_records()
            else:
                st.session_state.case_records = imported
            st.success(f"{copy['imported']}: {len(imported)}")
        except (UnicodeDecodeError, ValueError, CaseStoreError) as exc:
            st.error(f"{copy['import_error']}: {exc}")


def render_admin_opportunities(language: str, opportunities: list[Any]) -> None:
    st.subheader(
        "Reviewed opportunity directory"
        if language == "en"
        else "Urutonde rw'amahirwe yagenzuwe"
    )
    st.caption(
        "These are reviewed pathways, not a live vacancy feed. Applicants submit through the official provider; administrators do not approve applications."
        if language == "en"
        else "Izi ni inzira zagenzuwe, si urutonde ruhita ruvugururwa rw'imyanya. Usaba anyura ku rwego rwemewe; admin ntabwo yemeza ubusabe."
    )
    frame = pd.DataFrame(
        [
            {
                "ID": item.id,
                "Provider": item.provider,
                "Opportunity": item.title(language),
                "Official route": item.apply_url,
                "Source": item.source_url,
            }
            for item in opportunities
        ]
    )
    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Official route": st.column_config.LinkColumn("Official route"),
            "Source": st.column_config.LinkColumn("Source"),
        },
    )
    st.info(
        "For safety, catalogue changes are code-reviewed before deployment. Live editing is intentionally disabled in this release."
        if language == "en"
        else "Ku bw'umutekano, impinduka kuri uru rutonde zibanza kugenzurwa muri code mbere yo gushyirwa ku rubuga."
    )


def render_admin_settings(
    language: str, actor: str, store: MongoCaseStore | None
) -> None:
    st.subheader("Admin settings" if language == "en" else "Igenamiterere rya admin")
    database_status = (
        "Connected"
        if store is not None and store.health()
        else "Automated test session"
    )
    render_metric_grid(
        [
            ("Signed-in admin" if language == "en" else "Admin winjiye", actor),
            ("Database", database_status),
            (
                "Data scope" if language == "en" else "Ubwoko bw'amakuru",
                "Anonymous referrals",
            ),
        ]
    )
    if store is not None:
        st.subheader(
            "Recent admin activity"
            if language == "en"
            else "Ibikorwa bya admin biheruka"
        )
        try:
            activity = store.recent_audit()
            if activity:
                st.dataframe(activity, use_container_width=True, hide_index=True)
            else:
                st.caption(
                    "No admin activity recorded yet."
                    if language == "en"
                    else "Nta bikorwa bya admin birandikwa kugeza ubu."
                )
        except CaseStoreError as exc:
            st.error(str(exc))
        st.button(
            "Sign out" if language == "en" else "Sohoka",
            use_container_width=True,
            on_click=st.logout,
        )
    else:
        st.caption("Authentication and MongoDB are bypassed only by the automated UI test.")


def render_impact_dashboard(language: str) -> None:
    copy = IMPACT_COPY[language]
    access = require_admin_access(language)
    if access is None:
        return
    actor, store = access
    opportunities = get_opportunities()
    opportunities_by_id = {item.id: item for item in opportunities}

    if store is not None:
        try:
            st.session_state.case_records = store.list_records()
        except CaseStoreError as exc:
            st.error(str(exc))
            return

    render_page_intro(copy["kicker"], copy["title"], copy["body"])
    st.warning(copy["role_notice"])
    demo_label = (
        f"Protected admin · {actor}"
        if language == "en"
        else f"Admin urinzwe · {actor}"
    )
    st.markdown(f"<span class='staff-badge'>{escape(demo_label)}</span>", unsafe_allow_html=True)
    st.caption(copy["flow"])
    with st.expander(
        "Privacy and production requirements"
        if language == "en"
        else "Ibanga n'ibisabwa mu ikoreshwa nyaryo"
    ):
        st.write(copy["privacy"])
        st.write(copy["storage"])

    section_labels = {
        "new": copy["tab_new"],
        "update": copy["tab_update"],
        "dashboard": copy["tab_dashboard"],
        "opportunities": copy["tab_opportunities"],
        "data": copy["tab_data"],
        "settings": copy["tab_settings"],
    }
    if st.session_state.staff_section not in section_labels:
        st.session_state.staff_section = "dashboard"
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
            language, copy, opportunities, opportunities_by_id, store, actor
        )
    elif section == "update":
        render_staff_update(copy, store, actor)
    elif section == "dashboard":
        render_staff_dashboard(language, copy)
    elif section == "opportunities":
        render_admin_opportunities(language, opportunities)
    elif section == "data":
        render_staff_data(copy, store, actor)
    else:
        render_admin_settings(language, actor, store)


def main() -> None:
    inject_styles()
    initialize_state()
    try:
        bundle = get_bundle()
    except Exception as exc:
        st.error("The verified model bundle could not be loaded.")
        st.code(str(exc))
        st.stop()

    language = render_sidebar(bundle)
    base = bundle.translations[language]
    copy = EXTRA_COPY[language]
    page = render_header_navigation(copy)
    st.write("")

    if page == "check":
        render_check(bundle, language, base, copy)
    elif page == "opportunities":
        render_opportunity_matcher(language)
    elif page == "impact":
        render_impact_dashboard(language)
    else:
        render_about(bundle, language, base, copy)

    st.markdown(f"<div class='app-footer'>{copy['footer']}</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()

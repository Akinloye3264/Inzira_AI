from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from src.inzira.admin_dashboard import inject_admin_styles, render_admin_dashboard
from src.inzira.case_store import CaseStoreError, NeonCaseStore
from src.inzira.firebase_auth import (
    FirebaseAuthError,
    FirebaseSession,
    refresh_session,
    sign_in_with_password,
)


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(
    page_title="Inzira AI Admin",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _secret_section(name: str) -> dict[str, Any]:
    try:
        return dict(st.secrets[name]) if name in st.secrets else {}
    except (FileNotFoundError, KeyError):
        return {}


def configuration() -> tuple[str, str, str, set[str]]:
    firebase = _secret_section("firebase")
    neon = _secret_section("neon")
    admin = _secret_section("admin")
    api_key = str(os.getenv("FIREBASE_WEB_API_KEY") or firebase.get("api_key", "")).strip()
    project_id = str(os.getenv("FIREBASE_PROJECT_ID") or firebase.get("project_id", "")).strip()
    database_url = str(os.getenv("DATABASE_URL") or neon.get("database_url", "")).strip()
    env_emails = [item.strip() for item in os.getenv("ADMIN_EMAILS", "").split(",") if item.strip()]
    secret_emails = [str(item).strip() for item in admin.get("allowed_emails", [])]
    allowed_emails = {item.lower() for item in [*env_emails, *secret_emails] if item}
    return api_key, project_id, database_url, allowed_emails


@st.cache_resource(show_spinner=False)
def get_store(database_url: str) -> NeonCaseStore:
    return NeonCaseStore(database_url)


def render_login(api_key: str, allowed_emails: set[str]) -> None:
    inject_admin_styles()
    st.markdown(
        """
        <div class="admin-topbar">
          <div class="admin-brand"><div class="admin-mark">IA</div>
          <div><div class="admin-title">Inzira AI Admin</div>
          <div class="admin-subtitle">AUTHORIZED STAFF ONLY</div></div></div>
        </div>
        <div class="admin-hero">
          <div class="eyebrow">SECURE ADMINISTRATOR ACCESS</div>
          <h1>Welcome back</h1>
          <p>Sign in to review anonymous referrals, coordinate follow-ups and record provider-reported outcomes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, centre, right = st.columns([1, 1.25, 1])
    with centre:
        with st.form("firebase_admin_login"):
            st.subheader("Administrator sign in")
            email = st.text_input("Email address", placeholder="admin@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in securely", type="primary", width="stretch")
        if submitted:
            if not email.strip() or not password:
                st.error("Enter your administrator email and password.")
                return
            try:
                session = sign_in_with_password(api_key, email, password)
                if session.email not in allowed_emails:
                    st.error("This Firebase account is not authorized for the Inzira admin workspace.")
                    return
                st.session_state.firebase_session = session
                st.rerun()
            except FirebaseAuthError as exc:
                st.error(str(exc))
        st.caption("No public registration · Access is controlled by Firebase and the administrator allowlist.")


def main() -> None:
    api_key, project_id, database_url, allowed_emails = configuration()
    missing = [
        label for label, value in (
            ("FIREBASE_WEB_API_KEY", api_key),
            ("FIREBASE_PROJECT_ID", project_id),
            ("DATABASE_URL", database_url),
            ("ADMIN_EMAILS", allowed_emails),
        ) if not value
    ]
    if missing:
        inject_admin_styles()
        st.error("Admin configuration is incomplete.")
        st.code("Missing: " + ", ".join(missing))
        st.info("Add the missing values to `.env` locally or Streamlit Secrets when deployed.")
        st.stop()

    current = st.session_state.get("firebase_session")
    if not isinstance(current, FirebaseSession):
        render_login(api_key, allowed_emails)
        return
    try:
        session = refresh_session(api_key, current)
    except FirebaseAuthError as exc:
        st.session_state.pop("firebase_session", None)
        st.error(str(exc))
        render_login(api_key, allowed_emails)
        return
    if session.email not in allowed_emails:
        st.session_state.pop("firebase_session", None)
        st.error("This account is not authorized for the Inzira admin workspace.")
        return
    st.session_state.firebase_session = session
    try:
        store = get_store(database_url)
    except CaseStoreError as exc:
        inject_admin_styles()
        st.error("The Neon database is unavailable.")
        st.caption(str(exc))
        return
    render_admin_dashboard(actor=session.email, store=store, project_root=PROJECT_ROOT)


if __name__ == "__main__":
    main()

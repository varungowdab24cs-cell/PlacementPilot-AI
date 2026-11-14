import sys
from pathlib import Path

import streamlit as st

# Streamlit executes this file as a script, so make the repository package
# importable when launched with the documented `streamlit run` command.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.components.layout import apply_theme, run_page
from frontend.pages import (
    analytics,
    assessment,
    dashboard,
    dsa_practice,
    learning_path,
    login,
    profile,
    settings,
    tutor,
)

st.set_page_config(
    page_title="PlacementPilot AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


def _safe_page(renderer):
    def render_page() -> None:
        run_page(renderer)

    return render_page


if "access_token" not in st.session_state:
    navigation = st.navigation(
        [
            st.Page(
                _safe_page(login.render),
                title="Sign in",
                icon=":material/login:",
                url_path="sign-in",
            )
        ],
        position="hidden",
    )
    navigation.run()
else:
    with st.sidebar:
        st.markdown(
            '<div class="brand-lockup">'
            '<div class="brand-mark">PP</div>'
            '<div><div class="brand-name">PlacementPilot</div>'
            '<div class="brand-caption">adaptive preparation</div></div></div>',
            unsafe_allow_html=True,
        )
        st.caption("Workspace")
    navigation = st.navigation(
        [
            st.Page(
                _safe_page(dashboard.render),
                title="Dashboard",
                icon=":material/dashboard:",
                url_path="dashboard",
            ),
            st.Page(
                _safe_page(assessment.render),
                title="Benchmark Assessment",
                icon=":material/assignment:",
                url_path="benchmark-assessment",
            ),
            st.Page(
                _safe_page(learning_path.render),
                title="My Learning Path",
                icon=":material/route:",
                url_path="learning-path",
            ),
            st.Page(
                _safe_page(dsa_practice.render),
                title="DSA Practice",
                icon=":material/code:",
                url_path="dsa-practice",
            ),
            st.Page(
                _safe_page(tutor.render),
                title="AI Placement Tutor",
                icon=":material/forum:",
                url_path="ai-tutor",
            ),
            st.Page(
                _safe_page(analytics.render),
                title="My Analytics",
                icon=":material/analytics:",
                url_path="analytics",
            ),
            st.Page(
                _safe_page(profile.render),
                title="Student Profile",
                icon=":material/person:",
                url_path="profile",
            ),
            st.Page(
                _safe_page(settings.render),
                title="Settings",
                icon=":material/settings:",
                url_path="settings",
            ),
        ],
        position="sidebar",
    )
    with st.sidebar:
        st.divider()
        st.caption("Account")
        if st.button("Sign out", width="stretch"):
            st.session_state.clear()
            st.rerun()
    navigation.run()

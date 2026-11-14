import streamlit as st

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
        [st.Page(_safe_page(login.render), title="Sign in", icon=":material/login:")],
        position="hidden",
    )
    navigation.run()
else:
    with st.sidebar:
        st.markdown("## 🎯 PlacementPilot")
        st.caption("Adaptive placement preparation")
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    navigation = st.navigation(
        [
            st.Page(_safe_page(dashboard.render), title="Dashboard", icon=":material/dashboard:"),
            st.Page(
                _safe_page(assessment.render),
                title="Benchmark Assessment",
                icon=":material/assignment:",
            ),
            st.Page(
                _safe_page(learning_path.render),
                title="My Learning Path",
                icon=":material/route:",
            ),
            st.Page(_safe_page(dsa_practice.render), title="DSA Practice", icon=":material/code:"),
            st.Page(_safe_page(tutor.render), title="AI Placement Tutor", icon=":material/forum:"),
            st.Page(_safe_page(analytics.render), title="My Analytics", icon=":material/analytics:"),
            st.Page(_safe_page(profile.render), title="Student Profile", icon=":material/person:"),
            st.Page(_safe_page(settings.render), title="Settings", icon=":material/settings:"),
        ],
        position="sidebar",
    )
    navigation.run()

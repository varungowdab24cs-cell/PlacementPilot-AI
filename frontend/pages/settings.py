import os

import streamlit as st

from frontend.components.layout import page_header


def render() -> None:
    page_header("Settings", "Manage your workspace preferences and connection details.")
    st.subheader("Backend connection")
    st.text_input(
        "FastAPI base URL",
        value=os.getenv("BACKEND_URL", "http://127.0.0.1:8000"),
        disabled=True,
    )
    st.caption("Configure BACKEND_URL before starting Streamlit. API keys are never stored in the frontend.")
    st.subheader("Session")
    st.write("Your access token is kept in Streamlit session state for this browser session.")
    if st.button("Sign out", type="secondary"):
        st.session_state.clear()
        st.rerun()

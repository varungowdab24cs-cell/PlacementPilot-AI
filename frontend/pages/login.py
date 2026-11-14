import streamlit as st

from frontend.services.api_client import ApiClient, ApiError


def render() -> None:
    st.markdown(
        '<div class="hero"><h1>PlacementPilot AI</h1>'
        "<p>Your structured, adaptive placement preparation workspace.</p></div>",
        unsafe_allow_html=True,
    )
    login_tab, register_tab = st.tabs(["Sign in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            try:
                result = ApiClient().post(
                    "/auth/login",
                    json={"email": email, "password": password},
                )
                st.session_state.access_token = result["access_token"]
                st.session_state.page = "Dashboard"
                st.rerun()
            except ApiError as exc:
                st.error(exc.detail)

    with register_tab:
        with st.form("registration_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            department = st.text_input("Department")
            semester = st.number_input("Semester", min_value=1, max_value=20, value=1)
            languages = st.text_input("Preferred programming language")
            categories = st.text_input("Target company categories", placeholder="product, service")
            goals = st.text_area("Preparation goals")
            submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if submitted:
            try:
                ApiClient().post(
                    "/auth/register",
                    json={
                        "full_name": full_name,
                        "email": email,
                        "password": password,
                        "department": department or None,
                        "semester": semester,
                        "programming_language_preference": languages or None,
                        "target_company_categories": [
                            item.strip() for item in categories.split(",") if item.strip()
                        ],
                        "preparation_goals": goals or None,
                    },
                )
                st.success("Account created. You can now sign in.")
            except ApiError as exc:
                st.error(exc.detail)

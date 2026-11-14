import streamlit as st

from frontend.components.layout import page_header
from frontend.services.api_client import get_api_client


def render() -> None:
    api = get_api_client()
    profile = api.get("/students/me")
    page_header("Student profile", "Keep your preparation context current so recommendations stay relevant.")
    with st.form("profile_form"):
        full_name = st.text_input("Full name", value=profile.get("full_name", ""))
        department = st.text_input("Department", value=profile.get("department") or "")
        semester = st.number_input(
            "Semester",
            min_value=1,
            max_value=20,
            value=profile.get("semester") or 1,
        )
        language = st.text_input(
            "Preferred programming language",
            value=profile.get("programming_language_preference") or "",
        )
        categories = st.text_input(
            "Target company categories",
            value=", ".join(profile.get("target_company_categories") or []),
        )
        goals = st.text_area("Preparation goals", value=profile.get("preparation_goals") or "")
        submitted = st.form_submit_button("Save profile", type="primary")
    if submitted:
        api.patch(
            "/students/me",
            json={
                "full_name": full_name,
                "department": department or None,
                "semester": semester,
                "programming_language_preference": language or None,
                "target_company_categories": [
                    item.strip() for item in categories.split(",") if item.strip()
                ],
                "preparation_goals": goals or None,
            },
        )
        st.success("Profile updated.")

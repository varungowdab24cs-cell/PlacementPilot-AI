import streamlit as st

from frontend.components.formatting import label, percentage
from frontend.components.layout import metric_card, page_header
from frontend.services.api_client import get_api_client


def render() -> None:
    api = get_api_client()
    profile = api.get("/students/me")
    mastery = api.get("/adaptive/mastery")
    weak_topics = api.get("/adaptive/weak-topics")
    recommendations = api.get("/adaptive/recommendations")
    subjects = api.get("/subjects")
    topics = api.get("/topics")
    assessments = api.get("/assessments")
    assessment_history = api.get("/assessments/history")

    page_header("Good to see you", f"Welcome back, {profile['full_name']}. Keep your preparation moving.")
    columns = st.columns(4)
    with columns[0]:
        metric_card("Overall mastery", percentage(mastery.get("overall_score")), "Across classified topics")
    with columns[1]:
        metric_card("Topics tracked", str(mastery.get("total_topics", 0)), "Evidence in your profile")
    with columns[2]:
        metric_card("Weak topics", str(len(weak_topics)), "Prioritize these next")
    with columns[3]:
        metric_card("Recommended activities", str(len(recommendations)), "Deterministic adaptive plan")

    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Subject-wise mastery")
        topic_to_subject = {topic["id"]: topic["subject_id"] for topic in topics}
        subject_names = {subject["id"]: subject["name"] for subject in subjects}
        rows = []
        for topic in mastery.get("topics", []):
            rows.append(
                {
                    "Subject": subject_names.get(topic_to_subject.get(topic["topic_id"]), "Other"),
                    "Topic": topic["topic_name"],
                    "Mastery": topic["mastery_score"],
                    "Level": topic["mastery_level"],
                }
            )
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Complete an assessment or practice activity to build your mastery profile.")

    with right:
        st.subheader("Target placement categories")
        categories = profile.get("target_company_categories") or []
        if categories:
            st.write(" · ".join(categories))
        else:
            st.info("Add target categories from your profile.")
        st.subheader("Weak topics")
        if weak_topics:
            for topic in weak_topics[:5]:
                st.progress(
                    min(max((topic.get("mastery_score") or 0) / 100, 0.0), 1.0),
                    text=f"{topic['topic_name']} · {label(topic['mastery_level'])}",
                )
        else:
            st.success("No classified weak topics yet.")

    st.subheader("Recommended next activities")
    if recommendations:
        for recommendation in recommendations[:6]:
            with st.container(border=True):
                st.markdown(
                    f"**{recommendation['title']}** · `{recommendation['difficulty']}`"
                )
                st.caption(recommendation["rationale"])
    else:
        st.info("Your next activities will appear after the adaptive engine has evidence.")

    st.subheader("Recent assessment results")
    if assessment_history:
        st.dataframe(
            [
                {
                    "Assessment": item["assessment_title"],
                    "Score": percentage(item["score"]),
                    "Answered": item["answered_questions"],
                }
                for item in assessment_history[:5]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Complete a benchmark assessment to see recent results here.")

    st.subheader("Assessment catalog")
    if assessments:
        st.dataframe(
            [
                {
                    "Assessment": item["title"],
                    "Questions": item["question_count"],
                    "Description": item.get("description") or "",
                }
                for item in assessments
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Start a benchmark assessment from the Benchmark Assessment page.")
    else:
        st.info("No assessments are available yet. Seed or create questions and assessments first.")

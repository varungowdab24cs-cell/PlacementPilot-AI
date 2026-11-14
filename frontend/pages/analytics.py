import streamlit as st

from frontend.components.formatting import percentage
from frontend.components.layout import page_header
from frontend.services.api_client import get_api_client


def render() -> None:
    api = get_api_client()
    mastery = api.get("/adaptive/mastery")
    practice = api.get("/dsa/practice/stats")
    research = api.get("/research/student-analytics")
    page_header("My analytics", "Review the evidence behind your preparation progress.")
    columns = st.columns(4)
    values = [
        ("Overall mastery", percentage(mastery.get("overall_score"))),
        ("Classified topics", str(mastery.get("classified_topics", 0))),
        ("DSA solved", str(practice.get("solved", 0))),
        ("Practice time", f"{practice['average_solving_time_seconds']:.0f}s" if practice.get("average_solving_time_seconds") else "—"),
    ]
    for column, (name, value) in zip(columns, values):
        with column:
            from frontend.components.layout import metric_card

            metric_card(name, value)
    st.subheader("Pre-test and post-test")
    pre_post = {
        "Pre-test": research.get("pre_test_score"),
        "Post-test": research.get("post_test_score"),
    }
    observed_pre_post = {key: value for key, value in pre_post.items() if value is not None}
    if observed_pre_post:
        st.bar_chart(observed_pre_post)
    else:
        st.info("Pre-test and post-test scores appear after experiment-tagged assessments.")

    st.subheader("Assessment completion and timing")
    assessments = research.get("assessment_history", [])
    if assessments:
        st.dataframe(
            [
                {
                    "Assessment": item["assessment_title"],
                    "Phase": item.get("phase") or "Unassigned",
                    "Score": percentage(item["score"]),
                    "Completion": percentage(item["completion_rate"]),
                    "Avg. question time": (
                        f"{item['average_time_taken_seconds']:.1f}s"
                        if item["average_time_taken_seconds"] is not None
                        else "—"
                    ),
                }
                for item in assessments
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No completed assessment history is available yet.")

    topics = mastery.get("topics", [])
    st.subheader("Topic progress")
    if not topics:
        st.info("No topic evidence is available yet.")
        return
    observed_topics = {
        topic["topic_name"]: topic["mastery_score"]
        for topic in topics
        if topic["mastery_score"] is not None
    }
    if observed_topics:
        st.bar_chart(observed_topics)
    else:
        st.info("Topic scores remain unavailable until sufficient assessment evidence exists.")
    st.dataframe(
        [
            {
                "Topic": topic["topic_name"],
                "Mastery": percentage(topic["mastery_score"]),
                "Accuracy": percentage(topic["accuracy"]),
                "Consistency": percentage(topic["consistency"]),
                "Practice completion": percentage(topic["practice_completion"]),
                "Evidence": topic["assessment_count"],
            }
            for topic in topics
        ],
        use_container_width=True,
        hide_index=True,
    )
    timeline = research.get("topic_mastery_history", [])
    st.subheader("Mastery changes over time")
    observed_timeline = [
        {
            "Recorded": item["recorded_at"],
            "Topic": item["topic_name"],
            "Mastery": item["score"],
        }
        for item in timeline
        if item["score"] is not None
    ]
    if observed_timeline:
        st.dataframe(observed_timeline, use_container_width=True, hide_index=True)
    else:
        st.info("No sufficient mastery snapshots are available yet.")

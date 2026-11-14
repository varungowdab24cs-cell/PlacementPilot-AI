import streamlit as st

from frontend.components.formatting import label
from frontend.components.layout import metric_card, page_header
from frontend.services.api_client import get_api_client


def render() -> None:
    api = get_api_client()
    page_header("DSA practice", "Build confidence with curated LeetCode and Codeforces problems.")
    stats = api.get("/dsa/practice/stats")
    columns = st.columns(4)
    with columns[0]:
        metric_card("Solved", str(stats["solved"]), "Self-reported completions")
    with columns[1]:
        metric_card("Need help", str(stats["need_help"]), "Topics to revisit")
    with columns[2]:
        metric_card("Attempted", str(stats["attempted"]), "Practice history")
    with columns[3]:
        average = stats["average_solving_time_seconds"]
        metric_card("Average time", f"{average:.0f}s" if average else "—", "Reported solving time")

    left, middle, right = st.columns(3)
    with left:
        platform = st.selectbox("Platform", ["All", "leetcode", "codeforces"])
    with middle:
        difficulty = st.selectbox("Difficulty", ["All", "easy", "medium", "hard"])
    with right:
        topic_id = None
        topic_label = st.text_input("Topic ID (optional)", placeholder="e.g. 12")
        if topic_label.strip():
            try:
                topic_id = int(topic_label)
            except ValueError:
                st.warning("Topic ID must be numeric.")

    params = {}
    if platform != "All":
        params["platform"] = platform
    if difficulty != "All":
        params["difficulty"] = difficulty
    if topic_id:
        params["topic_id"] = topic_id
    problems = api.get("/dsa/problems/recommendations", params={**params, "limit": 30})
    st.caption(f"{len(problems)} recommendations match your current filters.")
    if not problems:
        st.info("No curated problems match these filters.")
        return
    for problem in problems:
        with st.container(border=True):
            title_col, action_col = st.columns([3, 1])
            with title_col:
                st.markdown(
                    f"**{problem['title']}** · `{label(problem['platform'])}` · "
                    f"`{label(problem['difficulty'])}`"
                )
                st.caption(f"{problem['topic_name']} · {problem.get('description') or ''}")
                st.link_button("Open official problem", problem["official_url"])
            with action_col:
                with st.form(f"problem_{problem['id']}_form"):
                    outcome = st.selectbox(
                        "Update status",
                        ["attempted", "solved", "need_help", "skipped"],
                        key=f"outcome_{problem['id']}",
                    )
                    seconds = st.number_input(
                        "Seconds",
                        min_value=0,
                        value=0,
                        step=30,
                        key=f"time_{problem['id']}",
                    )
                    submitted = st.form_submit_button("Save")
                if submitted:
                    api.post(
                        f"/dsa/problems/{problem['id']}/attempts",
                        json={
                            "outcome": outcome,
                            "solving_time_seconds": seconds or None,
                        },
                    )
                    st.success("Saved as self-reported practice.")
                    st.rerun()

    with st.expander("Recent practice history"):
        history = api.get("/dsa/practice/history")
        if history:
            st.dataframe(
                [
                    {
                        "Resource": item["resource_id"],
                        "Outcome": label(item["outcome"]),
                        "Time": (
                            f"{item['solving_time_seconds']}s"
                            if item["solving_time_seconds"] is not None
                            else "—"
                        ),
                        "Source": label(item["completion_source"]),
                        "Verified": "Yes" if item["verified"] else "No",
                    }
                    for item in history
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No external problem attempts recorded yet.")

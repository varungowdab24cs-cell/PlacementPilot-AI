import streamlit as st

from frontend.components.formatting import percentage
from frontend.components.layout import page_header
from frontend.services.api_client import ApiError, get_api_client


def render() -> None:
    api = get_api_client()
    page_header("My learning path", "Follow a focused sequence built from your topic-level evidence.")
    try:
        path = api.get("/adaptive/learning-path")
    except ApiError as exc:
        if exc.status_code == 404:
            st.info("Your learning path will appear after your first adaptive recalculation.")
            return
        raise
    st.progress(path["progress"] / 100, text=f"{percentage(path['progress'])} complete")
    st.caption(path.get("description") or "")
    if not path.get("items"):
        st.info("There are no activities in the active learning path.")
        return
    for item in path["items"]:
        status = "✅" if item["status"] == "completed" else "○"
        with st.container(border=True):
            st.markdown(f"**{status} {item['position']}. {item['title']}**")
            st.caption(
                f"{item['topic_name']} · {item['activity_type']} · {item['difficulty']}"
            )
            st.write(item["rationale"])
            if item["status"] != "completed":
                st.info("Complete this activity from Benchmark Assessment or DSA Practice.")

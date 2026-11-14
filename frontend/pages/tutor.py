import streamlit as st

from frontend.components.layout import page_header
from frontend.services.api_client import get_api_client


def render() -> None:
    api = get_api_client()
    page_header("AI placement tutor", "Ask for explanations, hints, aptitude help, or programming guidance.")
    sessions = api.get("/chat/sessions")
    if "chat_session_id" not in st.session_state and sessions:
        st.session_state.chat_session_id = sessions[0]["id"]

    with st.sidebar:
        st.markdown("### Conversations")
        if st.button("＋ New conversation", width="stretch"):
            session = api.post("/chat/sessions", json={"title": "Placement tutoring"})
            st.session_state.chat_session_id = session["id"]
            st.rerun()
        if sessions:
            choices = {session["id"]: session for session in sessions}
            current = st.session_state.get("chat_session_id", sessions[0]["id"])
            selected = st.selectbox(
                "Open conversation",
                list(choices),
                index=list(choices).index(current) if current in choices else 0,
                format_func=lambda item: choices[item].get("title") or f"Conversation {item}",
            )
            st.session_state.chat_session_id = selected

    if "chat_session_id" not in st.session_state:
        st.info("Start a conversation to begin tutoring.")
        return
    messages = api.get(f"/chat/sessions/{st.session_state.chat_session_id}/messages")
    for message in messages:
        with st.chat_message("assistant" if message["role"] == "assistant" else "user"):
            st.write(message["content"])

    st.markdown("**Suggested prompts**")
    prompt_columns = st.columns(3)
    prompts = [
        ("Explain a concept", "Explain binary search with a simple example."),
        ("Give me a hint", "Give me a hint for solving a two-pointer problem."),
        ("Practice aptitude", "Help me solve a percentage aptitude question."),
    ]
    for column, (caption, prompt) in zip(prompt_columns, prompts):
        with column:
            if st.button(caption, width="stretch"):
                st.session_state.tutor_prompt = prompt
    prompt = st.chat_input("Ask your placement tutor...")
    prompt = prompt or st.session_state.pop("tutor_prompt", None)
    if prompt:
        mode = st.selectbox(
            "Tutor mode",
            ["concept", "hint", "aptitude", "programming"],
            index=0,
        )
        response = api.post(
            f"/chat/sessions/{st.session_state.chat_session_id}/messages",
            json={"message": prompt, "mode": mode},
        )
        st.chat_message("user").write(prompt)
        with st.chat_message("assistant"):
            st.write(response["answer"])
            if response.get("suggested_actions"):
                st.caption("Next steps: " + " · ".join(response["suggested_actions"]))

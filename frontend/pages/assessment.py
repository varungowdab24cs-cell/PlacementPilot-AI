from datetime import datetime, timezone

import streamlit as st

from frontend.components.formatting import percentage
from frontend.components.layout import page_header
from frontend.services.api_client import get_api_client


def _clear_assessment() -> None:
    for key in (
        "assessment_attempt_id",
        "assessment_questions",
        "assessment_started_at",
        "assessment_answers",
        "assessment_result",
    ):
        st.session_state.pop(key, None)


def _start_assessment(api, assessment_id: int) -> None:
    started = api.post(f"/assessments/{assessment_id}/start")
    st.session_state.assessment_attempt_id = started["attempt_id"]
    st.session_state.assessment_questions = started["questions"]
    st.session_state.assessment_started_at = datetime.now(timezone.utc).isoformat()
    st.session_state.assessment_answers = {}
    st.session_state.pop("assessment_result", None)
    st.rerun()


def _render_result(result: dict) -> None:
    st.subheader("Assessment result")
    st.metric("Score", f"{result['score']:.0f}%")
    st.caption(
        f"{result['answered_questions']} of {result['total_questions']} questions answered."
    )
    for answer in result["answers"]:
        with st.expander(
            f"{'Correct' if answer['is_correct'] else 'Review'} · Question {answer['question_id']}"
        ):
            st.write(f"Your answer: {answer['selected_answer']}")
            st.write(f"Correct answer: {answer['correct_answer']}")
            if answer.get("explanation"):
                st.info(answer["explanation"])
    if result.get("topic_performance"):
        st.subheader("Topic performance")
        st.dataframe(
            [
                {
                    "Topic": item["topic_name"],
                    "Score": percentage(item["score"]),
                    "Answered": f"{item['answered_questions']}/{item['total_questions']}",
                }
                for item in result["topic_performance"]
            ],
            use_container_width=True,
            hide_index=True,
        )


def render() -> None:
    api = get_api_client()
    page_header("Benchmark assessment", "Choose a focused question set and measure your current readiness.")
    if "assessment_result" in st.session_state:
        _render_result(st.session_state.assessment_result)
        if st.button("Start another assessment"):
            _clear_assessment()
            st.rerun()
        return

    if "assessment_questions" in st.session_state:
        _render_active_assessment(api)
        return

    subjects = api.get("/subjects")
    if not subjects:
        st.info("No subjects are available yet.")
        return
    subject = st.selectbox("Subject", subjects, format_func=lambda item: item["name"])
    topics = api.get("/topics", params={"subject_id": subject["id"]})
    topic_options = [{"id": None, "name": "All topics"}] + topics
    topic = st.selectbox("Topic", topic_options, format_func=lambda item: item["name"])
    difficulty = st.selectbox("Difficulty", ["All", "easy", "medium", "hard"])
    params = {"subject_id": subject["id"]}
    if topic["id"] is not None:
        params["topic_id"] = topic["id"]
    if difficulty != "All":
        params["difficulty"] = difficulty
    questions = api.get("/questions", params=params)
    st.caption(f"{len(questions)} stored questions match this selection.")
    if not questions:
        st.warning("No questions match these filters.")
        return
    count = st.slider("Questions in this benchmark", 1, len(questions), min(len(questions), 5))
    assessments = api.get("/assessments")
    st.subheader("Start benchmark")
    if st.button("Create and start benchmark", type="primary"):
        assessment = api.post(
            "/assessments",
            json={
                "subject_id": subject["id"],
                "title": f"{subject['name']} benchmark",
                "description": "Frontend-created benchmark assessment.",
                "question_ids": [question["id"] for question in questions[:count]],
            },
        )
        _start_assessment(api, assessment["id"])
    if assessments:
        st.subheader("Previously created assessments")
        selected = st.selectbox(
            "Assessment",
            assessments,
            format_func=lambda item: f"{item['title']} · {item['question_count']} questions",
        )
        if st.button("Start selected assessment"):
            _start_assessment(api, selected["id"])


def _render_active_assessment(api) -> None:
    questions = st.session_state.assessment_questions
    started_at = datetime.fromisoformat(st.session_state.assessment_started_at)
    total_seconds = sum(question["estimated_solving_time_seconds"] for question in questions)
    elapsed = max(0, int((datetime.now(timezone.utc) - started_at).total_seconds()))
    remaining = max(0, total_seconds - elapsed)
    st.subheader("Assessment in progress")
    st.progress(min(elapsed / total_seconds, 1.0), text=f"Time remaining: {remaining // 60}m {remaining % 60:02d}s")
    index = st.selectbox(
        "Question",
        range(len(questions)),
        format_func=lambda item: f"{item + 1}. {questions[item]['prompt'][:70]}",
    )
    question = questions[index]
    st.markdown(f"### {question['prompt']}")
    st.caption(f"Difficulty: {question['difficulty']} · Topic ID: {question['topic_id']}")
    answer_options = ["Not answered", *question["options"]]
    current = st.session_state.assessment_answers.get(question["id"])
    choice = st.radio(
        "Choose an answer",
        answer_options,
        index=answer_options.index(current) if current in answer_options else 0,
        key=f"assessment_answer_{question['id']}",
    )
    if choice != "Not answered":
        st.session_state.assessment_answers[question["id"]] = choice
    st.caption(
        f"{len(st.session_state.assessment_answers)} of {len(questions)} answered."
    )
    if st.button("Submit assessment", type="primary"):
        result = api.post(
            f"/assessments/{st.session_state.assessment_attempt_id}/submit",
            json={
                "answers": [
                    {
                        "question_id": question_id,
                        "selected_answer": answer,
                        "time_taken_seconds": max(0, elapsed),
                    }
                    for question_id, answer in st.session_state.assessment_answers.items()
                ]
            },
        )
        st.session_state.assessment_result = result
        st.session_state.pop("assessment_questions", None)
        st.rerun()

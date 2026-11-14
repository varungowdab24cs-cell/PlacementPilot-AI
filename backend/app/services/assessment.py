from collections import defaultdict
from collections.abc import Iterable

from backend.app.models import Question
from backend.app.schemas.assessment import TopicPerformance


def normalise_answer(answer: str) -> str:
    return answer.strip().casefold()


def answer_is_correct(selected_answer: str, correct_answer: str) -> bool:
    return normalise_answer(selected_answer) == normalise_answer(correct_answer)


def build_topic_performance(
    questions: Iterable[Question],
    submitted_answers: dict[int, tuple[bool, int]],
) -> list[TopicPerformance]:
    grouped: dict[int, dict[str, int | str]] = defaultdict(
        lambda: {
            "topic_name": "",
            "total_questions": 0,
            "answered_questions": 0,
            "correct_answers": 0,
        }
    )
    for question in questions:
        topic = grouped[question.topic_id]
        topic["topic_name"] = question.topic.name
        topic["total_questions"] = int(topic["total_questions"]) + 1
        if question.id in submitted_answers:
            is_correct, _ = submitted_answers[question.id]
            topic["answered_questions"] = int(topic["answered_questions"]) + 1
            topic["correct_answers"] = int(topic["correct_answers"]) + int(is_correct)

    performance = []
    for topic_id, topic in grouped.items():
        total = int(topic["total_questions"])
        correct = int(topic["correct_answers"])
        performance.append(
            TopicPerformance(
                topic_id=topic_id,
                topic_name=str(topic["topic_name"]),
                total_questions=total,
                answered_questions=int(topic["answered_questions"]),
                correct_answers=correct,
                score=round(correct / total * 100, 2) if total else 0,
            )
        )
    return performance

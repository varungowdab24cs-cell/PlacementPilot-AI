from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import Resource, Student, TopicMastery


EXTERNAL_PROBLEM_TYPE = "external_problem"
SUPPORTED_PLATFORMS = ("leetcode", "codeforces")


def external_problem_query(
    *,
    platform: str | None = None,
    topic_id: int | None = None,
    difficulty: str | None = None,
):
    query = (
        select(Resource)
        .where(
            Resource.resource_type == EXTERNAL_PROBLEM_TYPE,
            Resource.is_external.is_(True),
            Resource.platform.in_(SUPPORTED_PLATFORMS),
            Resource.official_url.is_not(None),
        )
        .options(selectinload(Resource.topic))
        .order_by(Resource.id)
    )
    if platform is not None:
        query = query.where(Resource.platform == platform)
    if topic_id is not None:
        query = query.where(Resource.topic_id == topic_id)
    if difficulty is not None:
        query = query.where(Resource.difficulty == difficulty)
    return query


def recommend_external_problems(
    db: Session,
    student: Student,
    *,
    platform: str | None = None,
    topic_id: int | None = None,
    difficulty: str | None = None,
    limit: int = 10,
) -> list[Resource]:
    resources = list(
        db.scalars(
            external_problem_query(
                platform=platform,
                topic_id=topic_id,
                difficulty=difficulty,
            )
        ).all()
    )
    mastery = {
        record.topic_id: record
        for record in db.scalars(
            select(TopicMastery).where(TopicMastery.student_id == student.id)
        ).all()
    }
    preferred_categories = {
        category.casefold() for category in (student.target_company_categories or [])
    }

    def sort_key(resource: Resource) -> tuple[int, int, int]:
        record = mastery.get(resource.topic_id)
        score = (
            record.mastery_score
            if record is not None and record.is_sufficient and record.mastery_score is not None
            else -1
        )
        category_match = bool(
            preferred_categories
            and preferred_categories.intersection(
                category.casefold()
                for category in (resource.recommended_company_categories or [])
            )
        )
        return (int(score if score >= 0 else -1), 0 if category_match else 1, resource.id)

    resources.sort(key=sort_key)
    return resources[:limit]


def practice_statistics(records: Iterable) -> dict[str, int | float | None]:
    records = list(records)
    counts = {outcome: 0 for outcome in ("attempted", "solved", "need_help", "skipped")}
    solving_times: list[int] = []
    self_reported = 0
    verified = 0
    for record in records:
        if record.outcome in counts:
            counts[record.outcome] += 1
        if record.solving_time_seconds is not None:
            solving_times.append(record.solving_time_seconds)
        if record.verified:
            verified += 1
        else:
            self_reported += 1
    return {
        **counts,
        "average_solving_time_seconds": (
            round(sum(solving_times) / len(solving_times), 2)
            if solving_times
            else None
        ),
        "self_reported_count": self_reported,
        "verified_count": verified,
    }

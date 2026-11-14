from backend.app.services.adaptive import (
    MasteryCalculation,
    MasteryConfig,
    TopicMetrics,
    build_recommendation_drafts,
    calculate_consistency,
    calculate_mastery,
    recommendation_difficulty,
)


CONFIG = MasteryConfig(minimum_assessment_attempts=2)


def metrics(
    topic_id: int,
    name: str,
    *,
    prerequisite_topic_id: int | None = None,
    accuracy: float | None = 80,
    consistency: float | None = 70,
    practice_completion: float | None = 50,
    assessment_count: int = 2,
) -> TopicMetrics:
    return TopicMetrics(
        topic_id=topic_id,
        topic_name=name,
        prerequisite_topic_id=prerequisite_topic_id,
        accuracy=accuracy,
        consistency=consistency,
        practice_completion=practice_completion,
        assessment_count=assessment_count,
    )


def test_mastery_formula_and_classification() -> None:
    result = calculate_mastery(metrics(1, "Arrays"), CONFIG)

    assert result.score == 72
    assert result.level == "Good"
    assert result.is_sufficient is True


def test_missing_practice_is_renormalized_not_treated_as_zero() -> None:
    result = calculate_mastery(
        metrics(1, "Graphs", practice_completion=None, accuracy=50, consistency=50),
        CONFIG,
    )

    assert result.score == 50
    assert result.level == "Developing"


def test_insufficient_assessment_history_is_not_classified_as_weak() -> None:
    result = calculate_mastery(
        metrics(1, "Trees", assessment_count=1, accuracy=0, consistency=None),
        CONFIG,
    )

    assert result.score is None
    assert result.level == "Insufficient data"
    assert result.is_sufficient is False


def test_consistency_is_high_for_stable_attempts_and_lower_for_variance() -> None:
    assert calculate_consistency([0.8, 0.8]) == 100
    assert calculate_consistency([0.0, 1.0]) == 50
    assert calculate_consistency([0.8]) is None


def test_prerequisite_is_recommended_before_weak_dependent_topic() -> None:
    prerequisite = metrics(1, "Arrays", accuracy=30, consistency=30, practice_completion=30)
    dependent = metrics(
        2,
        "Dynamic Programming",
        prerequisite_topic_id=1,
        accuracy=20,
        consistency=20,
        practice_completion=20,
    )
    calculations = {
        1: calculate_mastery(prerequisite, CONFIG),
        2: calculate_mastery(dependent, CONFIG),
    }

    drafts = build_recommendation_drafts(
        [dependent, prerequisite],
        calculations,
        config=CONFIG,
    )

    assert [draft.topic_id for draft in drafts] == [1, 2]
    assert "prerequisite" in drafts[0].rationale


def test_recommendation_difficulty_changes_with_mastery() -> None:
    weak = calculate_mastery(
        metrics(1, "Sorting", accuracy=20, consistency=20, practice_completion=20),
        CONFIG,
    )
    good = calculate_mastery(
        metrics(1, "Sorting", accuracy=90, consistency=90, practice_completion=90),
        CONFIG,
    )

    assert recommendation_difficulty(weak, CONFIG) == "easy"
    assert recommendation_difficulty(good, CONFIG) == "hard"
    assert build_recommendation_drafts(
        [metrics(1, "Sorting", accuracy=90, consistency=90, practice_completion=90)],
        {1: good},
        config=CONFIG,
    ) == []

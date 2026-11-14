from dataclasses import dataclass
from math import fsum
from statistics import pstdev
from typing import Optional

from backend.app.core.config import Settings, get_settings

FORMULA_VERSION = "v1"


@dataclass(frozen=True)
class MasteryConfig:
    accuracy_weight: float = 0.6
    consistency_weight: float = 0.2
    practice_weight: float = 0.2
    minimum_assessment_attempts: int = 2
    weak_threshold: float = 40
    developing_threshold: float = 60
    good_threshold: float = 80

    def __post_init__(self) -> None:
        weights = (
            self.accuracy_weight,
            self.consistency_weight,
            self.practice_weight,
        )
        if any(weight < 0 for weight in weights) or sum(weights) <= 0:
            raise ValueError("Mastery weights must be non-negative and not all zero")
        if not (
            self.weak_threshold
            < self.developing_threshold
            < self.good_threshold
        ):
            raise ValueError("Mastery thresholds must be strictly increasing")

    @classmethod
    def from_settings(cls, settings: Settings) -> "MasteryConfig":
        return cls(
            accuracy_weight=settings.mastery_accuracy_weight,
            consistency_weight=settings.mastery_consistency_weight,
            practice_weight=settings.mastery_practice_weight,
            minimum_assessment_attempts=settings.mastery_minimum_assessment_attempts,
            weak_threshold=settings.mastery_weak_threshold,
            developing_threshold=settings.mastery_developing_threshold,
            good_threshold=settings.mastery_good_threshold,
        )


@dataclass(frozen=True)
class TopicMetrics:
    topic_id: int
    topic_name: str
    prerequisite_topic_id: Optional[int]
    accuracy: Optional[float]
    consistency: Optional[float]
    practice_completion: Optional[float]
    assessment_count: int


@dataclass(frozen=True)
class MasteryCalculation:
    score: Optional[float]
    level: str
    is_sufficient: bool


@dataclass(frozen=True)
class RecommendationDraft:
    topic_id: int
    title: str
    activity_type: str
    difficulty: str
    rationale: str


def calculate_consistency(attempt_accuracies: list[float]) -> Optional[float]:
    if len(attempt_accuracies) < 2:
        return None
    return round(max(0.0, 100.0 - pstdev(attempt_accuracies) * 100.0), 2)


def calculate_mastery(
    metrics: TopicMetrics,
    config: MasteryConfig | None = None,
) -> MasteryCalculation:
    config = config or MasteryConfig.from_settings(get_settings())
    if metrics.assessment_count < config.minimum_assessment_attempts:
        return MasteryCalculation(None, "Insufficient data", False)

    weighted_components = [
        (metrics.accuracy, config.accuracy_weight),
        (metrics.consistency, config.consistency_weight),
        (metrics.practice_completion, config.practice_weight),
    ]
    available_components = [
        (value, weight) for value, weight in weighted_components if value is not None
    ]
    total_weight = fsum(weight for _, weight in available_components)
    if total_weight == 0:
        return MasteryCalculation(None, "Insufficient data", False)

    score = round(
        fsum(value * weight for value, weight in available_components) / total_weight,
        2,
    )
    return MasteryCalculation(score, classify_mastery(score, config), True)


def classify_mastery(score: Optional[float], config: MasteryConfig | None = None) -> str:
    config = config or MasteryConfig.from_settings(get_settings())
    if score is None:
        return "Insufficient data"
    if score < config.weak_threshold:
        return "Weak"
    if score < config.developing_threshold:
        return "Developing"
    if score < config.good_threshold:
        return "Good"
    return "Strong"


def recommendation_difficulty(
    calculation: MasteryCalculation,
    config: MasteryConfig | None = None,
) -> str:
    config = config or MasteryConfig.from_settings(get_settings())
    if calculation.score is None:
        return "medium"
    if calculation.score < config.weak_threshold:
        return "easy"
    if calculation.score < config.good_threshold:
        return "medium"
    return "hard"


def build_recommendation_drafts(
    metrics: list[TopicMetrics],
    calculations: dict[int, MasteryCalculation],
    resource_titles: dict[int, str] | None = None,
    config: MasteryConfig | None = None,
) -> list[RecommendationDraft]:
    config = config or MasteryConfig.from_settings(get_settings())
    resource_titles = resource_titles or {}
    candidates = [
        metric
        for metric in metrics
        if calculations[metric.topic_id].score is None
        or calculations[metric.topic_id].score < config.good_threshold
    ]
    candidates.sort(
        key=lambda metric: (
            calculations[metric.topic_id].score is not None,
            calculations[metric.topic_id].score
            if calculations[metric.topic_id].score is not None
            else -1,
            metric.topic_name.casefold(),
        )
    )

    drafts: list[RecommendationDraft] = []
    added_topics: set[int] = set()

    def add_topic(metric: TopicMetrics, prerequisite_for: Optional[str] = None) -> None:
        if metric.topic_id in added_topics:
            return
        calculation = calculations[metric.topic_id]
        difficulty = recommendation_difficulty(calculation, config)
        resource_title = resource_titles.get(metric.topic_id)
        activity_type = "resource" if resource_title else "practice"
        title = (
            f"Review resource: {resource_title}"
            if resource_title
            else f"Practice {difficulty} questions: {metric.topic_name}"
        )
        if prerequisite_for:
            rationale = (
                f"Study {metric.topic_name} first because it is a prerequisite "
                f"for {prerequisite_for}."
            )
        elif calculation.score is None:
            rationale = (
                f"Build an initial evidence base for {metric.topic_name}; "
                "assessment history is insufficient."
            )
        else:
            rationale = (
                f"{metric.topic_name} is classified as {calculation.level}; "
                f"the next activity uses {difficulty} difficulty."
            )
        drafts.append(
            RecommendationDraft(
                topic_id=metric.topic_id,
                title=title,
                activity_type=activity_type,
                difficulty=difficulty,
                rationale=rationale,
            )
        )
        added_topics.add(metric.topic_id)

    metrics_by_id = {metric.topic_id: metric for metric in metrics}
    for metric in candidates:
        prerequisite = (
            metrics_by_id.get(metric.prerequisite_topic_id)
            if metric.prerequisite_topic_id is not None
            else None
        )
        if prerequisite is not None:
            prerequisite_calculation = calculations[prerequisite.topic_id]
            if (
                prerequisite_calculation.score is None
                or prerequisite_calculation.score < config.good_threshold
            ):
                add_topic(prerequisite, metric.topic_name)
        add_topic(metric)

    return drafts

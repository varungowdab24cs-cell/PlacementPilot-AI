import hashlib
import math
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean, stdev
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import (
    AssessmentAttempt,
    Experiment,
    ExperimentAssignment,
    LearningPath,
    MasteryHistory,
    PracticeRecord,
    RecommendationHistory,
    Student,
)
from backend.app.schemas.research import (
    AssessmentAnalyticsRead,
    ExperimentAssignmentRead,
    ExperimentRead,
    ExperimentSequenceRead,
    ResearchAggregateReport,
    ResearchComparison,
    ResearchGroupAggregate,
    StatisticalSummary,
    StudentAnalyticsRead,
    TopicMasteryTimelineRead,
)
from backend.app.services.external_problems import practice_statistics


def experiment_read(experiment: Experiment) -> ExperimentRead:
    return ExperimentRead(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        starts_at=experiment.starts_at,
        ends_at=experiment.ends_at,
        control_topic_ids=experiment.configuration.get("control_topic_ids", []),
    )


def stable_assignment(
    db: Session,
    experiment: Experiment,
    student: Student,
) -> ExperimentAssignment:
    existing = db.scalar(
        select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment.id,
            ExperimentAssignment.student_id == student.id,
        )
    )
    if existing is not None:
        return existing
    digest = hashlib.sha256(f"{experiment.id}:{student.id}".encode()).digest()
    condition = "experimental" if digest[0] % 2 else "control"
    assignment = ExperimentAssignment(
        experiment_id=experiment.id,
        student_id=student.id,
        condition=condition,
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def assignment_read(assignment: ExperimentAssignment) -> ExperimentAssignmentRead:
    return ExperimentAssignmentRead(
        experiment_id=assignment.experiment_id,
        condition=assignment.condition,
        assigned_at=assignment.assigned_at,
    )


def build_sequence(
    db: Session,
    experiment: Experiment,
    assignment: ExperimentAssignment,
    student_id: int,
) -> ExperimentSequenceRead:
    if assignment.condition == "control":
        topic_ids = experiment.configuration.get("control_topic_ids", [])
        return ExperimentSequenceRead(
            experiment_id=experiment.id,
            condition="control",
            sequence_type="fixed",
            topic_ids=topic_ids,
        )
    path = db.scalar(
        select(LearningPath)
        .where(
            LearningPath.student_id == student_id,
            LearningPath.status == "active",
        )
        .options(selectinload(LearningPath.items))
        .order_by(LearningPath.id.desc())
    )
    topic_ids = (
        [item.topic_id for item in sorted(path.items, key=lambda item: item.position)]
        if path is not None
        else [
            item.topic_id
            for item in db.scalars(
                select(RecommendationHistory)
                .where(
                    RecommendationHistory.student_id == student_id,
                    RecommendationHistory.status == "recommended",
                )
                .order_by(RecommendationHistory.id)
            ).all()
        ]
    )
    return ExperimentSequenceRead(
        experiment_id=experiment.id,
        condition="experimental",
        sequence_type="adaptive",
        topic_ids=topic_ids,
    )


def _summary(values: list[float | None]) -> StatisticalSummary:
    observed = [float(value) for value in values if value is not None]
    count = len(observed)
    if not observed:
        return StatisticalSummary(
            n=0,
            mean=None,
            standard_deviation=None,
            confidence_interval_low=None,
            confidence_interval_high=None,
        )
    average = mean(observed)
    if count < 2:
        return StatisticalSummary(
            n=1,
            mean=round(average, 4),
            standard_deviation=None,
            confidence_interval_low=None,
            confidence_interval_high=None,
        )
    deviation = stdev(observed)
    margin = float(1.96 * deviation / math.sqrt(count))
    return StatisticalSummary(
        n=count,
        mean=round(average, 4),
        standard_deviation=round(deviation, 4),
        confidence_interval_low=round(average - margin, 4),
        confidence_interval_high=round(average + margin, 4),
    )


def _mean_or_none(values: list[float]) -> float | None:
    return round(mean(values), 4) if values else None


def _participant_metrics(
    db: Session,
    experiment_id: int,
    assignment: ExperimentAssignment,
) -> dict[str, Any]:
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.experiment_id == experiment_id,
                AssessmentAttempt.student_id == assignment.student_id,
                AssessmentAttempt.completed_at.is_not(None),
            )
            .options(
                selectinload(AssessmentAttempt.assessment),
                selectinload(AssessmentAttempt.answers),
            )
        ).all()
    )
    scores_by_phase: dict[str, list[float]] = defaultdict(list)
    completion_rates: list[float] = []
    for attempt in attempts:
        if attempt.score is not None and attempt.assessment_phase is not None:
            scores_by_phase[attempt.assessment_phase].append(attempt.score)
        total = len(attempt.assessment.questions)
        if total:
            completion_rates.append(len(attempt.answers) / total * 100)

    records = list(
        db.scalars(
            select(PracticeRecord).where(
                PracticeRecord.student_id == assignment.student_id,
                PracticeRecord.resource_id.is_not(None),
            )
        ).all()
    )
    stats = practice_statistics(records)
    mastery_history = list(
        db.scalars(
            select(MasteryHistory)
            .where(MasteryHistory.student_id == assignment.student_id)
            .order_by(MasteryHistory.created_at)
        ).all()
    )
    by_topic: dict[int, list[float]] = defaultdict(list)
    for record in mastery_history:
        if record.is_sufficient and record.mastery_score is not None:
            by_topic[record.topic_id].append(record.mastery_score)
    changes = [
        scores[-1] - scores[0]
        for scores in by_topic.values()
        if len(scores) >= 2
    ]
    return {
        "condition": assignment.condition,
        "pre": _mean_or_none(scores_by_phase["pre"]),
        "post": _mean_or_none(scores_by_phase["post"]),
        "improvement": (
            _mean_or_none(
                [
                    scores_by_phase["post"][index] - scores_by_phase["pre"][index]
                    for index in range(
                        min(len(scores_by_phase["pre"]), len(scores_by_phase["post"]))
                    )
                ]
            )
            if scores_by_phase["pre"] and scores_by_phase["post"]
            else None
        ),
        "completion": _mean_or_none(completion_rates),
        "dsa_solved": (
            float(stats["solved"]) if records else None
        ),
        "mastery_change": _mean_or_none(changes),
    }


def aggregate_report(
    db: Session,
    experiment: Experiment,
) -> ResearchAggregateReport:
    assignments = list(
        db.scalars(
            select(ExperimentAssignment)
            .where(ExperimentAssignment.experiment_id == experiment.id)
            .order_by(ExperimentAssignment.id)
        ).all()
    )
    metrics = [_participant_metrics(db, experiment.id, assignment) for assignment in assignments]
    groups: list[ResearchGroupAggregate] = []
    for condition in ("control", "experimental"):
        observed = [item for item in metrics if item["condition"] == condition]
        groups.append(
            ResearchGroupAggregate(
                condition=condition,
                participant_count=len(observed),
                pre_test=_summary([item["pre"] for item in observed]),
                post_test=_summary([item["post"] for item in observed]),
                improvement=_summary([item["improvement"] for item in observed]),
                assessment_completion=_summary([item["completion"] for item in observed]),
                dsa_solved=_summary([item["dsa_solved"] for item in observed]),
                topic_mastery_change=_summary(
                    [item["mastery_change"] for item in observed]
                ),
            )
        )
    control = [item["improvement"] for item in metrics if item["condition"] == "control"]
    experimental = [
        item["improvement"] for item in metrics if item["condition"] == "experimental"
    ]
    control_observed = [value for value in control if value is not None]
    experimental_observed = [value for value in experimental if value is not None]
    statistic = p_value = None
    if len(control_observed) >= 2 and len(experimental_observed) >= 2:
        try:
            from scipy.stats import ttest_ind
        except ImportError:
            pass
        else:
            result = ttest_ind(experimental_observed, control_observed, equal_var=False)
            statistic = round(float(result.statistic), 4)
            p_value = round(float(result.pvalue), 6)
    return ResearchAggregateReport(
        experiment_id=experiment.id,
        experiment_name=experiment.name,
        evaluation_start=experiment.starts_at,
        evaluation_end=experiment.ends_at,
        generated_at=datetime.now(timezone.utc),
        groups=groups,
        comparisons=[
            ResearchComparison(
                metric="pre_post_improvement",
                control_n=len(control_observed),
                experimental_n=len(experimental_observed),
                statistic=statistic,
                p_value=p_value,
            )
        ],
    )


def student_analytics(db: Session, student_id: int) -> StudentAnalyticsRead:
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.student_id == student_id,
                AssessmentAttempt.completed_at.is_not(None),
            )
            .options(
                selectinload(AssessmentAttempt.assessment),
                selectinload(AssessmentAttempt.answers),
            )
            .order_by(AssessmentAttempt.completed_at)
        ).all()
    )
    assessment_rows = []
    pre_scores: list[float] = []
    post_scores: list[float] = []
    for attempt in attempts:
        total = len(attempt.assessment.questions)
        answered = len(attempt.answers)
        times = [answer.time_taken_seconds for answer in attempt.answers]
        if attempt.score is not None and attempt.assessment_phase == "pre":
            pre_scores.append(attempt.score)
        if attempt.score is not None and attempt.assessment_phase == "post":
            post_scores.append(attempt.score)
        assessment_rows.append(
            AssessmentAnalyticsRead(
                attempt_id=attempt.id,
                assessment_id=attempt.assessment_id,
                assessment_title=attempt.assessment.title,
                phase=attempt.assessment_phase,
                score=attempt.score,
                answered_questions=answered,
                total_questions=total,
                completion_rate=round(answered / total * 100, 2) if total else None,
                average_time_taken_seconds=round(mean(times), 2) if times else None,
                completed_at=attempt.completed_at,
            )
        )

    mastery_rows = list(
        db.scalars(
            select(MasteryHistory)
            .where(MasteryHistory.student_id == student_id)
            .options(selectinload(MasteryHistory.topic))
            .order_by(MasteryHistory.created_at)
        ).all()
    )
    topic_rows = [
        TopicMasteryTimelineRead(
            topic_id=record.topic_id,
            topic_name=record.topic.name,
            score=record.mastery_score if record.is_sufficient else None,
            is_sufficient=record.is_sufficient,
            assessment_count=record.assessment_count,
            recorded_at=record.created_at,
        )
        for record in mastery_rows
    ]
    external_records = list(
        db.scalars(
            select(PracticeRecord).where(
                PracticeRecord.student_id == student_id,
                PracticeRecord.resource_id.is_not(None),
            )
        ).all()
    )
    return StudentAnalyticsRead(
        pre_test_score=_mean_or_none(pre_scores),
        post_test_score=_mean_or_none(post_scores),
        assessment_history=assessment_rows,
        topic_mastery_history=topic_rows,
        dsa_practice=practice_statistics(external_records),
    )

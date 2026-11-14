"""Analyze an anonymized participant-level experiment CSV.

Required columns:
condition, pre_test_score, post_test_score, assessment_completion,
dsa_solved, topic_mastery_change

The CSV must not contain student identifiers or direct identifying fields.
Missing numeric observations remain missing and are excluded only from the
statistic that needs them.
"""

import argparse
import json
from pathlib import Path


def _summary(values, stats) -> dict[str, float | int | None]:
    observed = values.dropna()
    count = int(observed.count())
    if count == 0:
        return {
            "n": 0,
            "mean": None,
            "standard_deviation": None,
            "confidence_interval_low": None,
            "confidence_interval_high": None,
        }
    average = float(observed.mean())
    if count < 2:
        return {
            "n": count,
            "mean": round(average, 4),
            "standard_deviation": None,
            "confidence_interval_low": None,
            "confidence_interval_high": None,
        }
    deviation = float(observed.std(ddof=1))
    low, high = stats.t.interval(
        0.95,
        df=count - 1,
        loc=average,
        scale=deviation / count**0.5,
    )
    return {
        "n": count,
        "mean": round(average, 4),
        "standard_deviation": round(deviation, 4),
        "confidence_interval_low": round(float(low), 4),
        "confidence_interval_high": round(float(high), 4),
    }


def analyze(input_path: Path) -> dict:
    import pandas as pd
    from scipy import stats

    frame = pd.read_csv(input_path)
    required = {
        "condition",
        "pre_test_score",
        "post_test_score",
        "assessment_completion",
        "dsa_solved",
        "topic_mastery_change",
    }
    missing_columns = required - set(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")
    identifying = {
        column
        for column in frame.columns
        if any(token in column.casefold() for token in ("email", "name", "student_id", "student_name"))
    }
    if identifying:
        raise ValueError(f"Identifying columns are not allowed: {sorted(identifying)}")
    if not set(frame["condition"].dropna()).issubset({"control", "experimental"}):
        raise ValueError("condition must contain only control or experimental")

    numeric_columns = [
        "pre_test_score",
        "post_test_score",
        "assessment_completion",
        "dsa_solved",
        "topic_mastery_change",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["improvement"] = frame["post_test_score"] - frame["pre_test_score"]

    groups = []
    for condition in ("control", "experimental"):
        group = frame[frame["condition"] == condition]
        groups.append(
            {
                "condition": condition,
                "participant_count": int(len(group)),
                "pre_test": _summary(group["pre_test_score"], stats),
                "post_test": _summary(group["post_test_score"], stats),
                "improvement": _summary(group["improvement"], stats),
                "assessment_completion": _summary(group["assessment_completion"], stats),
                "dsa_solved": _summary(group["dsa_solved"], stats),
                "topic_mastery_change": _summary(group["topic_mastery_change"], stats),
            }
        )

    control = frame.loc[frame["condition"] == "control", "improvement"].dropna()
    experimental = frame.loc[
        frame["condition"] == "experimental", "improvement"
    ].dropna()
    comparison = {
        "metric": "pre_post_improvement",
        "control_n": int(len(control)),
        "experimental_n": int(len(experimental)),
        "statistic": None,
        "p_value": None,
    }
    if len(control) >= 2 and len(experimental) >= 2:
        result = stats.ttest_ind(experimental, control, equal_var=False)
        comparison["statistic"] = round(float(result.statistic), 4)
        comparison["p_value"] = round(float(result.pvalue), 6)
    return {"groups": groups, "comparisons": [comparison]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze anonymized experiment data.")
    parser.add_argument("input", type=Path, help="Anonymized participant-level CSV")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    result = analyze(args.input)
    serialized = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()

"""Summarize raw JSON produced by run_accuracy_study.py.

Run with ordinary Python; Blender is not required:
    python3 benchmarks/analyze_accuracy.py reports/accuracy-study-*.json
"""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(values, percentage):
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calculate a percentile without values")
    index = (len(ordered) - 1) * percentage / 100
    lower, upper = int(index), min(int(index) + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def summarize(records):
    errors = [record["absolute_percentage_error"] for record in records]
    if not errors:
        raise ValueError("no completed measurements found")
    by_fixture = defaultdict(list)
    for record in records:
        by_fixture[record["fixture"]].append(record["absolute_percentage_error"])
    return {
        "measurement_count": len(records),
        "absolute_percentage_error": {
            "mean": round(statistics.mean(errors), 2),
            "median": round(statistics.median(errors), 2),
            "p90": round(percentile(errors, 90), 2),
            "max": round(max(errors), 2),
        },
        "by_fixture": {
            name: {
                "count": len(values),
                "mean": round(statistics.mean(values), 2),
                "max": round(max(values), 2),
            }
            for name, values in sorted(by_fixture.items())
        },
    }


def recommendation(summary):
    p90 = summary["absolute_percentage_error"]["p90"]
    proposed = max(25, int((p90 + 4.999) // 5) * 5)
    return {
        "proposed_non_adaptive_range_percent": proposed,
        "reason": "Rounded up from the measured non-adaptive absolute-error p90",
    }


def load_records(paths):
    records = []
    for path in paths:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        records.extend(result for result in report["results"] if result.get("status") == "completed")
    return records


def markdown(summary, proposed):
    rows = [
        "# Accuracy Study Summary",
        "",
        f"Completed measurements: {summary['measurement_count']}",
        "",
        "| Metric | Absolute percentage error |",
        "| --- | ---: |",
    ]
    for key in ("mean", "median", "p90", "max"):
        rows.append(f"| {key.upper()} | {summary['absolute_percentage_error'][key]}% |")
    rows.extend(["", "| Fixture | Runs | Mean error | Max error |", "| --- | ---: | ---: | ---: |"])
    for name, values in summary["by_fixture"].items():
        rows.append(f"| {name} | {values['count']} | {values['mean']}% | {values['max']}% |")
    rows.extend([
        "",
        f"Recommended non-adaptive range: ±{proposed['proposed_non_adaptive_range_percent']}%.",
        "",
        "This recommendation applies only to the measured fixture set, settings, and hardware.",
    ])
    return "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("accuracy-study-summary.md"))
    args = parser.parse_args()
    summary = summarize(load_records(args.reports))
    proposed = recommendation(summary)
    args.output.write_text(markdown(summary, proposed), encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__":
    main()

"""Pre-demo quality pack for deterministic SupportMaster scenarios."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..models.evaluation import EvaluationScenario, QualityPackResult
from ..persistence import SQLiteRunStore
from .suite import EndToEndWorkflowSuite, FunctionalEvaluationSuite, load_scenarios


def run_quality_pack(
    store: SQLiteRunStore,
    scenarios: list[EvaluationScenario],
    *,
    suite_name: str = "pre-demo-quality",
) -> QualityPackResult:
    """Run all deterministic checks and summarize coverage and failures."""
    functional = FunctionalEvaluationSuite(store, suite_name=f"{suite_name}:functional").run(scenarios)
    end_to_end = EndToEndWorkflowSuite(store, suite_name=f"{suite_name}:e2e").run(scenarios)
    categories = Counter(tag for scenario in scenarios for tag in scenario.tags)
    checks = Counter()
    failures: list[str] = []
    for result in functional.scenarios:
        for check in result.checks:
            checks[check.name] += 1
            if check.status == "FAIL":
                failures.append(f"{result.scenario_id}:{check.name}")
    for result in end_to_end.simulations:
        for step in result.steps:
            checks[f"e2e:{step.name}"] += 1
            if step.status == "FAIL":
                failures.append(f"{result.scenario_id}:e2e:{step.name}")
    return QualityPackResult(
        status="PASS" if functional.status == "PASS" and end_to_end.status == "PASS" else "FAIL",
        functional=functional,
        end_to_end=end_to_end,
        category_counts=dict(categories),
        check_counts=dict(checks),
        failures=failures,
    )


def run_fixture_quality_pack(
    store: SQLiteRunStore,
    directory: str | Path,
) -> QualityPackResult:
    return run_quality_pack(store, load_scenarios(directory))

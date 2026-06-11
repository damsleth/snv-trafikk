"""Shared result loading and aggregation helpers for downstream scripts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


SUMMARY_STAT_KEYS = [
    "avg_duration_s",
    "max_duration_s",
    "avg_waiting_time_s",
    "system_delay_h",
    "completed_time_loss_h",
    "blocked_vehicle_h",
    "peak_waiting",
    "peak_queue_proxy",
    "waiting",
    "not_inserted",
    "inserted",
    "loaded",
    "emergency_avg_duration_s",
    "emergency_max_duration_s",
    "emergency_avg_time_loss_s",
    "snaroya_origin_count",
    "snaroya_avg_duration_s",
    "snaroya_avg_time_loss_s",
    "queue_length_km",
]


def load_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_all_results(output_dir: Path) -> dict:
    return load_json_if_exists(output_dir / "all_results.json")


def aggregate_stats(runs: list[dict], keys: list[str] | None = None) -> dict:
    if not runs:
        return {}

    metric_keys = keys or SUMMARY_STAT_KEYS
    stats = {}
    for key in metric_keys:
        values = [run.get(key, 0) for run in runs if key in run]
        if values:
            stats[f"{key}_mean"] = float(np.mean(values))
            stats[f"{key}_std"] = float(np.std(values))
    return stats


def metric_mean(runs: list[dict], key: str) -> float:
    values = [run.get(key, 0) for run in runs if key in run]
    if not values:
        return 0.0
    return float(np.mean(values))


def seed_counts(runs: list[dict]) -> tuple[int, int]:
    """Return (successful, total) seed counts for a scenario.

    A seed is "successful" when it produced completed-trip metrics. Seeds that
    failed (e.g. SUMO gridlock/crash) carry no metric keys and are silently
    excluded from the means, so reporting the count guards against seed-level
    survivorship bias.
    """
    total = len(runs)
    successful = sum(1 for run in runs if not run.get("failed") and "avg_duration_s" in run)
    return successful, total


def group_scenarios_by_period(results: dict, periods: dict, scenario_period) -> dict[str, list[str]]:
    grouped = {period_name: [] for period_name in periods}
    for scenario_name, runs in results.items():
        period_name = scenario_period(scenario_name)
        if runs and period_name in grouped:
            grouped[period_name].append(scenario_name)
    for period_name in grouped:
        grouped[period_name].sort()
    return grouped


def load_summary_stats(summary_file: Path) -> dict:
    return load_json_if_exists(summary_file)


def load_scenario_stats(output_dir: Path, summary_stats: dict, scenario_name: str) -> dict:
    if scenario_name in summary_stats:
        return summary_stats[scenario_name]
    return load_json_if_exists(output_dir / scenario_name / "seed_1" / "run_stats.json")
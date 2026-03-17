#!/usr/bin/env python3
"""Analyze SUMO simulation results and generate comparison visualizations."""

import os
import xml.etree.ElementTree as ET

from config import OUTPUT_DIR, PROJECT_ROOT, VISUALIZATIONS_DIR

os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".tmp" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils.results import group_scenarios_by_period, load_all_results, metric_mean
from utils.scenario_catalog import PERIODS, SCENARIOS, scenario_color, scenario_label, scenario_period


def load_summary(scenario_name: str, seed: int = 1) -> pd.DataFrame:
    filepath = OUTPUT_DIR / scenario_name / f"seed_{seed}" / "summary.xml"
    if not filepath.exists():
        return pd.DataFrame()

    tree = ET.parse(str(filepath))
    rows = []
    for step in tree.getroot().findall("step"):
        rows.append(
            {
                "time": float(step.get("time", 0)),
                "loaded": int(step.get("loaded", 0)),
                "inserted": int(step.get("inserted", 0)),
                "running": int(step.get("running", 0)),
                "waiting": int(step.get("waiting", 0)),
                "ended": int(step.get("ended", 0)),
                "meanSpeed": float(step.get("meanSpeed", 0)),
                "halting": int(step.get("halting", 0)),
            }
        )
    return pd.DataFrame(rows)


def available_scenarios_by_period(results: dict) -> dict[str, list[str]]:
    return group_scenarios_by_period(results, PERIODS, scenario_period)


def chart_metric(results: dict, period_name: str, metric: str, xlabel: str, title: str, filename: str) -> None:
    scenarios = []
    values = []
    colors = []
    for scenario_name in available_scenarios_by_period(results)[period_name]:
        runs = results[scenario_name]
        scenarios.append(scenario_label(scenario_name))
        values.append(metric_mean(runs, metric))
        colors.append(scenario_color(scenario_name))

    if not scenarios:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(scenarios, values, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_title(title, fontsize=14)

    for bar, value in zip(bars, values):
        label = f"{value:.1f}" if value < 100 else f"{value:.0f}"
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f"  {label}", va="center", fontsize=10)

    plt.tight_layout()
    plt.savefig(VISUALIZATIONS_DIR / filename, dpi=150)
    plt.close()
    print(f"Saved {filename}")


def chart_queue_timeline(results: dict, period_name: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    has_data = False
    for scenario_name in available_scenarios_by_period(results)[period_name]:
        df = load_summary(scenario_name, seed=1)
        if df.empty:
            continue
        has_data = True
        queue = df["waiting"] + df["halting"]
        if len(queue) > 10:
            queue = queue.rolling(window=10, min_periods=1).mean()
        ax.plot(df["time"] / 60.0, queue, label=scenario_label(scenario_name), color=scenario_color(scenario_name), linewidth=2)

    if not has_data:
        plt.close()
        return

    period_title = PERIODS[period_name]["title"]
    ax.set_xlabel("Tid (minutter fra simuleringsstart)", fontsize=12)
    ax.set_ylabel("Ventende + stående kjøretøy", fontsize=12)
    ax.set_title(f"Køutvikling, {period_title}", fontsize=14)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out_file = VISUALIZATIONS_DIR / f"{period_name}_queue_timeline.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"Saved {out_file.name}")


def generate_dashboard(results: dict) -> None:
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except Exception as exc:
        print(f"Skipping dashboard: {exc}")
        return

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[
            "Gjennomsnittlig reisetid (AM)",
            "Systemforsinkelse (AM)",
            "Gjennomsnittlig reisetid (PM)",
            "Systemforsinkelse (PM)",
        ],
    )

    for column, period_name in enumerate(["morning", "afternoon"], start=1):
        scenarios = available_scenarios_by_period(results)[period_name]
        labels = [scenario_label(name) for name in scenarios]
        colors = [scenario_color(name) for name in scenarios]
        avg_duration = [metric_mean(results[name], "avg_duration_s") / 60.0 for name in scenarios]
        system_delay = [metric_mean(results[name], "system_delay_h") for name in scenarios]

        fig.add_trace(
            go.Bar(x=labels, y=avg_duration, marker_color=colors, text=[f"{value:.1f}" for value in avg_duration], textposition="auto"),
            row=1,
            col=column,
        )
        fig.add_trace(
            go.Bar(x=labels, y=system_delay, marker_color=colors, text=[f"{value:.1f}" for value in system_delay], textposition="auto"),
            row=2,
            col=column,
        )

    fig.update_layout(height=800, template="plotly_white", title="Snarøyveien scenariosammenligning")
    dashboard_file = VISUALIZATIONS_DIR / "dashboard.html"
    fig.write_html(str(dashboard_file), include_plotlyjs=True)
    print(f"Saved {dashboard_file.name}")


def analyze_all() -> None:
    print("=" * 60)
    print("PHASE 4: Analysis and Visualization")
    print("=" * 60)
    VISUALIZATIONS_DIR.mkdir(parents=True, exist_ok=True)

    results = load_all_results(OUTPUT_DIR)
    if not results:
        print("No simulation results found.")
        return

    for period_name, period in PERIODS.items():
        chart_metric(
            results,
            period_name,
            "avg_duration_s",
            "Gjennomsnittlig reisetid (sekunder)",
            f"Reisetid, {period['title']}",
            f"{period_name}_avg_duration.png",
        )
        chart_metric(
            results,
            period_name,
            "peak_waiting",
            "Maks ventende kjøretøy utenfor modellen",
            f"Blokkerte kjøretøy, {period['title']}",
            f"{period_name}_peak_waiting.png",
        )
        chart_metric(
            results,
            period_name,
            "system_delay_h",
            "Systemforsinkelse (kjøretøy-timer)",
            f"Systemforsinkelse, {period['title']}",
            f"{period_name}_system_delay.png",
        )
        chart_queue_timeline(results, period_name)

    generate_dashboard(results)
    print(f"\nVisualizations written to {VISUALIZATIONS_DIR}")


if __name__ == "__main__":
    analyze_all()

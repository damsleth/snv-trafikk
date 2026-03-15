#!/usr/bin/env python3
"""Generate a markdown report from the latest simulation results."""

import json
from datetime import datetime
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
VIZ_DIR = OUTPUT_DIR / "visualizations"
REPORT_DIR = OUTPUT_DIR / "report"

import sys

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from utils.scenario_catalog import PERIODS, SCENARIOS, scenario_color, scenario_family, scenario_label, scenario_period


def load_results() -> dict:
    results_file = OUTPUT_DIR / "all_results.json"
    if not results_file.exists():
        return {}
    return json.loads(results_file.read_text(encoding="utf-8"))


def compute_stats(runs: list[dict]) -> dict:
    if not runs:
        return {}
    keys = [
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
    ]
    stats = {}
    for key in keys:
        values = [run.get(key, 0) for run in runs if key in run]
        if values:
            stats[f"{key}_mean"] = float(np.mean(values))
            stats[f"{key}_std"] = float(np.std(values))
    return stats


def compare_text(base_value: float, candidate_value: float, unit: str, precision: int = 1) -> str:
    delta = candidate_value - base_value
    sign = "+" if delta > 0 else ""
    return f"{candidate_value:.{precision}f}{unit} ({sign}{delta:.{precision}f}{unit} vs. base)"


def group_scenarios(results: dict) -> dict[str, list[str]]:
    grouped = {period_name: [] for period_name in PERIODS}
    for scenario_name, runs in results.items():
        if runs and scenario_period(scenario_name) in grouped:
            grouped[scenario_period(scenario_name)].append(scenario_name)
    for period_name in grouped:
        grouped[period_name].sort()
    return grouped


def generate_report() -> None:
    print("=" * 60)
    print("PHASE 5: Generating report")
    print("=" * 60)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = load_results()
    grouped = group_scenarios(results)
    stats_by_scenario = {scenario_name: compute_stats(runs) for scenario_name, runs in results.items()}

    def img(name: str) -> str:
        return f"../visualizations/{name}"

    lines = [
        "# Trafikkanalyse Snarøyveien",
        "",
        f"*Automatisk generert {datetime.now().strftime('%d.%m.%Y kl. %H:%M')}*",
        "",
        "## QA-status",
        "",
        "Denne rapporten bruker periodedelte scenarioer (AM/PM), appendix-baserte OD-matriser og en systemforsinkelses-KPI som inkluderer både fullførte turer og blokkerte avganger.",
        "",
        "Det betyr at tallene under ikke er direkte sammenlignbare med tidligere repo-utgaver som brukte kun morgenrute og kun tidstap fra fullførte turer.",
        "",
        "## Hovedobservasjoner",
        "",
    ]

    for period_name, period in PERIODS.items():
        period_scenarios = grouped[period_name]
        base_name = f"scenario_4A_base_{period_name}"
        v1_name = f"scenario_4A_v1_{period_name}"
        base_stats = stats_by_scenario.get(base_name, {})
        v1_stats = stats_by_scenario.get(v1_name, {})
        lines.append(f"### {period['title'].capitalize()}")
        lines.append("")
        if base_stats and v1_stats:
            base_duration = base_stats.get("avg_duration_s_mean", 0) / 60.0
            v1_duration = v1_stats.get("avg_duration_s_mean", 0) / 60.0
            base_delay = base_stats.get("system_delay_h_mean", 0)
            v1_delay = v1_stats.get("system_delay_h_mean", 0)
            base_waiting = base_stats.get("peak_waiting_mean", 0)
            v1_waiting = v1_stats.get("peak_waiting_mean", 0)
            lines.append(f"- Base: {base_duration:.1f} min gjennomsnittlig reisetid, {base_delay:.1f} kjt-t systemforsinkelse, {base_waiting:.0f} maks ventende kjøretøy.")
            lines.append(f"- V1: {v1_duration:.1f} min gjennomsnittlig reisetid, {v1_delay:.1f} kjt-t systemforsinkelse, {v1_waiting:.0f} maks ventende kjøretøy.")
            lines.append(f"- Endring V1 vs. base: {compare_text(base_duration, v1_duration, ' min')}, {compare_text(base_delay, v1_delay, ' kjt-t')}, {compare_text(base_waiting, v1_waiting, ' kjt', 0)}.")
        else:
            lines.append("- Ikke nok simuleringsdata for sammenligning.")
        lines.append("")

    lines += [
        "## Metode",
        "",
        "- Etterspørsel er hentet fra appendixmatrisene i PGF Trafikkanalyse Snarøyveien (Scenario 1A/4A, morgen og ettermiddag).",
        "- V1/V2/V3 følger segmentert A/B/C-laneoppsett i stedet for en ensartet 2+2-forenkling.",
        "- Rapporten bruker `system_delay_h = completed_time_loss_h + blocked_vehicle_h` for å unngå survivorship-bias når mange biler aldri kommer inn i modellen.",
        "- Resultatene er fortsatt begrenset av nettverksforenklinger fra OSM-basen og manglende kalibrering mot observerte telledata.",
        "",
        "## Visualiseringer",
        "",
        f"![AM reisetid]({img('morning_avg_duration.png')})",
        "",
        f"![AM systemforsinkelse]({img('morning_system_delay.png')})",
        "",
        f"![PM reisetid]({img('afternoon_avg_duration.png')})",
        "",
        f"![PM systemforsinkelse]({img('afternoon_system_delay.png')})",
        "",
        "## Scenariotabell",
        "",
        "| Scenario | Reisetid | Systemforsinkelse | Blokkerte avganger | Maks ventende |",
        "|---|---|---|---|---|",
    ]

    for scenario_name in sorted(results):
        stats = stats_by_scenario.get(scenario_name, {})
        if not stats:
            continue
        lines.append(
            f"| {scenario_label(scenario_name)} | "
            f"{stats.get('avg_duration_s_mean', 0) / 60.0:.1f} min | "
            f"{stats.get('system_delay_h_mean', 0):.1f} kjt-t | "
            f"{stats.get('not_inserted_mean', 0):.0f} | "
            f"{stats.get('peak_waiting_mean', 0):.0f} |"
        )

    lines += [
        "",
        "## Begrensninger",
        "",
        "- Repoet mangler fortsatt observasjonsbasert kalibrering og automatiserte tester.",
        "- Flytårnet/Bernt Balchens-krysset er fortsatt avhengig av OSM-nettets geometri og prioriteringsmodell; dette er en kjent modellbegrensning som må forbedres før rapportering utad.",
        "- Scenarioet med signaloptimalisering er midlertidig tatt ut av standardkjøringen til kryssmodellen er eksplisitt implementert.",
        "",
    ]

    report_file = REPORT_DIR / "snaroyveien_traffic_report.md"
    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report -> {report_file}")

    summary_file = REPORT_DIR / "summary_stats.json"
    summary_file.write_text(json.dumps(stats_by_scenario, indent=2), encoding="utf-8")
    print(f"Summary -> {summary_file}")


if __name__ == "__main__":
    generate_report()

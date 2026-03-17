#!/usr/bin/env python3
"""Generate a markdown report from the latest simulation results."""

import json
from datetime import datetime

import numpy as np

from config import OUTPUT_DIR, REPORT_DIR, VISUALIZATIONS_DIR
from utils.results import aggregate_stats, group_scenarios_by_period, load_all_results
from utils.scenario_catalog import PERIODS, SCENARIOS, scenario_color, scenario_family, scenario_label, scenario_period


def compare_text(base_value: float, candidate_value: float, unit: str, precision: int = 1) -> str:
    delta = candidate_value - base_value
    sign = "+" if delta > 0 else ""
    return f"{candidate_value:.{precision}f}{unit} ({sign}{delta:.{precision}f}{unit} vs. base)"


def group_scenarios(results: dict) -> dict[str, list[str]]:
    return group_scenarios_by_period(results, PERIODS, scenario_period)


def generate_report() -> None:
    print("=" * 60)
    print("PHASE 5: Generating report")
    print("=" * 60)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = load_all_results(OUTPUT_DIR)
    grouped = group_scenarios(results)
    stats_by_scenario = {scenario_name: aggregate_stats(runs) for scenario_name, runs in results.items()}

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

    # --- Emergency response time section ---
    lines += ["", "## Utrykningstid (beredskap)", ""]
    lines.append(
        "Tre ambulanser er lagt inn i hver simuleringsperiode "
        "(snv_syd → snv_nordost, dvs. Snarøya til nordre rundkjøring). "
        "Tabellen viser gjennomsnittlig reisetid for utrykningskjøretøy:"
    )
    lines += [
        "",
        "| Scenario | Utrykningstid (gj.snitt) | Maks utrykningstid | Tidstap utrykn. |",
        "|---|---|---|---|",
    ]
    for scenario_name in sorted(results):
        st = stats_by_scenario.get(scenario_name, {})
        emer_avg = st.get("emergency_avg_duration_s_mean")
        if emer_avg is None:
            continue
        emer_max = st.get("emergency_max_duration_s_mean", 0)
        emer_loss = st.get("emergency_avg_time_loss_s_mean", 0)
        lines.append(
            f"| {scenario_label(scenario_name)} | "
            f"{emer_avg / 60.0:.1f} min | "
            f"{emer_max / 60.0:.1f} min | "
            f"{emer_loss:.0f} s |"
        )

    # --- Per-capita delay (Snarøya residents) ---
    lines += ["", "## Forsinkelse for Snarøya-beboere", ""]
    lines.append(
        "Kun turer med avgang fra Snarøya (snv_syd-sonen). "
        "Viser forsinkelsen for beboere som skal ut fra halvøya."
    )
    lines += [
        "",
        "| Scenario | Ant. turer | Gj.snitt reisetid | Gj.snitt tidstap |",
        "|---|---|---|---|",
    ]
    for scenario_name in sorted(results):
        st = stats_by_scenario.get(scenario_name, {})
        sn_count = st.get("snaroya_origin_count_mean")
        if sn_count is None:
            continue
        sn_dur = st.get("snaroya_avg_duration_s_mean", 0)
        sn_loss = st.get("snaroya_avg_time_loss_s_mean", 0)
        lines.append(
            f"| {scenario_label(scenario_name)} | "
            f"{sn_count:.0f} | "
            f"{sn_dur / 60.0:.1f} min | "
            f"{sn_loss:.0f} s |"
        )

    # --- Queue length in km ---
    lines += ["", "## Estimert kølengde", ""]
    lines.append(
        "Beregnet fra antall blokkerte + ventende kjøretøy, konvertert med "
        "120 kjt/km (stoppet trafikk) fordelt på 2 tilkomstfelt."
    )
    lines += [
        "",
        "| Scenario | Blokkerte kjt | Maks ventende | Kølengde (km) |",
        "|---|---|---|---|",
    ]
    for scenario_name in sorted(results):
        st = stats_by_scenario.get(scenario_name, {})
        ql = st.get("queue_length_km_mean")
        if ql is None:
            continue
        ni = st.get("not_inserted_mean", 0)
        pw = st.get("peak_waiting_mean", 0)
        lines.append(
            f"| {scenario_label(scenario_name)} | "
            f"{ni:.0f} | "
            f"{pw:.0f} | "
            f"{ql:.1f} km |"
        )

    lines += [
        "",
        "## Begrensninger",
        "",
        "- Repoet mangler fortsatt observasjonsbasert kalibrering og automatiserte tester.",
        "- Flytårnet/Bernt Balchens-krysset er fortsatt avhengig av OSM-nettets geometri og prioriteringsmodell; dette er en kjent modellbegrensning som må forbedres før rapportering utad.",
        "- Scenarioet med signaloptimalisering er midlertidig tatt ut av standardkjøringen til kryssmodellen er eksplisitt implementert.",
        "- Utrykningstidsberegningen forutsetter at andre kjøretøy viker (SUMO vClass=emergency). I praksis er dette avhengig av at det finnes plass å vike til — med 2+2 felt er det mindre rom for å slippe frem utrykningskjøretøy enn med 2+3.",
        "- Kølengdeestimatet er en forenklet omregning og tar ikke hensyn til faktisk køgeometri eller E18-tilknytning.",
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

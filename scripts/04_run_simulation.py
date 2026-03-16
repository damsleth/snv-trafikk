#!/usr/bin/env python3
"""Run SUMO simulations for all configured scenarios."""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
SCENARIOS_DIR = PROJECT_ROOT / "scenarios"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from utils.scenario_catalog import SCENARIOS, scenario_label


def find_sumo_binary() -> str:
    """Find the SUMO binary."""
    # Prefer the actual compiled binary inside the pip package
    pkg_sumo = PROJECT_ROOT / ".venv" / "lib" / "python3.10" / "site-packages" / "sumo" / "bin" / "sumo"
    if pkg_sumo.exists():
        return str(pkg_sumo)
    venv_sumo = PROJECT_ROOT / ".venv" / "bin" / "sumo"
    if venv_sumo.exists():
        return str(venv_sumo)
    result = subprocess.run(["which", "sumo"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    raise FileNotFoundError("SUMO binary not found")


def create_sumo_config(scenario_name: str, seed: int) -> Path:
    """Create a SUMO configuration file for one scenario/seed."""
    scenario = SCENARIOS[scenario_name]
    scenario_dir = SCENARIOS_DIR / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    output_dir = OUTPUT_DIR / scenario_name / f"seed_{seed}"
    output_dir.mkdir(parents=True, exist_ok=True)

    additional = [f for f in scenario.get("additional", []) if Path(f).exists()]

    config_file = scenario_dir / f"sumo_seed{seed}.cfg"
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<configuration>",
        "  <input>",
        f'    <net-file value="{scenario["network"]}"/>',
        f'    <route-files value="{scenario["routes"]}"/>',
    ]
    if additional:
        lines.append(f'    <additional-files value="{",".join(additional)}"/>')
    lines += [
        "  </input>",
        "  <time>",
        '    <begin value="0"/>',
        '    <end value="5400"/>',
        '    <step-length value="1.0"/>',
        "  </time>",
        "  <processing>",
        '    <lateral-resolution value="0.8"/>',
        '    <collision.action value="warn"/>',
        '    <time-to-teleport value="300"/>',
        "  </processing>",
        "  <random_number>",
        f'    <seed value="{seed}"/>',
        "  </random_number>",
        "  <output>",
        f'    <tripinfo-output value="{output_dir / "tripinfo.xml"}"/>',
        f'    <summary-output value="{output_dir / "summary.xml"}"/>',
        f'    <fcd-output value="{output_dir / "fcd.xml"}"/>',
        f'    <statistic-output value="{output_dir / "stats.xml"}"/>',
        "  </output>",
        "  <fcd_device>",
        '    <device.fcd.period value="5"/>',
        "  </fcd_device>",
        "</configuration>",
    ]

    config_file.write_text("\n".join(lines), encoding="utf-8")
    return config_file


def run_scenario(scenario_name: str, seed: int, verbose: bool = False) -> dict:
    """Run one SUMO simulation and capture summary metrics."""
    sumo_bin = find_sumo_binary()
    config_file = create_sumo_config(scenario_name, seed)
    output_dir = OUTPUT_DIR / scenario_name / f"seed_{seed}"
    print(f"  Running {scenario_name} (seed={seed})...")

    cmd = [
        sumo_bin,
        "-c",
        str(config_file),
        "--no-warnings",
        "true",
        "--verbose",
        "true" if verbose else "false",
        "--no-step-log",
        "true",
        "--ignore-route-errors",
        "false",
        "--routing-algorithm",
        "astar",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        print(f"    WARNING: SUMO returned code {result.returncode}")
        if verbose:
            print(result.stderr[:1000])

    stats = parse_stats(output_dir)
    stats["seed"] = seed
    stats["scenario"] = scenario_name
    stats["returncode"] = result.returncode

    with open(output_dir / "run_stats.json", "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
    return stats


def parse_stats(output_dir: Path) -> dict:
    """Parse SUMO output files for robust scenario metrics."""
    stats: dict[str, float | int] = {}

    tripinfo_file = output_dir / "tripinfo.xml"
    if tripinfo_file.exists():
        try:
            tree = ET.parse(str(tripinfo_file))
            trips = tree.getroot().findall("tripinfo")

            # Separate regular vs emergency vehicles
            regular = [t for t in trips if not t.get("id", "").startswith("emer_")]
            emergency = [t for t in trips if t.get("id", "").startswith("emer_")]

            durations = [float(t.get("duration", 0)) for t in regular]
            waiting_times = [float(t.get("waitingTime", 0)) for t in regular]
            time_losses = [float(t.get("timeLoss", 0)) for t in regular]

            if durations:
                stats["completed_vehicles"] = len(durations)
                stats["avg_duration_s"] = sum(durations) / len(durations)
                stats["max_duration_s"] = max(durations)
                stats["avg_waiting_time_s"] = sum(waiting_times) / len(waiting_times)
                stats["max_waiting_time_s"] = max(waiting_times)
                stats["avg_time_loss_s"] = sum(time_losses) / len(time_losses)
                stats["completed_time_loss_h"] = sum(time_losses) / 3600.0

            # Emergency vehicle metrics
            if emergency:
                emer_durations = [float(t.get("duration", 0)) for t in emergency]
                emer_time_losses = [float(t.get("timeLoss", 0)) for t in emergency]
                stats["emergency_count"] = len(emer_durations)
                stats["emergency_avg_duration_s"] = sum(emer_durations) / len(emer_durations)
                stats["emergency_max_duration_s"] = max(emer_durations)
                stats["emergency_avg_time_loss_s"] = sum(emer_time_losses) / len(emer_time_losses)

            # Snarøya-origin trips (per-capita delay for peninsula residents).
            # tripinfo records departLane="edgeId_laneIndex", so we extract
            # the edge ID and match against the known snv_syd origin edges.
            SNV_SYD_ORIGINS = {"115505254", "515410724#0"}
            snaroya_only = []
            for t in regular:
                dl = t.get("departLane", "")
                depart_edge = dl.rsplit("_", 1)[0] if "_" in dl else ""
                if depart_edge in SNV_SYD_ORIGINS:
                    snaroya_only.append(t)
            if snaroya_only:
                snaroya_dur = [float(t.get("duration", 0)) for t in snaroya_only]
                snaroya_loss = [float(t.get("timeLoss", 0)) for t in snaroya_only]
                stats["snaroya_origin_count"] = len(snaroya_dur)
                stats["snaroya_avg_duration_s"] = sum(snaroya_dur) / len(snaroya_dur)
                stats["snaroya_avg_time_loss_s"] = sum(snaroya_loss) / len(snaroya_loss)

        except ET.ParseError:
            print(f"    WARNING: Could not parse {tripinfo_file}")

    summary_file = output_dir / "summary.xml"
    if summary_file.exists():
        try:
            tree = ET.parse(str(summary_file))
            steps = tree.getroot().findall("step")
            if steps:
                waiting_series = [int(step.get("waiting", 0)) for step in steps]
                halting_series = [int(step.get("halting", 0)) for step in steps]
                blocked_vehicle_seconds = sum(waiting_series)
                queued_vehicle_seconds = sum(waiting + halting for waiting, halting in zip(waiting_series, halting_series))
                stats["blocked_vehicle_h"] = blocked_vehicle_seconds / 3600.0
                stats["queued_vehicle_h"] = queued_vehicle_seconds / 3600.0
                stats["peak_waiting"] = max(waiting_series)
                stats["peak_queue_proxy"] = max(waiting + halting for waiting, halting in zip(waiting_series, halting_series))
        except ET.ParseError:
            print(f"    WARNING: Could not parse {summary_file}")

    stats_file = output_dir / "stats.xml"
    if stats_file.exists():
        try:
            tree = ET.parse(str(stats_file))
            root = tree.getroot()
            vehicles = root.find(".//vehicles")
            if vehicles is not None:
                stats["loaded"] = int(vehicles.get("loaded", 0))
                stats["inserted"] = int(vehicles.get("inserted", 0))
                stats["waiting"] = int(vehicles.get("waiting", 0))
                stats["teleports"] = int(vehicles.get("teleports", 0))
                stats["not_inserted"] = int(vehicles.get("loaded", 0)) - int(vehicles.get("inserted", 0))

            perf = root.find(".//vehicleTripStatistics")
            if perf is not None:
                stats["stat_duration"] = float(perf.get("duration", 0))
                stats["stat_waiting_time"] = float(perf.get("waitingTime", 0))
                stats["stat_time_loss"] = float(perf.get("timeLoss", 0))
                stats["stat_speed"] = float(perf.get("speed", 0))
        except ET.ParseError:
            print(f"    WARNING: Could not parse {stats_file}")

    completed_delay = float(stats.get("completed_time_loss_h", 0))
    blocked_delay = float(stats.get("blocked_vehicle_h", 0))
    stats["system_delay_h"] = completed_delay + blocked_delay

    # Approximate queue length in km.
    # "not_inserted" vehicles are waiting outside the network boundary.
    # Density assumption: ~120 vehicles/km for stopped single-lane traffic
    # (avg vehicle length 4.5 m + ~3.8 m gap ≈ 8.3 m/veh → ~120 veh/km).
    # Snarøyveien approach from E18 has 2 lanes, so divide by 2.
    STOPPED_DENSITY_VEH_PER_KM = 120
    APPROACH_LANES = 2
    not_inserted = int(stats.get("not_inserted", 0))
    peak_waiting = int(stats.get("peak_waiting", 0))
    stats["queue_length_km"] = round(
        (not_inserted + peak_waiting) / (STOPPED_DENSITY_VEH_PER_KM * APPROACH_LANES), 1
    )

    return stats


def run_all_scenarios(seeds: int = 5, verbose: bool = False) -> None:
    """Run every configured scenario across multiple random seeds."""
    print("=" * 60)
    print("PHASE 3: Running SUMO simulations")
    print("=" * 60)

    all_results: dict[str, list[dict]] = {}

    for scenario_name, scenario_def in SCENARIOS.items():
        if not Path(str(scenario_def["network"])).exists():
            print(f"\nSKIPPING {scenario_name}: network not found at {scenario_def['network']}")
            continue
        route_files = str(scenario_def["routes"]).split(",")
        missing_routes = [r for r in route_files if not Path(r).exists()]
        if missing_routes:
            print(f"\nSKIPPING {scenario_name}: routes not found: {missing_routes}")
            continue

        print(f"\n{'-' * 44}")
        print(f"Scenario: {scenario_name}")
        print(f"  {scenario_def['description']}")
        print(f"  Label: {scenario_label(scenario_name)}")
        print(f"  Seeds: {seeds}")

        scenario_results = []
        for seed in range(1, seeds + 1):
            try:
                stats = run_scenario(scenario_name, seed, verbose)
                scenario_results.append(stats)
                print(
                    "    "
                    f"Seed {seed}: inserted={stats.get('inserted', '?')} "
                    f"waiting={stats.get('waiting', '?')} "
                    f"system_delay_h={stats.get('system_delay_h', '?')}"
                )
            except Exception as exc:
                print(f"    Seed {seed}: FAILED - {exc}")

        all_results[scenario_name] = scenario_results

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "all_results.json", "w", encoding="utf-8") as handle:
        json.dump(all_results, handle, indent=2, default=str)
    print(f"\nCombined results -> {OUTPUT_DIR / 'all_results.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SUMO traffic simulations")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--scenario", type=str, help="Run a specific scenario")
    parser.add_argument("--seeds", type=int, default=5, help="Number of random seeds")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.all:
        run_all_scenarios(seeds=args.seeds, verbose=args.verbose)
        return

    if args.scenario:
        if args.scenario not in SCENARIOS:
            print(f"Unknown scenario: {args.scenario}")
            print(f"Available: {sorted(SCENARIOS)}")
            sys.exit(1)
        for seed in range(1, args.seeds + 1):
            stats = run_scenario(args.scenario, seed, args.verbose)
            print(json.dumps(stats, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()

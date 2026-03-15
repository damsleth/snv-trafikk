#!/usr/bin/env python3
"""Run SUMO simulations for all scenarios.

Usage:
    python scripts/04_run_simulation.py --all
    python scripts/04_run_simulation.py --scenario scenario_4A_v1
    python scripts/04_run_simulation.py --scenario scenario_4A_base --seeds 5
"""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NETWORK_DIR = PROJECT_ROOT / "network"
DEMAND_DIR = PROJECT_ROOT / "demand"
SCENARIOS_DIR = PROJECT_ROOT / "scenarios"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Scenario definitions
SCENARIOS = {
    "scenario_4A_base": {
        "network": NETWORK_DIR / "base" / "fornebu.net.xml",
        "routes": DEMAND_DIR / "routes" / "morning_4A.rou.xml",
        "description": "Scenario 4A demand on current (2+3) network",
        "additional": [
            str(NETWORK_DIR / "signals" / "roundabout_params.add.xml"),
        ],
    },
    "scenario_4A_v1": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "routes": DEMAND_DIR / "routes" / "morning_4A.rou.xml",
        "description": "Scenario 4A on proposed 2+2 network (MAIN SCENARIO)",
        "additional": [
            str(NETWORK_DIR / "signals" / "roundabout_params.add.xml"),
        ],
    },
    "scenario_4A_v2": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v2.net.xml",
        "routes": DEMAND_DIR / "routes" / "morning_4A.rou.xml",
        "description": "Scenario 4A on worst-case 1+1+kollektiv network",
        "additional": [
            str(NETWORK_DIR / "signals" / "roundabout_params.add.xml"),
        ],
    },
    "scenario_1A_v1": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "routes": DEMAND_DIR / "routes" / "morning_1A.rou.xml",
        "description": "Higher demand (Scenario 1A) on proposed 2+2 network",
        "additional": [
            str(NETWORK_DIR / "signals" / "roundabout_params.add.xml"),
        ],
    },
    "scenario_4A_v1_optimized": {
        "network": NETWORK_DIR / "proposed" / "fornebu_v1.net.xml",
        "routes": DEMAND_DIR / "routes" / "morning_4A.rou.xml",
        "description": "Scenario 4A on 2+2 with optimized signal timing",
        "additional": [
            str(NETWORK_DIR / "signals" / "roundabout_params.add.xml"),
        ],
    },
}


def find_sumo_binary() -> str:
    """Find the SUMO binary."""
    venv_sumo = PROJECT_ROOT / ".venv" / "bin" / "sumo"
    if venv_sumo.exists():
        return str(venv_sumo)
    result = subprocess.run(["which", "sumo"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    raise FileNotFoundError("SUMO binary not found")


def create_sumo_config(scenario_name: str, seed: int) -> Path:
    """Create a SUMO configuration file for a scenario run.

    Uses plain text format to avoid XML element naming issues with SUMO's
    option parser (dots in names, nested elements, etc.).
    """
    scenario = SCENARIOS[scenario_name]
    scenario_dir = SCENARIOS_DIR / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    output_dir = OUTPUT_DIR / scenario_name / f"seed_{seed}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter additional files to existing ones
    additional = []
    if scenario.get("additional"):
        additional = [f for f in scenario["additional"] if Path(f).exists()]

    config_file = scenario_dir / f"sumo_seed{seed}.cfg"
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<configuration>',
        '  <input>',
        f'    <net-file value="{scenario["network"]}"/>',
        f'    <route-files value="{scenario["routes"]}"/>',
    ]
    if additional:
        lines.append(f'    <additional-files value="{",".join(additional)}"/>')
    lines += [
        '  </input>',
        '  <time>',
        '    <begin value="0"/>',
        '    <end value="5400"/>',
        '    <step-length value="1.0"/>',
        '  </time>',
        '  <processing>',
        '    <lateral-resolution value="0.8"/>',
        '    <collision.action value="warn"/>',
        '    <time-to-teleport value="300"/>',
        '  </processing>',
        '  <random_number>',
        f'    <seed value="{seed}"/>',
        '  </random_number>',
        '  <output>',
        f'    <tripinfo-output value="{output_dir / "tripinfo.xml"}"/>',
        f'    <summary-output value="{output_dir / "summary.xml"}"/>',
        f'    <fcd-output value="{output_dir / "fcd.xml"}"/>',
        f'    <statistic-output value="{output_dir / "stats.xml"}"/>',
        '  </output>',
        '  <fcd_device>',
        '    <device.fcd.period value="5"/>',
        '  </fcd_device>',
        '</configuration>',
    ]

    config_file.write_text("\n".join(lines), encoding="utf-8")
    return config_file


def run_scenario(scenario_name: str, seed: int, verbose: bool = False) -> dict:
    """Run a single SUMO simulation and return basic stats."""
    sumo_bin = find_sumo_binary()
    config_file = create_sumo_config(scenario_name, seed)

    output_dir = OUTPUT_DIR / scenario_name / f"seed_{seed}"
    print(f"  Running {scenario_name} (seed={seed})...")

    cmd = [
        sumo_bin,
        "-c", str(config_file),
        "--no-warnings", "true",
        "--verbose", "true" if verbose else "false",
        "--no-step-log", "true",
        "--ignore-route-errors", "true",
        "--routing-algorithm", "astar",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,  # 10 min max
    )

    if result.returncode != 0:
        print(f"    WARNING: SUMO returned code {result.returncode}")
        if verbose:
            print(f"    STDERR: {result.stderr[:500]}")

    # Parse basic statistics
    stats = parse_stats(output_dir)
    stats["seed"] = seed
    stats["scenario"] = scenario_name
    stats["returncode"] = result.returncode

    # Save stats
    with open(output_dir / "run_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    return stats


def parse_stats(output_dir: Path) -> dict:
    """Parse SUMO output files for key statistics."""
    stats = {}

    # Parse tripinfo for travel times
    tripinfo_file = output_dir / "tripinfo.xml"
    if tripinfo_file.exists():
        try:
            tree = ET.parse(str(tripinfo_file))
            root = tree.getroot()
            trips = root.findall("tripinfo")

            durations = []
            waiting_times = []
            time_losses = []

            for trip in trips:
                durations.append(float(trip.get("duration", 0)))
                waiting_times.append(float(trip.get("waitingTime", 0)))
                time_losses.append(float(trip.get("timeLoss", 0)))

            if durations:
                stats["total_vehicles"] = len(durations)
                stats["avg_duration_s"] = sum(durations) / len(durations)
                stats["max_duration_s"] = max(durations)
                stats["avg_waiting_time_s"] = sum(waiting_times) / len(waiting_times)
                stats["max_waiting_time_s"] = max(waiting_times)
                stats["avg_time_loss_s"] = sum(time_losses) / len(time_losses)
                stats["total_time_loss_h"] = sum(time_losses) / 3600.0
        except ET.ParseError:
            print(f"    WARNING: Could not parse {tripinfo_file}")

    # Parse statistics output
    stats_file = output_dir / "stats.xml"
    if stats_file.exists():
        try:
            tree = ET.parse(str(stats_file))
            root = tree.getroot()

            vehicles = root.find(".//vehicles")
            if vehicles is not None:
                stats["loaded"] = int(vehicles.get("loaded", 0))
                stats["inserted"] = int(vehicles.get("inserted", 0))
                stats["waiting"] = int(vehicles.get("waiting", 0))  # couldn't enter
                stats["teleports"] = int(vehicles.get("teleports", 0))

            perf = root.find(".//vehicleTripStatistics")
            if perf is not None:
                stats["stat_duration"] = float(perf.get("duration", 0))
                stats["stat_waiting_time"] = float(perf.get("waitingTime", 0))
                stats["stat_time_loss"] = float(perf.get("timeLoss", 0))
                stats["stat_speed"] = float(perf.get("speed", 0))
        except ET.ParseError:
            pass

    return stats


def run_all_scenarios(seeds: int = 5, verbose: bool = False):
    """Run all defined scenarios with multiple random seeds."""
    print("=" * 60)
    print("PHASE 3: Running SUMO simulations")
    print("=" * 60)

    all_results = {}

    for scenario_name, scenario_def in SCENARIOS.items():
        # Check network exists
        if not scenario_def["network"].exists():
            print(f"\nSKIPPING {scenario_name}: network not found at {scenario_def['network']}")
            continue
        if not scenario_def["routes"].exists():
            print(f"\nSKIPPING {scenario_name}: routes not found at {scenario_def['routes']}")
            continue

        print(f"\n{'─' * 40}")
        print(f"Scenario: {scenario_name}")
        print(f"  {scenario_def['description']}")
        print(f"  Network: {scenario_def['network'].name}")
        print(f"  Routes: {scenario_def['routes'].name}")
        print(f"  Seeds: {seeds}")

        scenario_results = []
        for seed in range(1, seeds + 1):
            try:
                stats = run_scenario(scenario_name, seed, verbose)
                scenario_results.append(stats)
                inserted = stats.get("inserted", "?")
                waiting = stats.get("waiting", "?")
                avg_loss = stats.get("avg_time_loss_s", "?")
                print(f"    Seed {seed}: {inserted} inserted, {waiting} waiting, avg_loss={avg_loss}s")
            except Exception as e:
                print(f"    Seed {seed}: FAILED - {e}")

        all_results[scenario_name] = scenario_results

    # Save combined results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "all_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nCombined results → {OUTPUT_DIR / 'all_results.json'}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for scenario_name, results in all_results.items():
        if not results:
            continue
        avg_loss = sum(r.get("avg_time_loss_s", 0) for r in results) / len(results)
        avg_waiting = sum(r.get("waiting", 0) for r in results) / len(results)
        print(f"  {scenario_name}:")
        print(f"    Avg time loss: {avg_loss:.1f}s")
        print(f"    Avg vehicles unable to enter: {avg_waiting:.0f}")

    print(f"\n✓ All simulations complete!")


def main():
    parser = argparse.ArgumentParser(description="Run SUMO traffic simulations")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--scenario", type=str, help="Run a specific scenario")
    parser.add_argument("--seeds", type=int, default=5, help="Number of random seeds")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.all:
        run_all_scenarios(seeds=args.seeds, verbose=args.verbose)
    elif args.scenario:
        if args.scenario not in SCENARIOS:
            print(f"Unknown scenario: {args.scenario}")
            print(f"Available: {list(SCENARIOS.keys())}")
            sys.exit(1)
        for seed in range(1, args.seeds + 1):
            stats = run_scenario(args.scenario, seed, args.verbose)
            print(f"  → {json.dumps(stats, indent=2)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

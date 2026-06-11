#!/usr/bin/env python3
"""Run SUMO simulations for all configured scenarios."""

import argparse
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from config import (
    OUTPUT_DIR,
    PROJECT_ROOT,
    SCENARIOS_DIR,
    SIMULATION_BEGIN_S,
    SIMULATION_END_S,
    SNAROYA_ORIGIN_EDGE_IDS,
    lane_edge_id,
    queue_length_km,
    sumo_config_path,
    sumo_config_path_list,
)
from utils.provenance import git_commit, sha256_file, utc_now_iso, write_json
from utils.scenario_catalog import SCENARIOS, scenario_label, validate_scenario_catalog


EXPECTED_OUTPUT_FILES = ("tripinfo.xml", "summary.xml", "fcd.xml", "stats.xml")
LOCAL_ABSOLUTE_PATH_MARKERS = ("/Users/", "/home/", "/Volumes/", "/private/var/")
OLD_PROJECT_MARKERS = ("/Users/damsleth/Code/SNV",)


def find_sumo_binary() -> str:
    """Find the SUMO binary."""
    candidates = [PROJECT_ROOT / ".venv" / "bin" / "sumo"]
    site_packages_root = PROJECT_ROOT / ".venv" / "lib"
    if site_packages_root.exists():
        candidates.extend(site_packages_root.glob("python*/site-packages/sumo/bin/sumo"))

    path_sumo = shutil.which("sumo")
    if path_sumo:
        candidates.append(Path(path_sumo))

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise FileNotFoundError("SUMO binary not found")


def validate_config_paths(config_file: Path) -> dict:
    """Validate that generated SUMO config paths are portable."""
    text = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
    offending = sorted(
        marker for marker in (*LOCAL_ABSOLUTE_PATH_MARKERS, *OLD_PROJECT_MARKERS)
        if marker in text
    )
    return {
        "valid": not offending,
        "file": str(config_file),
        "offending_markers": offending,
    }


def cleanup_configs(dry_run: bool = True) -> list[Path]:
    """Delete or list generated scenario SUMO config files."""
    targets = sorted(SCENARIOS_DIR.glob("scenario_*/sumo_seed*.cfg"))
    if not dry_run:
        for target in targets:
            target.unlink(missing_ok=True)
    return targets


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
        f'    <net-file value="{sumo_config_path(scenario["network"])}"/>',
        f'    <route-files value="{sumo_config_path_list(str(scenario["routes"]))}"/>',
    ]
    if additional:
        lines.append(f'    <additional-files value="{sumo_config_path_list(additional)}"/>')
    lines += [
        "  </input>",
        "  <time>",
        f'    <begin value="{SIMULATION_BEGIN_S}"/>',
        f'    <end value="{SIMULATION_END_S}"/>',
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
        f'    <tripinfo-output value="{sumo_config_path(output_dir / "tripinfo.xml")}"/>',
        f'    <summary-output value="{sumo_config_path(output_dir / "summary.xml")}"/>',
        f'    <fcd-output value="{sumo_config_path(output_dir / "fcd.xml")}"/>',
        f'    <statistic-output value="{sumo_config_path(output_dir / "stats.xml")}"/>',
        "  </output>",
        "  <fcd_device>",
        '    <device.fcd.period value="5"/>',
        "  </fcd_device>",
        "</configuration>",
    ]

    config_file.write_text("\n".join(lines), encoding="utf-8")
    validation = validate_config_paths(config_file)
    if not validation["valid"]:
        markers = ", ".join(validation["offending_markers"])
        raise ValueError(f"Generated non-portable SUMO config {config_file}: {markers}")
    return config_file


def output_integrity(output_dir: Path) -> dict:
    """Check expected SUMO output files for presence and parseability."""
    files = {}
    errors = []
    for filename in EXPECTED_OUTPUT_FILES:
        path = output_dir / filename
        status = {
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "parseable": None,
        }
        if filename.endswith(".xml") and path.exists() and path.stat().st_size > 0:
            try:
                ET.parse(str(path))
                status["parseable"] = True
            except ET.ParseError as exc:
                status["parseable"] = False
                errors.append(f"{filename}: XML parse error: {exc}")
        elif not path.exists() or status["size_bytes"] == 0:
            errors.append(f"{filename}: missing or empty")
        files[filename] = status
    return {"valid": not errors, "files": files, "errors": errors}


def run_command(cmd: list[str], timeout: int) -> dict:
    """Run a subprocess and return structured execution metadata."""
    started = time.monotonic()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
            "duration_s": round(time.monotonic() - started, 2),
            "category": "ok" if result.returncode == 0 else "nonzero_exit",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": -1,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "duration_s": round(time.monotonic() - started, 2),
            "category": "timeout",
        }


def write_simulation_metadata(scenario_name: str, seed: int, output_dir: Path, sumo_bin: str, config_file: Path) -> None:
    """Write a small provenance receipt for one simulation seed."""
    scenario = SCENARIOS[scenario_name]
    route_hashes = {
        str(Path(route)): sha256_file(Path(route))
        for route in str(scenario["routes"]).split(",")
        if route
    }
    payload = {
        "generated_at": utc_now_iso(),
        "git_commit": git_commit(PROJECT_ROOT),
        "scenario": scenario_name,
        "family": scenario.get("family"),
        "period": scenario.get("period"),
        "status": scenario.get("status"),
        "seed": seed,
        "sumo_binary": sumo_bin,
        "network": str(scenario["network"]),
        "network_sha256": sha256_file(Path(scenario["network"])),
        "routes": route_hashes,
        "config": str(config_file),
        "config_sha256": sha256_file(config_file),
    }
    write_json(output_dir / "simulation_metadata.json", payload)


def run_scenario(scenario_name: str, seed: int, verbose: bool = False, strict_xml: bool = False) -> dict:
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

    execution = run_command(cmd, timeout=900)
    if execution["returncode"] != 0:
        print(f"    WARNING: SUMO returned code {execution['returncode']}")
        if verbose:
            print(execution["stderr"][:1000])
        stats = {
            "failed": True,
            "error": execution["stderr"][:1000].strip() or execution["category"],
        }
    else:
        stats = parse_stats(output_dir, strict_xml=strict_xml)

    integrity = output_integrity(output_dir)
    if strict_xml and not integrity["valid"]:
        stats["failed"] = True
        stats["error"] = "; ".join(integrity["errors"])

    stats["seed"] = seed
    stats["scenario"] = scenario_name
    stats["returncode"] = execution["returncode"]
    stats["execution"] = execution
    stats["integrity"] = integrity
    write_simulation_metadata(scenario_name, seed, output_dir, sumo_bin, config_file)

    with open(output_dir / "run_stats.json", "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
    return stats


def parse_stats(output_dir: Path, strict_xml: bool = False) -> dict:
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
            snaroya_only = []
            for t in regular:
                depart_edge = lane_edge_id(t.get("departLane", ""))
                if depart_edge in SNAROYA_ORIGIN_EDGE_IDS:
                    snaroya_only.append(t)
            if snaroya_only:
                snaroya_dur = [float(t.get("duration", 0)) for t in snaroya_only]
                snaroya_loss = [float(t.get("timeLoss", 0)) for t in snaroya_only]
                stats["snaroya_origin_count"] = len(snaroya_dur)
                stats["snaroya_avg_duration_s"] = sum(snaroya_dur) / len(snaroya_dur)
                stats["snaroya_avg_time_loss_s"] = sum(snaroya_loss) / len(snaroya_loss)

        except ET.ParseError as exc:
            print(f"    WARNING: Could not parse {tripinfo_file}")
            if strict_xml:
                stats["failed"] = True
                stats["error"] = f"Could not parse {tripinfo_file}: {exc}"

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
        except ET.ParseError as exc:
            print(f"    WARNING: Could not parse {summary_file}")
            if strict_xml:
                stats["failed"] = True
                stats["error"] = f"Could not parse {summary_file}: {exc}"

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
        except ET.ParseError as exc:
            print(f"    WARNING: Could not parse {stats_file}")
            if strict_xml:
                stats["failed"] = True
                stats["error"] = f"Could not parse {stats_file}: {exc}"

    completed_delay = float(stats.get("completed_time_loss_h", 0))
    blocked_delay = float(stats.get("blocked_vehicle_h", 0))
    stats["system_delay_h"] = completed_delay + blocked_delay

    not_inserted = int(stats.get("not_inserted", 0))
    peak_waiting = int(stats.get("peak_waiting", 0))
    stats["queue_length_km"] = queue_length_km(not_inserted + peak_waiting)

    return stats


def run_all_scenarios(seeds: int = 5, verbose: bool = False, strict_xml: bool = False, retry_failed: bool = False) -> None:
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
                if retry_failed and not seed_needs_retry(scenario_name, seed):
                    continue
                stats = run_scenario(scenario_name, seed, verbose, strict_xml=strict_xml)
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


def seed_needs_retry(scenario_name: str, seed: int) -> bool:
    """Return True when a seed is missing, failed, or has invalid outputs."""
    output_dir = OUTPUT_DIR / scenario_name / f"seed_{seed}"
    stats_file = output_dir / "run_stats.json"
    if not stats_file.exists():
        return True
    try:
        stats = json.loads(stats_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    if stats.get("failed"):
        return True
    integrity = stats.get("integrity") or output_integrity(output_dir)
    return not bool(integrity.get("valid", False))


def generate_configs_only(seeds: int = 5, scenario_name: str | None = None) -> list[Path]:
    """Generate SUMO config files without running SUMO."""
    scenario_names = [scenario_name] if scenario_name else sorted(SCENARIOS)
    configs = []
    for name in scenario_names:
        if name not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {name}")
        for seed in range(1, seeds + 1):
            configs.append(create_sumo_config(name, seed))
    return configs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SUMO traffic simulations")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--scenario", type=str, help="Run a specific scenario")
    parser.add_argument("--seeds", type=int, default=5, help="Number of random seeds")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--strict-xml", action="store_true", help="Treat malformed XML outputs as failed seeds")
    parser.add_argument("--retry-failed", action="store_true", help="Only run missing, failed, or invalid seeds")
    parser.add_argument("--validate", action="store_true", help="Validate scenario catalog and inputs, then exit")
    parser.add_argument("--clean-configs", action="store_true", help="Remove generated scenario SUMO config files")
    parser.add_argument("--dry-run", action="store_true", help="Preview cleanup actions without deleting files")
    parser.add_argument("--generate-configs-only", action="store_true", help="Generate SUMO config files without running simulations")
    args = parser.parse_args()

    if args.validate:
        report = validate_scenario_catalog()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if not report["valid"]:
            sys.exit(1)
        return

    if args.clean_configs:
        targets = cleanup_configs(dry_run=args.dry_run)
        action = "Would remove" if args.dry_run else "Removed"
        for target in targets:
            print(f"{action} {target}")
        return

    if args.generate_configs_only:
        configs = generate_configs_only(seeds=args.seeds, scenario_name=args.scenario)
        for config in configs:
            print(config)
        return

    if args.all:
        run_all_scenarios(seeds=args.seeds, verbose=args.verbose, strict_xml=args.strict_xml, retry_failed=args.retry_failed)
        return

    if args.scenario:
        if args.scenario not in SCENARIOS:
            print(f"Unknown scenario: {args.scenario}")
            print(f"Available: {sorted(SCENARIOS)}")
            sys.exit(1)
        for seed in range(1, args.seeds + 1):
            if args.retry_failed and not seed_needs_retry(args.scenario, seed):
                print(f"Skipping {args.scenario} seed {seed}: already valid")
                continue
            stats = run_scenario(args.scenario, seed, args.verbose, strict_xml=args.strict_xml)
            print(json.dumps(stats, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
